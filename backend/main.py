"""
main.py — FastAPI application entry point for Music AI Chatbot.

Endpoints:
  GET  /health                 — health check (used by Railway)
  POST /analyze                — fetch YouTube transcript + embed into ChromaDB
  POST /analyze-lyrics         — embed manually pasted lyrics (for non-English songs)
  POST /chat                   — send a message to the LangChain agent
  GET  /transcript/{video_id}  — read back transcript chunks from ChromaDB

Startup behaviour:
  - Creates the LangChain agent once (reused across all requests)
  - Validates all required environment variables
  - In production (Railway): seeds marketing knowledge into ChromaDB on boot
    because EphemeralClient resets on every restart
"""

from contextlib import asynccontextmanager
import os
import tempfile

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import date
import json
from openai import AsyncOpenAI
from database import create_tables, save_calendar_events, get_calendar_events, update_calendar_event, delete_calendar_event, save_todos, get_todos, update_todo, delete_todo, delete_session_data

from seed_knowledge import seed_knowledge_file
from config import validate_config, IS_PRODUCTION, ENVIRONMENT
from pipeline import fetch_transcript, chunk_and_embed, get_transcript_from_chroma
from agent import create_music_agent, run_agent


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    youtube_url: str


class ChatRequest(BaseModel):
    video_id: str
    message: str
    session_id: str
    video_title: str = ""
    video_channel: str = ""  # Optional — used to give agent better context


class AnalyzeLyricsRequest(BaseModel):
    video_id: str
    lyrics_text: str
    title: str = "Unknown Title"
    artist: str = "Unknown Artist"


class AnalyzeLyricsResponse(BaseModel):
    video_id: str
    title: str
    artist: str
    word_count: int
    chunks_created: int
    collection_name: str
    status: str


class TranscriptResponse(BaseModel):
    video_id: str
    transcript_text: str
    word_count: int
    collection_name: str


class ChatResponse(BaseModel):
    response: str
    tools_used: list[str]
    session_id: str
    calendar_events: list[dict] = []
    todo_items: list[dict] = []


# ---------------------------------------------------------------------------
# App lifecycle — startup + shutdown
# ---------------------------------------------------------------------------

agent_state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once when the server starts, before accepting any requests.

    Order:
      1. Validate all required environment variables (crash early if missing)
      2. In production: seed marketing knowledge into ChromaDB (EphemeralClient
         loses all data on restart, so we must re-seed every boot)
      3. Create the LangChain agent (expensive — done once, reused forever)
    """
    print("\n🚀 [startup] Starting Music AI backend...")
    print(f"🚀 [startup] Environment: {ENVIRONMENT}")

    # Step 1 — validate env vars
    try:
        validate_config()
    except ValueError as e:
        print(f"🚀 [startup] FATAL: {e}")
        raise

    # Step 2 — seed marketing knowledge in production
    if IS_PRODUCTION:
        print("🚀 [startup] Production mode — seeding marketing knowledge base...")
        try:
            from seed_knowledge import seed_knowledge_file
            seed_knowledge_file(
                filename="marketing_knowledge.md",
                namespace="marketing_knowledge",
            )
            print("🚀 [startup] Marketing knowledge seeded ✓")
        except Exception as e:
            # Non-fatal: app still works without the knowledge base
            print(f"🚀 [startup] WARNING: Could not seed marketing knowledge: {e}")
    else:
        print("🚀 [startup] Local mode — skipping knowledge seed (run seed_knowledge.py manually)")

    # Step 2.5 — create database tables
    await create_tables()

    # Step 3 — create agent
    agent_state["agent"] = create_music_agent()
    print("🚀 [startup] Backend ready ✓\n")

    yield

    print("\n[shutdown] Music AI backend shutting down")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Music AI Chatbot API",
    description="AI-powered music marketing assistant. Analyze YouTube videos and chat about songs.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — open for development and school demo.
# In the SaaS phase: replace allow_origins=["*"] with your exact Vercel domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check — Railway pings this to confirm the service is alive."""
    return {
        "status": "ok",
        "message": "Music AI backend running",
        "environment": ENVIRONMENT,
        "agent_ready": "agent" in agent_state,
    }


