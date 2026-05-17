# backend/pipeline.py
# -------------------------------------------------------
# Core data pipeline for the Music AI Chatbot.
#
# fetch_transcript()   → gets text from a YouTube video
# chunk_and_embed()    → splits text into chunks and stores
#                        them as vectors in ChromaDB
#
# These two functions are called by POST /analyze in main.py.
# The ChromaDB collections they create are later searched
# by the agent's search_transcript tool (Day 2).
# -------------------------------------------------------

import os
import re

import tiktoken
import yt_dlp
import chromadb
import assemblyai as aai
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

from config import OPENAI_API_KEY, ASSEMBLYAI_API_KEY, IS_PRODUCTION


# Path where ChromaDB saves its data on disk.
# Stays inside the backend/ folder.
CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")


# -------------------------------------------------------
# HELPER — count tokens in a text string
# Used before and after splitting to log size and cost.
# model: text-embedding-3-small matches our embedding model
# -------------------------------------------------------
def count_tokens(text: str, model: str = "text-embedding-3-small") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
        tokens = encoding.encode(text)
        print(f"[TOKEN COUNT] {len(tokens)} tokens")
        return len(tokens)
    except Exception as e:
        print(f"[TOKEN COUNT ERROR] {e}")
        return 0


# -------------------------------------------------------
# HELPER — extract video ID from any YouTube URL format
# Handles:
#   https://www.youtube.com/watch?v=H5v3kku4y6Q
#   https://youtu.be/H5v3kku4y6Q
#   https://www.youtube.com/watch?v=H5v3kku4y6Q&t=30s
# -------------------------------------------------------
def extract_video_id(youtube_url: str) -> str:
    print(f"[pipeline] Extracting video ID from URL: {youtube_url}")

    # Match youtu.be/ID short URLs
    short_url_match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", youtube_url)
    if short_url_match:
        video_id = short_url_match.group(1)
        print(f"[pipeline] Found video ID (short URL): {video_id}")
        return video_id

    # Match youtube.com/watch?v=ID long URLs
    long_url_match = re.search(r"v=([a-zA-Z0-9_-]{11})", youtube_url)
    if long_url_match:
        video_id = long_url_match.group(1)
        print(f"[pipeline] Found video ID (long URL): {video_id}")
        return video_id

    raise ValueError(
        f"[pipeline] Could not extract video ID from URL: {youtube_url}\n"
        f"Make sure it is a valid YouTube URL."
    )


# -------------------------------------------------------
# HELPER — fetch video metadata (title, channel, duration)
# Uses yt-dlp in info-only mode (no download)
# -------------------------------------------------------
def fetch_video_metadata(video_id: str) -> dict:
    print(f"[pipeline] Fetching metadata for video ID: {video_id}")
    url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            metadata = {
                "title": info.get("title", "Unknown Title"),
                "channel": info.get("uploader", "Unknown Channel"),
                "duration": info.get("duration", 0),
                "language": info.get("language") or None,
            }
            print(f"[pipeline] Metadata fetched: {metadata['title']} by {metadata['channel']}")
            return metadata
    except Exception as e:
        print(f"[pipeline] Warning: Could not fetch metadata: {e}")
        return {"title": "Unknown Title", "channel": "Unknown Channel", "duration": 0, "language": None}


