# backend/pipeline.py
# -------------------------------------------------------
# Core data pipeline for the Music AI Chatbot.
#
# fetch_transcript()      → gets text from a YouTube video
# chunk_and_embed()       → splits text into chunks and stores
#                           them as vectors in Pinecone
# detect_genres()          → detects genre + subgenres via Essentia Discogs-EffNet
#                           called during yt-dlp download (audio already on disk)
#
# Transcript strategy (in order):
#   1. Supadata API         — works from any server, never blocked
#   2. YouTube Data API v3  — official Google API fallback
#   3. youtube-transcript-api — direct fallback
#   4. yt-dlp + AssemblyAI  — audio transcription last resort
#
# These functions are called by POST /analyze and POST /analyze-audio in main.py.
# -------------------------------------------------------

import os
import re
import tempfile
import time

import httpx
import tiktoken
import yt_dlp
import assemblyai as aai
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

from config import OPENAI_API_KEY, ASSEMBLYAI_API_KEY


# YouTube Data API v3 base URL
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

# Pinecone config
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "music-ai")


# -------------------------------------------------------
# SINGLETON PINECONE CLIENT
# -------------------------------------------------------
_pinecone_client = None
_pinecone_index = None

def get_pinecone_index():
    global _pinecone_client, _pinecone_index
    if _pinecone_index is None:
        print(f"[pipeline] Initialising Pinecone client...")
        _pinecone_client = Pinecone(api_key=PINECONE_API_KEY)

        existing = [i.name for i in _pinecone_client.list_indexes()]
        if PINECONE_INDEX_NAME not in existing:
            print(f"[pipeline] Creating Pinecone index '{PINECONE_INDEX_NAME}'...")
            _pinecone_client.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=1536,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            while not _pinecone_client.describe_index(PINECONE_INDEX_NAME).status["ready"]:
                print(f"[pipeline] Waiting for index to be ready...")
                time.sleep(2)

        _pinecone_index = _pinecone_client.Index(PINECONE_INDEX_NAME)
        print(f"[pipeline] ✅ Pinecone index '{PINECONE_INDEX_NAME}' ready")
    return _pinecone_index


# -------------------------------------------------------
# HELPER — count tokens
# -------------------------------------------------------
def count_tokens(text: str, model: str = "text-embedding-3-small") -> int:
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
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
# HELPER — fetch video metadata
# -------------------------------------------------------
def fetch_video_metadata(video_id: str) -> dict:
    print(f"[pipeline] Fetching metadata for video ID: {video_id}")
    api_key = os.getenv("YOUTUBE_API_KEY")

    if api_key:
        try:
            url = f"{YOUTUBE_API_BASE}/videos?part=snippet,contentDetails&id={video_id}&key={api_key}"
            response = httpx.get(url, timeout=10)
            data = response.json()
            items = data.get("items", [])
            if items:
                snippet = items[0]["snippet"]
                duration_iso = items[0]["contentDetails"]["duration"]
                duration_match = re.search(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_iso)
                hours = int(duration_match.group(1) or 0)
                minutes = int(duration_match.group(2) or 0)
                seconds = int(duration_match.group(3) or 0)
                metadata = {
                    "title": snippet.get("title", "Unknown Title"),
                    "channel": snippet.get("channelTitle", "Unknown Channel"),
                    "duration": hours * 3600 + minutes * 60 + seconds,
                    "language": snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage") or None,
                }
                print(f"[pipeline] Metadata fetched via YouTube API: {metadata['title']} by {metadata['channel']}")
                return metadata
        except Exception as e:
            print(f"[pipeline] YouTube API metadata failed: {e}, trying yt-dlp...")

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
# -------------------------------------------------------
def fetch_transcript_youtube_api(video_id: str) -> str | None:
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return None

    print(f"[pipeline] Attempting YouTube Data API v3...")
    try:
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

        caption_id = None
        caption_lang = None

        for item in items:
            lang = item["snippet"]["language"]
            track_kind = item["snippet"]["trackKind"]
            if lang.startswith("en") and track_kind == "asr":
                caption_id = item["id"]
                caption_lang = lang
                break

        if not caption_id:
            for item in items:
                if item["snippet"]["trackKind"] == "asr":
                    caption_id = item["id"]
                    caption_lang = item["snippet"]["language"]
                    break

        if not caption_id:
            caption_id = items[0]["id"]
            caption_lang = items[0]["snippet"]["language"]

        print(f"[pipeline] Using caption track: {caption_lang}")

        caption_url = f"{YOUTUBE_API_BASE}/captions/{caption_id}?tfmt=sbv&key={api_key}"
        caption_response = httpx.get(caption_url, timeout=15)

        if caption_response.status_code != 200:
            print(f"[pipeline] Caption download failed: HTTP {caption_response.status_code}")
            return None

        raw = caption_response.text
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
# Tries 4 methods in order. When yt-dlp downloads audio for
# AssemblyAI (Attempt 4), Essentia also runs on the same file
# to extract genre features — no extra download cost.
# -------------------------------------------------------
def fetch_transcript(youtube_url: str) -> dict:
    print(f"\n[pipeline] ── Starting fetch_transcript ──")
    print(f"[pipeline] URL: {youtube_url}")

    video_id = extract_video_id(youtube_url)
    metadata = fetch_video_metadata(video_id)

    transcript_text = None
    source = None
    audio_features = {}  # populated only when yt-dlp downloads audio

    # --- Attempt 1: Supadata API ---
    try:
        supadata_key = os.getenv("SUPADATA_API_KEY")
        if supadata_key:
            print(f"[pipeline] Attempting Supadata API...")
            response = httpx.get(
                "https://api.supadata.ai/v1/youtube/transcript",
                params={"videoId": video_id, "text": "true"},
                headers={"x-api-key": supadata_key},
                timeout=30,
            )
            if response.status_code == 200:
                data = response.json()
                transcript_text = data.get("content", "")
                if transcript_text:
                    source = "supadata"
                    print(f"[pipeline] ✅ Transcript fetched via Supadata")
                    print(f"[pipeline] Word count: {len(transcript_text.split())}")
    except Exception as e:
        print(f"[pipeline] Supadata failed: {e}")

    # --- Attempt 2: YouTube Data API v3 ---
    if not transcript_text:
        transcript_text = fetch_transcript_youtube_api(video_id)
        if transcript_text:
            source = "youtube_data_api"

    # --- Attempt 3: youtube-transcript-api ---
    if not transcript_text:
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

    # --- Attempt 4: yt-dlp + AssemblyAI ---
    # Audio is already downloaded here — run Essentia genre detection on it for free
    if not transcript_text:
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
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

                # ── Extract genre features while file is on disk ──
                # Essentia runs on the same file already downloaded for AssemblyAI.
                print(f"[pipeline] Running Essentia genre detection on downloaded audio...")
                try:
                    from tools.genre_detect import detect_genres
                    audio_features = detect_genres(audio_path)
                except Exception as genre_err:
                    print(f"[pipeline] ⚠️ Genre detection failed (non-fatal): {genre_err}")
                    audio_features = {}

                print(f"[pipeline] Audio downloaded. Sending to AssemblyAI...")
                aai.settings.api_key = ASSEMBLYAI_API_KEY
                config = aai.TranscriptionConfig(
                    language_detection=True,
                    speech_models=[aai.SpeechModel.universal],
                )
                transcriber = aai.Transcriber(config=config)
                aai_transcript = transcriber.transcribe(audio_path)

                if aai_transcript.status == aai.TranscriptStatus.error:
                    raise RuntimeError(f"AssemblyAI error: {aai_transcript.error}")

                transcript_text = aai_transcript.text.strip()
                source = "assemblyai"
                print(f"[pipeline] ✅ Transcript fetched via AssemblyAI")
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
        "audio_features": audio_features,  # {} when transcript came from captions
    }

    if audio_features:
        top = audio_features.get('top_genres', [])
        if top:
            g = top[0]
            print(f"[pipeline] 🎵 Genre detected: {g.get('genre')} › {g.get('subgenre')} "
                  f"({round(g.get('confidence', 0) * 100, 1)}%)")
    else:
        print(f"[pipeline] ℹ️  No audio features (transcript came from captions — no download needed)")

    print(f"[pipeline] ── fetch_transcript complete ──\n")
    return result


