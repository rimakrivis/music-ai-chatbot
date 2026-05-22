"""
main.py — FastAPI application entry point for Music AI Chatbot.

Endpoints:
  GET  /health                       — health check
  POST /analyze                      — fetch YouTube transcript + embed into Pinecone
  POST /analyze-lyrics               — embed manually pasted lyrics
  POST /analyze-audio                — upload MP3/WAV → Grok Whisper → Pinecone
  POST /chat                         — send a message to the LangChain agent
  POST /event-chat                   — creative assistant for a specific calendar task
  GET  /transcript/{video_id}        — read back transcript from Pinecone

  POST   /calendar/events
  GET    /calendar/events/{session_id}
  PATCH  /calendar/events/{event_id}
  DELETE /calendar/events/{event_id}
  DELETE /session/{session_id}       — clears all events + todos for a session

  POST   /todos
  GET    /todos/{session_id}
  PATCH  /todos/{todo_id}
  DELETE /todos/{todo_id}

Architecture notes:
  - Vector DB: Pinecone Serverless (namespaced per video)
  - No ChromaDB anywhere — legacy comments removed
  - Agent created once at startup, reused across all requests
  - Audio features extracted by librosa during /analyze-audio
  - Task extraction uses GPT-4o-mini with today's date injected
"""

from contextlib import asynccontextmanager
import os
import hashlib
import json
import tempfile

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import date

from openai import AsyncOpenAI

from database import (
    create_tables,
    save_calendar_events,
    get_calendar_events,
    update_calendar_event,
    delete_calendar_event,
    save_todos,
    get_todos,
    update_todo,
    delete_todo,
    delete_session_data,
)
from config import validate_config, IS_PRODUCTION, ENVIRONMENT, OPENAI_API_KEY, XAI_API_KEY
from pipeline import (
    fetch_transcript,
    chunk_and_embed,
    get_transcript_from_chroma,   # alias for get_transcript_from_pinecone
    extract_audio_features,
)
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
    video_channel: str = ""
    audio_features: dict | None = None   # optional — passed to agent for richer context


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
    namespace: str
    status: str


class TranscriptResponse(BaseModel):
    video_id: str
    transcript_text: str
    word_count: int
    namespace: str


class ChatResponse(BaseModel):
    response: str
    tools_used: list[str]
    session_id: str
    calendar_events: list[dict] = []
    todo_items: list[dict] = []


# ---------------------------------------------------------------------------
# App lifecycle — startup only (no blocking seed calls)
# ---------------------------------------------------------------------------