# -------------------------------------------------------
# FUNCTION 1 — fetch_transcript(youtube_url)
#
# Step 1: Try youtube-transcript-api (fast, no download)
#         Uses Webshare proxy if credentials are set (needed on Render)
# Step 2: If captions disabled, fall back to:
#         AssemblyAI direct YouTube URL transcription
#         No yt-dlp download needed — works on cloud servers
#         AssemblyAI auto-detects language — works for
#         Lithuanian, English, Spanish, and 100+ languages
# Returns a dict with all video info + transcript text
# -------------------------------------------------------
def fetch_transcript(youtube_url: str) -> dict:
    print(f"\n[pipeline] ── Starting fetch_transcript ──")
    print(f"[pipeline] URL: {youtube_url}")

    video_id = extract_video_id(youtube_url)
    metadata = fetch_video_metadata(video_id)

    transcript_text = None
    source = None

    # --- Attempt 1: youtube-transcript-api ---
    # Uses Webshare proxy on Render so YouTube doesn't block the request
    print(f"[pipeline] Attempting youtube-transcript-api...")
    try:
        from youtube_transcript_api.proxies import WebshareProxyConfig

        if os.getenv("WEBSHARE_USERNAME"):
            print(f"[pipeline] Using Webshare proxy...")
            ytt_api = YouTubeTranscriptApi(
                proxy_config=WebshareProxyConfig(
                    proxy_username=os.getenv("WEBSHARE_USERNAME", ""),
                    proxy_password=os.getenv("WEBSHARE_PASSWORD", ""),
                )
            )
        else:
            print(f"[pipeline] No proxy configured, connecting directly...")
            ytt_api = YouTubeTranscriptApi()

        transcript_list = ytt_api.fetch(video_id, languages=['en', 'lt', 'de', 'fr', 'es', 'it', 'pt', 'ru', 'ja', 'ko', 'nl', 'pl', 'sv', 'da', 'fi', 'nb'])
        transcript_text = " ".join([entry.text for entry in transcript_list])
        source = "youtube_api"
        print(f"[pipeline] ✅ Transcript fetched via youtube-transcript-api")
        print(f"[pipeline] Word count: {len(transcript_text.split())}")

    except NoTranscriptFound:
        print(f"[pipeline] No transcript found, falling back to AssemblyAI...")

    except Exception as e:
        print(f"[pipeline] youtube-transcript-api failed: {type(e).__name__}: {e}")
        print(f"[pipeline] Falling back to AssemblyAI...")

    # --- Attempt 2: AssemblyAI direct YouTube URL ---
    # No yt-dlp download needed — AssemblyAI fetches audio directly from YouTube
    # This works on cloud servers (Render) where yt-dlp gets bot-blocked
    if transcript_text is None:
        try:
            youtube_url_direct = f"https://www.youtube.com/watch?v={video_id}"
            print(f"[pipeline] Sending YouTube URL directly to AssemblyAI...")
            print(f"[pipeline] AssemblyAI will auto-detect the language...")

            # Configure AssemblyAI with language detection
            # Works for Lithuanian, English, Spanish, French, and 100+ languages
            aai.settings.api_key = ASSEMBLYAI_API_KEY
            config = aai.TranscriptionConfig(
                language_detection=True,
                speech_models=[aai.SpeechModel.universal]
            )
            transcriber = aai.Transcriber(config=config)
            aai_transcript = transcriber.transcribe(youtube_url_direct)

            if aai_transcript.status == aai.TranscriptStatus.error:
                raise RuntimeError(f"AssemblyAI error: {aai_transcript.error}")

            transcript_text = aai_transcript.text.strip()
            detected_language = getattr(aai_transcript, 'language_code', 'unknown')
            source = "assemblyai"
            print(f"[pipeline] ✅ Transcript fetched via AssemblyAI")
            print(f"[pipeline] Detected language: {detected_language}")
            print(f"[pipeline] Word count: {len(transcript_text.split())}")

        except Exception as e:
            raise RuntimeError(
                f"[pipeline] Both transcript methods failed for video {video_id}.\n"
                f"AssemblyAI error: {e}"
            )

    result = {
        "video_id": video_id,
        "title": metadata["title"],
        "channel": metadata["channel"],
        "duration": metadata["duration"],
        "transcript_text": transcript_text,
        "word_count": len(transcript_text.split()),
        "source": source,
    }

    print(f"[pipeline] ── fetch_transcript complete ──\n")
    return result