# -------------------------------------------------------
# FUNCTION 2 — chunk_and_embed(video_id, transcript_text)
# -------------------------------------------------------
def chunk_and_embed(video_id: str, transcript_text: str, session_id: str = None) -> dict:
    print(f"\n[pipeline] ── Starting chunk_and_embed ──")
    print(f"[pipeline] Video ID: {video_id}")
    print(f"[pipeline] Transcript length: {len(transcript_text)} characters")

    total_tokens = count_tokens(transcript_text)
    print(f"[pipeline] Full transcript: {total_tokens} tokens")

    if not transcript_text.strip():
        raise ValueError("[pipeline] Transcript is empty — cannot embed.")

    print(f"[pipeline] Splitting transcript into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_text(transcript_text)
    print(f"[pipeline] Created {len(chunks)} chunks")

    if not chunks:
        raise ValueError("[pipeline] Transcript produced no chunks — it may be empty.")

    print(f"[pipeline] Initialising OpenAI embeddings (text-embedding-3-small)...")
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=OPENAI_API_KEY
    )

    namespace = f"video_{video_id}"
    print(f"[pipeline] Storing chunks in Pinecone namespace '{namespace}'...")

    index = get_pinecone_index()
    try:
        index.delete(delete_all=True, namespace=namespace)
        print(f"[pipeline] Cleared existing vectors for namespace '{namespace}'")
    except Exception:
        pass

    PineconeVectorStore.from_texts(
        texts=chunks,
        embedding=embeddings,
        index_name=PINECONE_INDEX_NAME,
        namespace=namespace,
    )

    print(f"[pipeline] ✅ {len(chunks)} chunks stored in Pinecone namespace '{namespace}'")
    print(f"[pipeline] ── chunk_and_embed complete ──\n")

    return {
        "video_id": video_id,
        "chunks_created": len(chunks),
        "namespace": namespace,
        "status": "success",
    }


# -------------------------------------------------------
# HELPER — get_transcript_from_pinecone(video_id)
# -------------------------------------------------------
def get_transcript_from_pinecone(video_id: str) -> dict | None:
    namespace = f"video_{video_id}"
    print(f"[get_transcript_from_pinecone] Looking up namespace: {namespace}")

    try:
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=OPENAI_API_KEY
        )
        vector_store = PineconeVectorStore(
            index_name=PINECONE_INDEX_NAME,
            embedding=embeddings,
            namespace=namespace,
        )
        results = vector_store.similarity_search("lyrics transcript song", k=100)

        if not results:
            return None

        full_text = " ".join([doc.page_content for doc in results])
        return {
            "transcript_text": full_text,
            "word_count": len(full_text.split())
        }

    except Exception as e:
        print(f"[get_transcript_from_pinecone] Not found: {e}")
        return None


def get_transcript_from_chroma(video_id: str) -> dict | None:
    return get_transcript_from_pinecone(video_id)