agent_state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once at server start before accepting any requests.

    Order:
      1. Validate all required environment variables.
      2. Create Supabase tables (idempotent).
      3. Create the LangChain agent once — reused for all /chat requests.

    Production note:
      Marketing knowledge is seeded separately via a one-off script.
      We do NOT seed on boot — it causes Render startup timeouts.
    """
    print("\n🚀 [startup] Starting Music AI backend...")
    print(f"🚀 [startup] Environment: {ENVIRONMENT}")

    # 1 — validate env vars (raises ValueError and halts boot on missing keys)
    try:
        validate_config()
    except ValueError as e:
        print(f"🚀 [startup] FATAL: {e}")
        raise

    print("🚀 [startup] Production mode — relying on persistent Pinecone for marketing knowledge")

    # 2 — ensure Supabase tables exist
    await create_tables()

    # 3 — create agent once
    agent_state["agent"] = create_music_agent()

    print("🚀 [startup] Backend ready ✓\n")

    yield

    print("\n[shutdown] Music AI backend shutting down")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Music AI Chatbot API",
    description="AI-powered music marketing assistant.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "message": "Music AI backend running",
        "environment": ENVIRONMENT,
        "agent_ready": "agent" in agent_state,
    }


# ---------------------------------------------------------------------------
# /analyze — YouTube URL → Pinecone
# ---------------------------------------------------------------------------

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    """
    Fetches YouTube transcript (4-method cascade) and embeds into Pinecone.
    Returns video metadata + embedding stats.

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
        print(f"   ❌ /analyze error: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    try:
        embed_data = chunk_and_embed(
            video_id=transcript_data["video_id"],
            transcript_text=transcript_data["transcript_text"],
        )
        print(f"   Embedded: {embed_data.get('chunks_created', 0)} chunks")
    except Exception as e:
        print(f"   ❌ /analyze embed error: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")

    return {**transcript_data, **embed_data}


# ---------------------------------------------------------------------------
# /analyze-lyrics — paste lyrics → Pinecone
# ---------------------------------------------------------------------------

@app.post("/analyze-lyrics", response_model=AnalyzeLyricsResponse)
async def analyze_lyrics(request: AnalyzeLyricsRequest):
    """
    Accepts manually pasted lyrics and embeds them into Pinecone.

    Use when:
      - The YouTube video has no captions
      - Auto-transcript quality is poor (common for Lithuanian, Latvian, Estonian)
      - You already have correct lyrics from Genius or another source
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
        print(f"   ❌ /analyze-lyrics error: {e}")
        raise HTTPException(status_code=500, detail=f"Lyrics embedding failed: {str(e)}")

    return AnalyzeLyricsResponse(
        video_id=request.video_id,
        title=request.title,
        artist=request.artist,
        word_count=len(request.lyrics_text.split()),
        chunks_created=embed_data["chunks_created"],
        namespace=embed_data["namespace"],
        status="success",
    )


# ---------------------------------------------------------------------------
# /analyze-audio — upload file → Grok Whisper → Pinecone
# ---------------------------------------------------------------------------

@app.post("/analyze-audio")
async def analyze_audio(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    title: str = Form("Unknown Audio"),
    artist: str = Form("Unknown Artist"),
):
    """
    Accepts an audio file (MP3, WAV, M4A, OGG, FLAC).
    Pipeline:
      1. Validate format
      2. Generate stable video_id from session + filename
      3. Save to temp file
      4. Extract audio features with librosa (BPM, energy, key, mode)
      5. Transcribe with AssemblyAI
      6. Chunk + embed into Pinecone
      7. Clean up temp file AFTER transcription is done
    """
    print(f"\n📥 [/analyze-audio] File: {file.filename} | Session: {session_id}")

    # 1 — validate format
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ["mp3", "wav", "m4a", "ogg", "flac"]:
        raise HTTPException(status_code=400, detail="Supported formats: MP3, WAV, M4A, OGG, FLAC.")

    # 2 — read bytes
    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        print(f"   File size: {len(file_bytes) / 1024 / 1024:.2f} MB")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read audio file: {str(e)}")

    # 3 — stable video_id
    generated_video_id = hashlib.md5(
        f"{session_id}_{file.filename}".encode()
    ).hexdigest()[:11]
    print(f"   Generated video_id: {generated_video_id}")

    # 4 — save to temp file (must stay on disk until AssemblyAI upload completes)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        print(f"   Saved to temp: {tmp_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save temp file: {str(e)}")

    transcript_text = ""
    audio_features = {}

    try:
        # 5 — librosa audio features (non-fatal)
        try:
            audio_features = extract_audio_features(tmp_path)
            print(f"   🎵 Audio features: {audio_features}")
        except Exception as e:
            print(f"   ⚠️ librosa failed (non-fatal): {e}")
            audio_features = {}

        # 6 — AssemblyAI transcription via direct REST API (bypasses SDK version issues)
        import httpx as _httpx
        import time as _time

        _aai_key = os.getenv("ASSEMBLYAI_API_KEY")
        _headers = {"authorization": _aai_key}

        print("   Uploading to AssemblyAI...")
        with open(tmp_path, "rb") as _f:
            _upload_resp = _httpx.post(
                "https://api.assemblyai.com/v2/upload",
                headers=_headers,
                content=_f.read(),
                timeout=120,
            )
        _upload_resp.raise_for_status()
        _upload_url = _upload_resp.json()["upload_url"]
        print(f"   ✅ Uploaded to AssemblyAI CDN")

        print("   Submitting transcription job...")
        _transcript_resp = _httpx.post(
            "https://api.assemblyai.com/v2/transcript",
            headers={**_headers, "content-type": "application/json"},
            json={
                "audio_url": _upload_url,
                "language_detection": True,
                "speech_models": ["universal-2"],
            },
            timeout=30,
        )
        if not _transcript_resp.is_success:
            raise HTTPException(
                status_code=422,
                detail=f"AssemblyAI job submission failed: {_transcript_resp.text}",
            )
        _transcript_id = _transcript_resp.json()["id"]
        print(f"   Job ID: {_transcript_id}")

        while True:
            _poll = _httpx.get(
                f"https://api.assemblyai.com/v2/transcript/{_transcript_id}",
                headers=_headers,
                timeout=30,
            )
            _poll.raise_for_status()
            _status = _poll.json()["status"]
            if _status == "completed":
                transcript_text = _poll.json()["text"].strip()
                print(f"   ✅ AssemblyAI complete ({len(transcript_text)} chars)")
                break
            elif _status == "error":
                raise HTTPException(
                    status_code=422,
                    detail=f"Transcription failed: {_poll.json().get('error')}",
                )
            else:
                print(f"   ⏳ {_status} — polling...")
                _time.sleep(3)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Transcription failed: {str(e)}")

    finally:
        # Always clean up — runs AFTER transcribe() returns (it's synchronous/blocking)
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                print("   Cleaned up temp file")
            except Exception:
                pass

    if not transcript_text:
        raise HTTPException(status_code=422, detail="Transcription returned empty text.")

    # 7 — chunk + embed into Pinecone
    try:
        embed_data = chunk_and_embed(
            video_id=generated_video_id,
            transcript_text=transcript_text,
        )
        print(f"   Embedded: {embed_data.get('chunks_created', 0)} chunks")
    except Exception as e:
        print(f"   ❌ Embedding failed: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")

    return {
        "video_id": generated_video_id,
        "transcript_text": transcript_text,
        "word_count": len(transcript_text.split()),
        "title": title if title != "Unknown Audio" else file.filename,
        "artist": artist,
        "channel": artist,
        "chunks_created": embed_data.get("chunks_created", 0),
        "audio_features": audio_features,
        "namespace": embed_data.get("namespace", f"video_{generated_video_id}"),
        "status": "success",
    }
# ---------------------------------------------------------------------------
# Task extraction helper — parses calendar events + todos from agent response
# ---------------------------------------------------------------------------

async def extract_tasks_from_response(response_text: str) -> dict:
    """
    Calls GPT-4o-mini to extract structured calendar events and todo items
    from the agent's markdown response text.

    Returns:
        {
            "calendar_events": [{"title": str, "date": str, "type": str}, ...],
            "todo_items":      [{"title": str, "due_date": str | None}, ...]
        }
    """
    print("   🗂️ [extract_tasks] Extracting tasks from response...")

    today = date.today().isoformat()  # e.g. "2026-05-23"

    system_prompt = f"""You are a task extraction assistant. Today's date is {today}.

Extract structured tasks from the music marketing plan below.

Return ONLY valid JSON — no markdown, no backticks, no explanation:
{{
  "calendar_events": [
    {{"title": "string", "date": "YYYY-MM-DD", "type": "release|deadline|promo|spotify|youtube|social_media|general"}}
  ],
  "todo_items": [
    {{"title": "string", "due_date": "YYYY-MM-DD or null"}}
  ]
}}

Rules:
- Only extract events that have a clear date or relative time hint (e.g. "2 weeks before release")
- Resolve relative dates using today = {today}
- If no date is mentioned, set due_date to null for todos and skip for calendar events
- type must be one of: release, deadline, promo, spotify, youtube, social_media, general
- If no tasks found, return {{"calendar_events": [], "todo_items": []}}"""

    try:
        client = AsyncOpenAI()
        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": response_text},
            ],
            temperature=0,
            max_tokens=1000,
        )
        raw = completion.choices[0].message.content.strip()
        print(f"   🗂️ [extract_tasks] Raw response: {raw[:120]}...")

        # Strip markdown fences if model ignores instructions
        clean = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean)

        calendar_events = parsed.get("calendar_events", [])
        todo_items = parsed.get("todo_items", [])

        print(f"   ✅ [extract_tasks] Found {len(calendar_events)} events, {len(todo_items)} todos")
        return {"calendar_events": calendar_events, "todo_items": todo_items}

    except json.JSONDecodeError as e:
        print(f"   ⚠️ [extract_tasks] JSON parse failed: {e} — returning empty tasks")
        return {"calendar_events": [], "todo_items": []}
    except Exception as e:
        print(f"   ⚠️ [extract_tasks] Extraction failed: {e} — returning empty tasks")
        return {"calendar_events": [], "todo_items": []}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    
    """
    Sends a user message to the LangChain ReAct agent and returns the response.
    Memory is scoped to session_id.

    Agent behaviour is controlled by the system prompt in agent.py:
      - Genre/mood only → search_transcript + analyze_marketing_potential (STOP)
      - Full plan → full chain including find_release_timing
      - How-to → search_marketing_knowledge
    """
    print(f"\n📥 [/chat] Session: {request.session_id} | Video: {request.video_id}")
    print(f"   Message: '{request.message}'")

    if "agent" not in agent_state:
        raise HTTPException(
            status_code=503,
            detail="Agent not initialised. Please restart the backend.",
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
            audio_features=request.audio_features,  # dict or None
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
        print(f"   ❌ /chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


# ---------------------------------------------------------------------------
# /event-chat — per-event creative assistant (EventDrawer)
# ---------------------------------------------------------------------------

@app.post("/event-chat")
async def event_chat(request: dict):
    """
    Creative assistant scoped to a specific calendar task.

    Pipeline:
      1. Search Pinecone marketing_knowledge for relevant guidelines
      2. Fetch song transcript from Pinecone for real lyrical content
      3. Build a tight system prompt and call GPT-4o
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

    # 1 — search marketing knowledge in Pinecone
    knowledge_context = ""
    try:
        from langchain_openai import OpenAIEmbeddings
        from langchain_pinecone import PineconeVectorStore

        _embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=OPENAI_API_KEY,
        )
        vector_store = PineconeVectorStore(
            index_name=os.getenv("PINECONE_INDEX_NAME", "music-ai-chat"),
            embedding=_embeddings,
            namespace="marketing_knowledge",
        )
        results = vector_store.similarity_search(
            f"{event_type} {event_title} {message}", k=3
        )
        if results:
            chunks = []
            for doc in results:
                header = doc.metadata.get("Header 2") or doc.metadata.get("Header 1") or ""
                chunks.append(f"[{header}]\n{doc.page_content}")
            knowledge_context = "\n\n---\n\n".join(chunks)
            print(f"   📚 Retrieved {len(results)} knowledge chunks")
        else:
            print("   📚 No knowledge chunks found — using training data")
    except Exception as e:
        print(f"   ⚠️ Knowledge search failed: {e}")

    # 2 — fetch transcript from Pinecone
    transcript_context = ""
    if video_id:
        try:
            result = get_transcript_from_chroma(video_id)
            if result:
                transcript_context = result["transcript_text"][:800]
                print(f"   📄 Got transcript: {len(transcript_context)} chars")
        except Exception as e:
            print(f"   ⚠️ Could not fetch transcript: {e}")

    # 3 — tone guide per event type
    tone_guide = {
        "spotify":      "formal, professional, industry-standard",
        "deadline":     "clear, direct, professional",
        "release":      "professional with excitement",
        "youtube":      "engaging, platform-native",
        "social_media": "casual, platform-matched — Instagram: visual storytelling; TikTok: punchy hook first; Twitter/X: concise wit",
        "promo":        "energetic, promotional",
        "general":      "professional but approachable",
    }
    tone = tone_guide.get(event_type, "professional but approachable")

    artist = (
        video_channel
        if video_channel and video_channel != "Unknown Artist"
        else (video_title.split(" - ")[0] if " - " in video_title else video_channel)
    )

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