# -------------------------------------------------------
# FUNCTION 2 — chunk_and_embed(video_id, transcript_text)
#
# Takes the raw transcript text and:
# 1. Splits it into overlapping chunks (500 chars, 50 overlap)
# 2. Converts each chunk into an embedding vector via OpenAI
# 3. Stores everything in ChromaDB under collection "video_{video_id}"
#
# Why overlap? So that a sentence split across two chunks
# still appears in full in at least one of them.
# -------------------------------------------------------
def chunk_and_embed(video_id: str, transcript_text: str) -> dict:
    print(f"\n[pipeline] ── Starting chunk_and_embed ──")
    print(f"[pipeline] Video ID: {video_id}")
    print(f"[pipeline] Transcript length: {len(transcript_text)} characters")

    # --- Token count BEFORE splitting ---
    total_tokens = count_tokens(transcript_text)
    print(f"[pipeline] Full transcript: {total_tokens} tokens")

    # --- Step 1: Split transcript into chunks ---
    print(f"[pipeline] Splitting transcript into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_text(transcript_text)
    print(f"[pipeline] Created {len(chunks)} chunks")

    # --- Token count AFTER splitting ---
    avg_tokens = sum(count_tokens(c) for c in chunks) // len(chunks)
    print(f"[pipeline] Average chunk size: {avg_tokens} tokens")

    # --- Step 2: Set up OpenAI embeddings ---
    print(f"[pipeline] Initialising OpenAI embeddings (text-embedding-3-small)...")
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=OPENAI_API_KEY
    )

    # --- Step 3: Set up ChromaDB ---
    print(f"[pipeline] Connecting to ChromaDB at: {CHROMA_DB_PATH}")
    collection_name = f"video_{video_id}"

    # Production (Render): in-memory only — no disk persistence on free tier
    # Local: saves to ./chroma_db so data survives restarts
    chroma_client = chromadb.EphemeralClient() if IS_PRODUCTION else chromadb.PersistentClient(path=CHROMA_DB_PATH)
    existing_collections = [c.name for c in chroma_client.list_collections()]
    if collection_name in existing_collections:
        print(f"[pipeline] Collection '{collection_name}' already exists — deleting and recreating...")
        chroma_client.delete_collection(name=collection_name)

    # --- Step 4: Store chunks + embeddings in ChromaDB ---
    print(f"[pipeline] Embedding chunks and storing in ChromaDB...")
    print(f"[pipeline] This may take 10-30 seconds depending on transcript length...")

    if IS_PRODUCTION:
        vector_store = Chroma.from_texts(
            texts=chunks,
            embedding=embeddings,
            collection_name=collection_name,
            client=chroma_client,
        )
    else:
        vector_store = Chroma.from_texts(
            texts=chunks,
            embedding=embeddings,
            collection_name=collection_name,
            persist_directory=CHROMA_DB_PATH,
        )

    print(f"[pipeline] ✅ {len(chunks)} chunks stored in collection '{collection_name}'")
    print(f"[pipeline] ── chunk_and_embed complete ──\n")

    return {
        "video_id": video_id,
        "chunks_created": len(chunks),
        "collection_name": collection_name,
        "status": "success",
    }


# -------------------------------------------------------
# HELPER — get_transcript_from_chroma(video_id)
#
# Reads all chunks back from ChromaDB and reassembles them.
# Used by the agent's extract_lyrics tool (Day 2).
# Returns None if the video has not been analyzed yet.
# -------------------------------------------------------
def get_transcript_from_chroma(video_id: str) -> dict | None:
    collection_name = f"video_{video_id}"
    print(f"[get_transcript_from_chroma] Looking up: {collection_name}")

    try:
        # Must use same client type as chunk_and_embed — EphemeralClient in production
        client = chromadb.EphemeralClient() if IS_PRODUCTION else chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = client.get_collection(name=collection_name)
        results = collection.get(include=["documents"])

        if not results["documents"]:
            return None

        full_text = " ".join(results["documents"])
        return {
            "transcript_text": full_text,
            "word_count": len(full_text.split()),
        }

    except Exception as e:
        print(f"[get_transcript_from_chroma] Not found: {e}")
        return None