@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    """
    Accepts a YouTube URL, fetches the transcript, embeds it into ChromaDB.
    Returns video metadata + embedding stats.

    Transcript strategy:
      1. youtube-transcript-api (fast, free, works for most major releases)
      2. AssemblyAI fallback (for videos with captions disabled)

    For non-English songs with poor auto-captions, use POST /analyze-lyrics instead.
    """
    print(f"\n📥 [/analyze] URL: {request.youtube_url}")

    try:
        transcript_data = fetch_transcript(request.youtube_url)
        print(f"   Transcript fetched: {transcript_data.get('word_count', 0)} words")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"   ❌ /analyze error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    try:
        embed_data = chunk_and_embed(
            video_id=transcript_data["video_id"],
            transcript_text=transcript_data["transcript_text"],
        )
        print(f"   Embedded: {embed_data.get('chunks_created', 0)} chunks")
    except Exception as e:
        print(f"   ❌ /analyze embed error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")

    return {**transcript_data, **embed_data}


@app.post("/analyze-lyrics", response_model=AnalyzeLyricsResponse)
async def analyze_lyrics(request: AnalyzeLyricsRequest):
    """
    Accepts manually pasted lyrics and embeds them into ChromaDB.

    Use this when:
      - The YouTube video has no captions (e.g. new indie release)
      - The auto-transcript quality is poor (common for Lithuanian, Latvian,
        Estonian, and other smaller-language songs)
      - You already have the correct lyrics from Genius or another source

    The video_id must match the one returned by POST /analyze — the agent
    uses the same video_id to scope its ChromaDB searches.
    """
    print(f"\n📥 [/analyze-lyrics] video_id: {request.video_id} | artist: {request.artist}")

    if not request.lyrics_text.strip():
        raise HTTPException(status_code=400, detail="lyrics_text cannot be empty.")

    if len(request.lyrics_text.strip()) < 20:
        raise HTTPException(status_code=400, detail="lyrics_text is too short. Paste the full lyrics.")

    try:
        embed_data = chunk_and_embed(
            video_id=request.video_id,
            transcript_text=request.lyrics_text,
        )
        print(f"   Embedded: {embed_data.get('chunks_created', 0)} chunks")
    except Exception as e:
        print(f"   ❌ /analyze-lyrics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lyrics embedding failed: {str(e)}")

    return AnalyzeLyricsResponse(
        video_id=request.video_id,
        title=request.title,
        artist=request.artist,
        word_count=len(request.lyrics_text.split()),
        chunks_created=embed_data["chunks_created"],
        collection_name=embed_data["collection_name"],
        status="success",
    )

