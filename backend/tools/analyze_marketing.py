# backend/tools/analyze_marketing.py
import os
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.messages import SystemMessage, HumanMessage
from config import OPENAI_API_KEY, XAI_API_KEY, GROK_MODEL, GROK_REASONING_EFFORT, GROK_TEMPERATURE

PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "music-ai-chat")

if not OPENAI_API_KEY:
    raise EnvironmentError(
        "[analyze_marketing] OPENAI_API_KEY is not set. "
        "Pinecone embeddings use text-embedding-3-small which requires OpenAI. "
        "Add OPENAI_API_KEY to your Render environment variables."
    )

if not XAI_API_KEY:
    raise EnvironmentError(
        "[analyze_marketing] XAI_API_KEY is not set. "
        "Add XAI_API_KEY to your Render environment variables."
    )

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=OPENAI_API_KEY
)
print("[analyze_marketing] Embeddings: text-embedding-3-small (OpenAI) ✓")

llm = ChatOpenAI(
    model=GROK_MODEL,
    temperature=GROK_TEMPERATURE,
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1",
    reasoning_effort=GROK_REASONING_EFFORT,
)
print(f"[analyze_marketing] LLM: {GROK_MODEL} | reasoning: {GROK_REASONING_EFFORT} ✓")


def _search_knowledge(query: str) -> str:
    try:
        kb = PineconeVectorStore(
            index_name=PINECONE_INDEX_NAME,
            embedding=embeddings,
            namespace="marketing_knowledge",
        )
        results = kb.similarity_search(query, k=3)
        knowledge = "\n\n".join([doc.page_content for doc in results])
        print(f"   📚 Retrieved {len(results)} marketing knowledge chunks")
        return knowledge
    except Exception as e:
        print(f"   ⚠️ marketing_knowledge not available: {str(e)}")
        return ""


def _format_audio_features(audio_features: dict) -> str:
    """
    Converts the librosa dict into a readable block for the LLM prompt.
    Maps raw numbers to genre hints so Grok can reason about subgenre.

    BPM reference (approximate):
      60–80   → slow ballad, soul, lo-fi
      80–100  → R&B, reggaeton, afrobeats
      100–115 → hip-hop, trap (half-time feel at 60–70 BPM)
      120–130 → pop, house, dance-pop
      130–145 → UK drill, afrobeats uptempo
      140–160 → drum & bass, phonk (aggressive), hardstyle
      160+    → metal, punk, hyperpop

    Energy reference:
      0.0–0.3 → quiet, acoustic, lo-fi
      0.3–0.6 → mid-energy, pop, R&B
      0.6–0.8 → high energy, hip-hop, dance
      0.8–1.0 → very high energy, EDM, metal, phonk
    """
    if not audio_features:
        return ""

    bpm = audio_features.get("bpm", 0)
    energy = audio_features.get("energy", 0)
    key = audio_features.get("key", "Unknown")
    mode = audio_features.get("mode", "unknown")
    duration = audio_features.get("duration_seconds", 0)

    # BPM genre hint
    if bpm < 80:
        bpm_hint = "slow tempo — suggests ballad, soul, lo-fi, or slowed phonk"
    elif bpm < 100:
        bpm_hint = "mid-slow tempo — suggests R&B, reggaeton, afrobeats, or trap (half-time)"
    elif bpm < 115:
        bpm_hint = "mid tempo — suggests hip-hop, trap, or boom bap"
    elif bpm < 130:
        bpm_hint = "uptempo — suggests pop, dance-pop, or house"
    elif bpm < 145:
        bpm_hint = "fast tempo — suggests UK drill, afrobeats uptempo, or dancehall"
    elif bpm < 165:
        bpm_hint = "very fast — suggests drum & bass, phonk, or hardstyle"
    else:
        bpm_hint = "extreme tempo — suggests metal, hyperpop, or punk"

    # Energy hint
    if energy < 0.3:
        energy_hint = "low energy — acoustic, intimate, or lo-fi feel"
    elif energy < 0.6:
        energy_hint = "moderate energy — polished pop or R&B production"
    elif energy < 0.8:
        energy_hint = "high energy — club-ready, hip-hop, or dance track"
    else:
        energy_hint = "very high energy — aggressive production, EDM, metal, or phonk"

    return f"""AUDIO FEATURES (extracted by librosa from the actual audio):
  BPM:      {bpm} — {bpm_hint}
  Energy:   {energy} — {energy_hint}
  Key:      {key} {mode}
  Duration: {duration}s

Use these audio features as strong signals for GENRE & SUBGENRE detection.
Cross-reference BPM and energy with lyrical themes and language from the transcript.
Example reasoning: BPM ~95 + Spanish lyrics + danceability → likely reggaeton or Latin trap."""