# ---------------------------------------------------------------------------
# /transcript/{video_id} — read back from Pinecone
# ---------------------------------------------------------------------------

@app.get("/transcript/{video_id}", response_model=TranscriptResponse)
async def get_transcript(video_id: str):
    """
    Reads all chunks from Pinecone and returns the reconstructed transcript.
    Returns 404 if the video has not been analysed yet.
    """
    print(f"\n📥 [/transcript] video_id: {video_id}")

    try:
        result = get_transcript_from_chroma(video_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pinecone read failed: {str(e)}")

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No transcript found for video_id '{video_id}'. Run POST /analyze first.",
        )

    return TranscriptResponse(
        video_id=video_id,
        transcript_text=result["transcript_text"],
        word_count=result["word_count"],
        namespace=f"video_{video_id}",
    )


# ---------------------------------------------------------------------------
# Calendar endpoints
# ---------------------------------------------------------------------------

@app.post("/calendar/events")
async def create_calendar_events(request: dict):
    try:
        saved = await save_calendar_events(
            request["session_id"], request["video_id"], request["events"]
        )
        return {"saved": saved, "status": "ok"}
    except Exception as e:
        print(f"❌ POST /calendar/events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/calendar/events/{session_id}")
async def read_calendar_events(session_id: str):
    try:
        events = await get_calendar_events(session_id)
        return {"events": events}
    except Exception as e:
        print(f"❌ GET /calendar/events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/calendar/events/{event_id}")