async def extract_tasks_from_response(response_text: str) -> dict:
    """
    Calls GPT-4o-mini to extract actionable tasks and dates from agent response.
    Today's date is injected so all relative dates (next Friday, in 2 weeks)
    are resolved to real YYYY-MM-DD values — no hallucination possible.
    """
    today = date.today().isoformat()
    print(f"📅 Extracting tasks from agent response (today = {today})")

    client = AsyncOpenAI()

    prompt = f"""Today: {today}

Extract ALL actionable items from this music marketing response.

Rules:
- Convert ALL relative dates to YYYY-MM-DD using today={today}
- Dates mentioned explicitly OR implied (e.g. "2 weeks before June 11" = {today}) → calendar_events
- Actions without dates → todo_items
- Extract EVERY item — do not summarize or skip any
- type: release|deadline|promo|spotify|youtube|social_media|general
- Return ONLY valid JSON, no markdown

{{"calendar_events":[{{"title":"...","date":"YYYY-MM-DD","type":"..."}}],"todo_items":[{{"title":"...","due_date":"YYYY-MM-DD or null"}}]}}

Response to analyze:
{response_text}"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()
        print(f"   Raw extraction: {raw[:200]}")

        # Strip markdown fences if model adds them anyway
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        parsed = json.loads(raw)
        calendar_events = parsed.get("calendar_events", [])
        todo_items = parsed.get("todo_items", [])
        print(f"   ✅ Extracted {len(calendar_events)} calendar events, {len(todo_items)} todos")
        return {"calendar_events": calendar_events, "todo_items": todo_items}

    except Exception as e:
        print(f"   ⚠️ Task extraction failed (non-fatal): {e}")
        return {"calendar_events": [], "todo_items": []}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Sends a user message to the LangChain agent and returns the response.
    Memory is scoped to session_id — each session has its own conversation history.

    Request body:
        video_id:      YouTube video ID from /analyze response
        message:       User's question or request
        session_id:    Unique session identifier (generate on frontend, e.g. uuid)
        video_title:   Optional — helps agent give better context in responses
        video_channel: Optional — YouTube channel name (used as artist name)
    """
    print(f"\n📥 [/chat] Session: {request.session_id} | Video: {request.video_id}")
    print(f"   Message: '{request.message}'")

    if "agent" not in agent_state:
        raise HTTPException(
            status_code=503,
            detail="Agent not initialized. Please restart the backend.",
        )

    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        result = await run_agent(
            agent=agent_state["agent"],
            message=request.message,
            session_id=request.session_id,
            video_id=request.video_id,
            video_title=request.video_title,
            video_channel=request.video_channel,
        )

        tasks = await extract_tasks_from_response(result["response"])

        return ChatResponse(
            response=result["response"],
            tools_used=result["tools_used"],
            session_id=result["session_id"],
            calendar_events=tasks["calendar_events"],
            todo_items=tasks["todo_items"],
        )

    except Exception as e:
        print(f"   ❌ /chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@app.post("/event-chat")
async def event_chat(request: dict):
    """
    Dedicated creative assistant for a specific calendar task.
    1. Searches marketing_knowledge ChromaDB for relevant guidelines
    2. Fetches song transcript for real content
    3. Uses both as context — only falls back to training data if DB empty
    """
    message = request.get("message", "")
    event_title = request.get("event_title", "")
    event_type = request.get("event_type", "general")
    event_date = request.get("event_date", "")
    video_title = request.get("video_title", "")
    video_channel = request.get("video_channel", "")
    video_id = request.get("video_id", "")
    doc_content = request.get("doc_content", "")

    print(f"\n📥 [/event-chat] Task: '{event_title}' | Message: '{message[:60]}'")

    if not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # 1. Search marketing knowledge base for relevant guidelines
    knowledge_context = ""
    try:
        from langchain_openai import OpenAIEmbeddings
        from langchain_pinecone import PineconeVectorStore
        from config import OPENAI_API_KEY
        import os

        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=OPENAI_API_KEY
        )
        vector_store = PineconeVectorStore(
            index_name=os.getenv("PINECONE_INDEX_NAME", "music-ai-chat"),
            embedding=embeddings,
            namespace="marketing_knowledge",
        )
        # Search using both the task type and the user message for better recall
        search_query = f"{event_type} {event_title} {message}"
        results = vector_store.similarity_search(search_query, k=3)
        if results:
            chunks = []
            for doc in results:
                header = doc.metadata.get("Header 2") or doc.metadata.get("Header 1") or ""
                chunks.append(f"[{header}]\n{doc.page_content}")
            knowledge_context = "\n\n---\n\n".join(chunks)
            print(f"   📚 Retrieved {len(results)} knowledge chunks from DB")
        else:
            print("   📚 No knowledge chunks found — using training data")
    except Exception as e:
        print(f"   ⚠️ Knowledge search failed: {e}")

    # 2. Fetch transcript for real song content
    transcript_context = ""
    if video_id:
        try:
            result = get_transcript_from_chroma(video_id)
            if result:
                transcript_context = result["transcript_text"][:800]
                print(f"   📄 Got transcript: {len(transcript_context)} chars")
        except Exception as e:
            print(f"   ⚠️ Could not fetch transcript: {e}")

    # 3. Build system prompt — DB knowledge first, training data as fallback
    # Determine tone based on task type
    tone_guide = {
        "spotify": "formal, professional, industry-standard",
        "deadline": "clear, direct, professional",
        "release": "professional with excitement",
        "youtube": "engaging, platform-native",
        "social_media": "casual, platform-matched — Instagram: visual storytelling; TikTok: punchy hook first; Twitter/X: concise wit",
        "promo": "energetic, promotional",
        "general": "professional but approachable",
    }
    tone = tone_guide.get(event_type, "professional but approachable")

    artist = video_channel if video_channel and video_channel != "Unknown Artist" else (video_title.split(" - ")[0] if " - " in video_title else video_channel)

    system_prompt = f"""You are a music industry professional. Write submission-ready content only.

Task: "{event_title}" | Type: {event_type} | Date: {event_date}
Song: "{video_title}" by "{artist}"
Tone: {tone}

{f"LYRICS:{chr(10)}{transcript_context}" if transcript_context else ""}
{f"GUIDELINES:{chr(10)}{knowledge_context}" if knowledge_context else ""}
{f"SAVED NOTES:{chr(10)}{doc_content[:400]}" if doc_content else ""}

Rules:
- Follow GUIDELINES strictly if provided
- Use LYRICS for specific song references
- No placeholders ever — write real content
- Spotify pitch: max 500 chars
- Output only the final content, no explanation"""

    try:
        client = AsyncOpenAI()
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0.7,
        )
        reply = response.choices[0].message.content.strip()
        print(f"   ✅ Event chat response ({len(reply)} chars)")
        return {"response": reply}

    except Exception as e:
        print(f"   ❌ /event-chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Event chat failed: {str(e)}")