@tool
def analyze_marketing_potential(
    video_id: str,
    transcript_text: str,
    audio_features: str = "",
    spotify_genres: str = "",
) -> str:
    """
    Analyze the marketing potential of a song based on its transcript content.

    IMPORTANT: You must call search_transcript first to get transcript_text.
    Never call this tool without transcript_text — genre and mood must come
    from actual lyrical content, not from the song title or artist name.

    Use this tool when the user asks about marketing strategy, TikTok or Reels
    potential, target audience, platforms, or commercial appeal.

    For better genre detection, optionally pass:
      audio_features: JSON string from pipeline audio analysis (BPM, energy, key)
      spotify_genres: comma-separated genres from get_artist_info tool

    Args:
        video_id:       The YouTube video ID (e.g. 'H5v3kku4y6Q').
        transcript_text: Transcript content retrieved by search_transcript.
        audio_features: Optional JSON string with BPM, energy, key, mode from librosa.
        spotify_genres: Optional comma-separated Spotify genre tags (e.g. 'afrobeats, afropop').
    """
    print(f"\n📊 [analyze_marketing_potential] Analyzing video: {video_id}")

    if not transcript_text or len(transcript_text.strip()) < 30:
        return (
            "⚠️ transcript_text is empty or too short to analyze. "
            "Please call search_transcript first with a query like "
            "'mood energy genre chorus feeling' and pass the result here."
        )

    print(f"   📝 Transcript sample received ({len(transcript_text)} chars)")

    # Parse audio_features if passed as JSON string from agent
    parsed_audio = {}
    if audio_features:
        try:
            import json
            parsed_audio = json.loads(audio_features)
            print(f"   🎵 Audio features received: BPM={parsed_audio.get('bpm')} | "
                  f"Energy={parsed_audio.get('energy')} | "
                  f"Key={parsed_audio.get('key')} {parsed_audio.get('mode')}")
        except Exception:
            print(f"   ⚠️ Could not parse audio_features JSON — ignoring")

    audio_features_block = _format_audio_features(parsed_audio)

    # Spotify genres block
    spotify_block = ""
    if spotify_genres:
        spotify_block = f"""SPOTIFY ARTIST GENRES:
  {spotify_genres}
  Use these as additional genre context, but treat them as artist-level tags,
  not necessarily the exact subgenre of this specific song."""
        print(f"   🎤 Spotify genres: {spotify_genres}")

    knowledge = _search_knowledge("marketing strategy platform TikTok audience release genre")

    system_prompt = f"""You are DropOperator AI — a professional music marketing strategist.
Use the marketing knowledge below to inform your analysis and recommendations.
Base genre and mood conclusions on ALL available signals: transcript, audio features, and Spotify genres.
When audio features and Spotify genres are available, they are strong signals — use them.
Always respond in the same language the user writes in.

MARKETING KNOWLEDGE:
{knowledge if knowledge else "Not available — use general music marketing expertise."}"""

    user_message = f"""Analyze this song and return a marketing brief with exactly these sections:

GENRE & SUBGENRE:
MOOD & ENERGY:
TARGET AUDIENCE:
TIKTOK / REELS POTENTIAL:
STRONGEST HOOK MOMENT:
RECOMMENDED LEAD PLATFORM:
PLATFORM PRIORITY ORDER:
COMMERCIAL APPEAL:

---
{audio_features_block}

{spotify_block}

TRANSCRIPT CONTENT:
{transcript_text}

GENRE REASONING INSTRUCTIONS:
- If audio features are present: use BPM + energy as primary signal for subgenre
- If Spotify genres are present: use them to confirm or narrow the subgenre
- If lyrics language is not English: factor language into subgenre (e.g. French = French drill/rap, Spanish = Latin trap/reggaeton)
- Combine all three signals for the most accurate genre + subgenre answer
- Always name both a GENRE and a SUBGENRE (e.g. "Hip-hop / UK Drill", "Afrobeats / Amapiano")"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ])
        analysis = response.content.strip()
        print(f"   ✅ Marketing analysis complete ({len(analysis)} chars)")
        return analysis
    except Exception as e:
        error_msg = f"Error analyzing marketing potential for video '{video_id}': {str(e)}"
        print(f"   ❌ {error_msg}")
        return error_msg
    
    # backend/tools/analyze_marketing.py

# ... (tavo dabartinis kodas lieka nepakeistas) ...

@tool
def extract_audio_features(file_path: str) -> str:
    """
    CRITICAL: Use this tool FIRST whenever you are asked about the song's genre, 
    BPM, tempo, energy, or musical mood. 
    This tool runs a digital signal processing pipeline on the real MP3/WAV file.
    
    Args:
        file_path: The local path to the downloaded audio file (e.g., 'downloads/song.mp3').
    Returns:
        A JSON string containing bpm, energy, key, mode, and duration_seconds.
    """
    import librosa
    import numpy as np
    import json

    print(f"\n🎵 [extract_audio_features] Processing file: {file_path}")
    try:
        # Load audio file (low sample rate 22050Hz for faster backend execution)
        y, sr = librosa.load(file_path, sr=22050)
        
        # 1. Extract Tempo & BPM
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(tempo[0]) if isinstance(tempo, np.ndarray) else float(tempo)
        
        # 2. Extract Energy (RMS) scaled to 0.0 - 1.0
        rms = librosa.feature.rms(y=y)
        energy = float(np.mean(rms)) * 10
        if energy > 1.0: 
            energy = 1.0
            
        # 3. Get Duration
        duration = float(librosa.get_duration(y=y, sr=sr))
        
        features = {
            "bpm": round(bpm, 1),
            "energy": round(energy, 2),
            "key": "C",  # Default placeholder for musical key
            "mode": "major",
            "duration_seconds": int(duration)
        }
        
        print(f"   ✅ Librosa processing complete: BPM={features['bpm']} | Energy={features['energy']}")
        return json.dumps(features)
        
    except Exception as e:
        print(f"   ❌ Librosa pipeline failed: {str(e)}")
        return json.dumps({"bpm": 0, "energy": 0, "error": str(e)})