# backend/pipeline.py
# -------------------------------------------------------
# Core data pipeline for the Music AI Chatbot.
#
# fetch_transcript()   → gets text from a YouTube video
# chunk_and_embed()    → splits text into chunks and stores
#                        them as vectors in ChromaDB
#
# Transcript strategy (in order):
#   1. YouTube Data API v3  — official Google API, never blocked
#   2. youtube-transcript-api — fast fallback for most videos
#   3. yt-dlp + AssemblyAI  — audio transcription for videos with no captions
#
# These two functions are called by POST /analyze in main.py.
# The ChromaDB collections they create are later searched
# by the agent's search_transcript tool.
# -------------------------------------------------------

import os
import re
import tempfile

import httpx
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
CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")

# YouTube Data API v3 base URL
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


# -------------------------------------------------------
# HELPER — count tokens in a text string
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
# -------------------------------------------------------
def extract_video_id(youtube_url: str) -> str:
    print(f"[pipeline] Extracting video ID from URL: {youtube_url}")

    short_url_match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", youtube_url)
    if short_url_match:
        video_id = short_url_match.group(1)
        print(f"[pipeline] Found video ID (short URL): {video_id}")
        return video_id

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
# HELPER — fetch video metadata using YouTube Data API v3
# Falls back to yt-dlp if API key not set
# -------------------------------------------------------
def fetch_video_metadata(video_id: str) -> dict:
    print(f"[pipeline] Fetching metadata for video ID: {video_id}")

    api_key = os.getenv("YOUTUBE_API_KEY")

    # --- Try YouTube Data API v3 first ---
    if api_key:
        try:
            url = f"{YOUTUBE_API_BASE}/videos?part=snippet,contentDetails&id={video_id}&key={api_key}"
            response = httpx.get(url, timeout=10)
            data = response.json()
            items = data.get("items", [])
            if items:
                snippet = items[0]["snippet"]
                duration_iso = items[0]["contentDetails"]["duration"]
                # Parse ISO 8601 duration (PT3M33S → 213 seconds)
                duration_match = re.search(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_iso)
                hours = int(duration_match.group(1) or 0)
                minutes = int(duration_match.group(2) or 0)
                seconds = int(duration_match.group(3) or 0)
                duration = hours * 3600 + minutes * 60 + seconds
                metadata = {
                    "title": snippet.get("title", "Unknown Title"),
                    "channel": snippet.get("channelTitle", "Unknown Channel"),
                    "duration": duration,
                    "language": snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage") or None,
                }
                print(f"[pipeline] Metadata fetched via YouTube API: {metadata['title']} by {metadata['channel']}")
                return metadata
        except Exception as e:
            print(f"[pipeline] YouTube API metadata failed: {e}, trying yt-dlp...")

    # --- Fall back to yt-dlp ---
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {"quiet": True, "skip_download": True, "no_warnings": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            metadata = {
                "title": info.get("title", "Unknown Title"),
                "channel": info.get("uploader", "Unknown Channel"),
                "duration": info.get("duration", 0),
                "language": info.get("language") or None,
            }
            print(f"[pipeline] Metadata fetched via yt-dlp: {metadata['title']} by {metadata['channel']}")
            return metadata
    except Exception as e:
        print(f"[pipeline] Warning: Could not fetch metadata: {e}")
        return {"title": "Unknown Title", "channel": "Unknown Channel", "duration": 0, "language": None}


# -------------------------------------------------------
# HELPER — fetch captions via YouTube Data API v3
#
# Uses the official Google API — never blocked on any server.
# Requires YOUTUBE_API_KEY environment variable.
# Returns transcript text or None if captions not available.
# -------------------------------------------------------
def fetch_transcript_youtube_api(video_id: str) -> str | None:
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print(f"[pipeline] YOUTUBE_API_KEY not set, skipping YouTube API")
        return None

    print(f"[pipeline] Attempting YouTube Data API v3...")

    try:
        # Step 1: list available caption tracks
        captions_url = f"{YOUTUBE_API_BASE}/captions?part=snippet&videoId={video_id}&key={api_key}"
        response = httpx.get(captions_url, timeout=10)
        data = response.json()

        if "error" in data:
            print(f"[pipeline] YouTube API error: {data['error']['message']}")
            return None

        items = data.get("items", [])
        if not items:
            print(f"[pipeline] No caption tracks found via YouTube API")
            return None

        print(f"[pipeline] Found {len(items)} caption track(s)")

        # Step 2: pick best caption track
        # Priority: English auto-generated > any auto-generated > English manual > any manual
        caption_id = None
        caption_lang = None

        # First pass: English auto-generated
        for item in items:
            lang = item["snippet"]["language"]
            track_kind = item["snippet"]["trackKind"]
            if lang.startswith("en") and track_kind == "asr":
                caption_id = item["id"]
                caption_lang = lang
                break

        # Second pass: any auto-generated
        if not caption_id:
            for item in items:
                track_kind = item["snippet"]["trackKind"]
                if track_kind == "asr":
                    caption_id = item["id"]
                    caption_lang = item["snippet"]["language"]
                    break

        # Third pass: any manual caption
        if not caption_id:
            caption_id = items[0]["id"]
            caption_lang = items[0]["snippet"]["language"]

        print(f"[pipeline] Using caption track: {caption_lang} (id: {caption_id})")

        # Step 3: download caption track as SBV format
        caption_url = f"{YOUTUBE_API_BASE}/captions/{caption_id}?tfmt=sbv&key={api_key}"
        caption_response = httpx.get(caption_url, timeout=15)

        if caption_response.status_code != 200:
            print(f"[pipeline] Caption download failed: HTTP {caption_response.status_code}")
            return None

        raw = caption_response.text

        # Step 4: strip SBV timestamps and clean text
        # SBV format: timestamp line like "0:00:01.000,0:00:03.500" followed by text
        lines = []
        for line in raw.splitlines():
            line = line.strip()
            if re.match(r"^\d+:\d+:\d+\.\d+,\d+:\d+:\d+\.\d+$", line):
                continue
            if not line or line.isdigit():
                continue
            lines.append(line)

        transcript_text = " ".join(lines).strip()

        if not transcript_text:
            print(f"[pipeline] Caption track was empty after cleaning")
            return None

        print(f"[pipeline] ✅ Transcript fetched via YouTube Data API v3")
        print(f"[pipeline] Word count: {len(transcript_text.split())}")
        return transcript_text

    except Exception as e:
        print(f"[pipeline] YouTube Data API failed: {type(e).__name__}: {e}")
        return None


# -------------------------------------------------------
# FUNCTION 1 — fetch_transcript(youtube_url)
#
# Tries 3 methods in order:
#   1. YouTube Data API v3        — official, never blocked
#   2. youtube-transcript-api     — fast, works for most videos
#   3. yt-dlp + AssemblyAI        — audio transcription fallback
# -------------------------------------------------------
def fetch_transcript(youtube_url: str) -> dict:
    print(f"\n[pipeline] ── Starting fetch_transcript ──")
    print(f"[pipeline] URL: {youtube_url}")

    video_id = extract_video_id(youtube_url)
    metadata = fetch_video_metadata(video_id)

    transcript_text = None
    source = None

    # --- Attempt 1: YouTube Data API v3 ---
    transcript_text = fetch_transcript_youtube_api(video_id)
    if transcript_text:
        source = "youtube_data_api"

    # --- Attempt 2: youtube-transcript-api ---
    if transcript_text is None:
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

            transcripts = ytt_api.list(video_id)
            try:
                transcript = transcripts.find_generated_transcript(['en', 'lt', 'de', 'fr', 'es', 'it', 'pt', 'ru', 'ja', 'ko'])
            except Exception:
                transcript = transcripts.find_manually_created_transcript(['en', 'lt', 'de', 'fr', 'es', 'it', 'pt', 'ru', 'ja', 'ko'])

            transcript_list = transcript.fetch()
            transcript_text = " ".join([entry.text for entry in transcript_list])
            source = "youtube_transcript_api"
            print(f"[pipeline] ✅ Transcript fetched via youtube-transcript-api")
            print(f"[pipeline] Word count: {len(transcript_text.split())}")

        except NoTranscriptFound:
            print(f"[pipeline] No transcript found, falling back to AssemblyAI...")
        except Exception as e:
            print(f"[pipeline] youtube-transcript-api failed: {type(e).__name__}: {e}")
            print(f"[pipeline] Falling back to yt-dlp + AssemblyAI...")

    # --- Attempt 3: yt-dlp + AssemblyAI ---
    if transcript_text is None:
        try:
            print(f"[pipeline] Downloading audio with yt-dlp...")

            with tempfile.TemporaryDirectory() as tmp_dir:
                audio_path = os.path.join(tmp_dir, "audio.mp3")

                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": os.path.join(tmp_dir, "audio"),
                    "quiet": True,
                    "no_warnings": True,
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "128",
                    }],
                }

                url = f"https://www.youtube.com/watch?v={video_id}"
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                print(f"[pipeline] Audio downloaded. Sending to AssemblyAI...")
                print(f"[pipeline] AssemblyAI will auto-detect the language...")

                aai.settings.api_key = ASSEMBLYAI_API_KEY
                config = aai.TranscriptionConfig(
                    language_detection=True,
                    speech_models=[aai.SpeechModel.universal]
                )
                transcriber = aai.Transcriber(config=config)
                aai_transcript = transcriber.transcribe(audio_path)

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
                f"[pipeline] All transcript methods failed for video {video_id}.\n"
                f"Last error: {e}"
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
# -------------------------------------------------------
def chunk_and_embed(video_id: str, transcript_text: str) -> dict:
    print(f"\n[pipeline] ── Starting chunk_and_embed ──")
    print(f"[pipeline] Video ID: {video_id}")
    print(f"[pipeline] Transcript length: {len(transcript_text)} characters")

    total_tokens = count_tokens(transcript_text)
    print(f"[pipeline] Full transcript: {total_tokens} tokens")

    print(f"[pipeline] Splitting transcript into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_text(transcript_text)
    print(f"[pipeline] Created {len(chunks)} chunks")

    avg_tokens = sum(count_tokens(c) for c in chunks) // len(chunks)
    print(f"[pipeline] Average chunk size: {avg_tokens} tokens")

    print(f"[pipeline] Initialising OpenAI embeddings (text-embedding-3-small)...")
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=OPENAI_API_KEY
    )

    print(f"[pipeline] Connecting to ChromaDB...")
    collection_name = f"video_{video_id}"

    chroma_client = chromadb.EphemeralClient() if IS_PRODUCTION else chromadb.PersistentClient(path=CHROMA_DB_PATH)
    existing_collections = [c.name for c in chroma_client.list_collections()]
    if collection_name in existing_collections:
        print(f"[pipeline] Collection '{collection_name}' already exists — deleting and recreating...")
        chroma_client.delete_collection(name=collection_name)

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
# Used by the agent's extract_lyrics tool.
# Returns None if the video has not been analyzed yet.
# -------------------------------------------------------
def get_transcript_from_chroma(video_id: str) -> dict | None:
    collection_name = f"video_{video_id}"
    print(f"[get_transcript_from_chroma] Looking up: {collection_name}")

    try:
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