@app.get("/transcript/{video_id}", response_model=TranscriptResponse)
async def get_transcript(video_id: str):
    """
    Reads all chunks from ChromaDB and returns the reconstructed transcript.
    Used by the frontend TranscriptPanel to display the raw lyrics/transcript.
    Returns 404 if the video has not been analyzed yet.
    """
    print(f"\n📥 [/transcript] video_id: {video_id}")

    try:
        result = get_transcript_from_chroma(video_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ChromaDB read failed: {str(e)}")

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No transcript found for video_id '{video_id}'. Run POST /analyze first.",
        )

    return TranscriptResponse(
        video_id=video_id,
        transcript_text=result["transcript_text"],
        word_count=result["word_count"],
        collection_name=f"video_{video_id}",
    )

@app.post("/analyze-audio")
async def analyze_audio(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    title: str = Form("Unknown Audio"),
    artist: str = Form("Unknown Artist")
):
    """
    Accepts an MP3 or WAV file, sends it to AssemblyAI for transcription,
    and embeds the resulting text into Pinecone.
    """
    print(f"\n📥 [/analyze-audio] File: {file.filename} | Session: {session_id}")

    # 1. Validate file format
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in ["mp3", "wav"]:
        raise HTTPException(status_code=400, detail="Only MP3 and WAV files are supported.")

    # 2. Read file bytes
    try:
        file_bytes = await file.read()
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read audio file: {str(e)}")

    # 3. Generate a stable internal ID based on session and filename
    import hashlib
    generated_video_id = hashlib.md5(f"{session_id}_{file.filename}".encode()).hexdigest()[:11]