async def edit_calendar_event(event_id: int, request: dict):
    try:
        updated = await update_calendar_event(event_id, request)
        return {"updated": updated, "status": "ok"}
    except Exception as e:
        print(f"❌ PATCH /calendar/events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/calendar/events/{event_id}")
async def remove_calendar_event(event_id: int):
    try:
        deleted = await delete_calendar_event(event_id)
        return {"deleted": deleted, "status": "ok"}
    except Exception as e:
        print(f"❌ DELETE /calendar/events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Session delete — clears all events + todos for a session
# ---------------------------------------------------------------------------

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    try:
        deleted = await delete_session_data(session_id)
        return {"deleted": deleted, "status": "ok"}
    except Exception as e:
        print(f"❌ DELETE /session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Todo endpoints
# ---------------------------------------------------------------------------

@app.post("/todos")
async def create_todos(request: dict):
    try:
        saved = await save_todos(
            request["session_id"], request["video_id"], request["items"]
        )
        return {"saved": saved, "status": "ok"}
    except Exception as e:
        print(f"❌ POST /todos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/todos/{session_id}")
async def read_todos(session_id: str):
    try:
        items = await get_todos(session_id)
        return {"items": items}
    except Exception as e:
        print(f"❌ GET /todos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/todos/{todo_id}")
async def edit_todo(todo_id: int, request: dict):
    try:
        updated = await update_todo(todo_id, request)
        return {"updated": updated, "status": "ok"}
    except Exception as e:
        print(f"❌ PATCH /todos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/todos/{todo_id}")
async def remove_todo(todo_id: int):
    try:
        deleted = await delete_todo(todo_id)
        return {"deleted": deleted, "status": "ok"}
    except Exception as e:
        print(f"❌ DELETE /todos: {e}")
        raise HTTPException(status_code=500, detail=str(e))
