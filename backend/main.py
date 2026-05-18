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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import create_tables, save_calendar_events, get_calendar_events, update_calendar_event, delete_calendar_event, save_todos, get_todos, update_todo, delete_todo

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
                collection_name="marketing_knowledge",
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

        return ChatResponse(
            response=result["response"],
            tools_used=result["tools_used"],
            session_id=result["session_id"],
        )

    except Exception as e:
        print(f"   ❌ /chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


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


@app.delete("/calendar/events/{event_id}")
async def remove_calendar_event(event_id: int):
    try:
        deleted = await delete_calendar_event(event_id)
        return {"deleted": deleted, "status": "ok"}
    except Exception as e:
        print(f"❌ Error in DELETE /calendar/events: {e}")
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