# 4. Call AssemblyAI transcription logic via Official SDK
    try:
        import assemblyai as aai
        import os

        aai_key = os.getenv("ASSEMBLYAI_API_KEY")
        if not aai_key:
            raise ValueError("ASSEMBLYAI_API_KEY is not set in environment variables.")

        # Configure the official client
        aai.settings.api_key = aai_key
        transcriber = aai.Transcriber()

        # Custom configuration aligned with the latest AssemblyAI SDK standards
        config = aai.TranscriptionConfig(
            language_detection=True,
            speech_models=["universal-3-pro", "universal-2"]
        )

        print("   Saving audio to temp file for AssemblyAI...")
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        print(f"   Transcribing via AssemblyAI SDK: {tmp_path}")
        transcript = transcriber.transcribe(tmp_path, config=config)

        # Clean up temp file
        try:
            os.remove(tmp_path)
        except Exception:
            pass

        if transcript.status == aai.TranscriptStatus.error:
            raise RuntimeError(f"AssemblyAI error: {transcript.error}")

        transcript_text = transcript.text
        word_count = len(transcript_text.split())
        print(f"   Audio transcribed successfully: {word_count} words")

    except Exception as e:
        print(f"   ❌ AssemblyAI transcription failed: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Transcription failed: {str(e)}")

    # 5. Chunk and embed the resulting transcript into Pinecone
    try:
        embed_data = chunk_and_embed(
            video_id=generated_video_id,
            transcript_text=transcript_text,
            session_id=session_id
        )
        print(f"   Embedded audio transcript: {embed_data.get('chunks_created', 0)} chunks")
    except Exception as e:
        print(f"   ❌ Embedding failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")

    return {
        "video_id": generated_video_id,
        "transcript_text": transcript_text,
        "word_count": word_count,
        "title": title,
        "artist": artist,
        "channel": artist,
        "chunks_created": embed_data.get("chunks_created", 0),
        "status": "success"
    }

# ── Calendar Endpoints ─────────────────────────────────────────────────────────

@app.post("/calendar/events")
async def create_calendar_events(request: dict):
    try:
        session_id = request["session_id"]
        video_id = request["video_id"]
        events = request["events"]
        saved = await save_calendar_events(session_id, video_id, events)
        return {"saved": saved, "status": "ok"}
    except Exception as e:
        print(f"❌ Error in POST /calendar/events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/calendar/events/{session_id}")
async def read_calendar_events(session_id: str):
    try:
        events = await get_calendar_events(session_id)
        return {"events": events}
    except Exception as e:
        print(f"❌ Error in GET /calendar/events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/calendar/events/{event_id}")
async def edit_calendar_event(event_id: int, request: dict):
    try:
        updated = await update_calendar_event(event_id, request)
        return {"updated": updated, "status": "ok"}
    except Exception as e:
        print(f"❌ Error in PATCH /calendar/events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    try:
        deleted = await delete_session_data(session_id)
        return {"deleted": deleted, "status": "ok"}
    except Exception as e:
        print(f"❌ Error in DELETE /session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/calendar/events/{event_id}")
async def remove_calendar_event(event_id: int):
    try:
        deleted = await delete_calendar_event(event_id)
        return {"deleted": deleted, "status": "ok"}
    except Exception as e:
        print(f"❌ Error in DELETE /calendar/events: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@app.delete("/todos/session/{session_id}")
async def delete_session_todos(session_id: str):
    try:
        await supabase_client.table("todos").delete().eq("session_id", session_id).execute()
        return {"status": "ok"}
    except Exception as e:
        print(f"❌ Error deleting session todos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Todo Endpoints ─────────────────────────────────────────────────────────────

@app.post("/todos")
async def create_todos(request: dict):
    try:
        session_id = request["session_id"]
        video_id = request["video_id"]
        items = request["items"]
        saved = await save_todos(session_id, video_id, items)
        return {"saved": saved, "status": "ok"}
    except Exception as e:
        print(f"❌ Error in POST /todos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/todos/{session_id}")
async def read_todos(session_id: str):
    try:
        items = await get_todos(session_id)
        return {"items": items}
    except Exception as e:
        print(f"❌ Error in GET /todos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/todos/{todo_id}")
async def edit_todo(todo_id: int, request: dict):
    try:
        updated = await update_todo(todo_id, request)
        return {"updated": updated, "status": "ok"}
    except Exception as e:
        print(f"❌ Error in PATCH /todos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/todos/{todo_id}")
async def remove_todo(todo_id: int):
    try:
        deleted = await delete_todo(todo_id)
        return {"deleted": deleted, "status": "ok"}
    except Exception as e:
        print(f"❌ Error in DELETE /todos: {e}")
        raise HTTPException(status_code=500, detail=str(e))