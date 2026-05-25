# backend/tools/analyze_marketing.py
import os
import json
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.messages import SystemMessage, HumanMessage
from config import OPENAI_API_KEY, XAI_API_KEY, GROK_MODEL, GROK_REASONING_EFFORT, GROK_TEMPERATURE

PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "music-ai-chat")

if not OPENAI_API_KEY:
    raise EnvironmentError(
        "[analyze_marketing] OPENAI_API_KEY is not set. "
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


# ---------------------------------------------------------------------------
# Internal helper — searches Pinecone marketing knowledge namespace
# ---------------------------------------------------------------------------
def _search_knowledge(query: str) -> str:
    try:
        vector_store = PineconeVectorStore(
            index_name=PINECONE_INDEX_NAME,
            embedding=embeddings,
            namespace="marketing_knowledge",
        )
        results = vector_store.similarity_search(query, k=3)
        if not results:
            return ""
        chunks = []
        for doc in results:
            header = doc.metadata.get("section") or ""
            chunks.append(f"[{header}]\n{doc.page_content}")
        return "\n\n---\n\n".join(chunks)
    except Exception as e:
        print(f"   ⚠️ _search_knowledge failed: {e}")
        return ""


# ---------------------------------------------------------------------------
# Internal helper — formats librosa dict into a readable LLM prompt block
# ---------------------------------------------------------------------------
def _format_audio_features(audio_features: dict) -> str:
    """
    Converts the librosa dict into a readable block for the LLM prompt.

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


# ---------------------------------------------------------------------------
# Tool — analyze_marketing_potential (single definition)
# ---------------------------------------------------------------------------
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
        video_id:        The YouTube video ID (e.g. 'H5v3kku4y6Q').
        transcript_text: Transcript content retrieved by search_transcript.
        audio_features:  Optional JSON string with BPM, energy, key, mode from librosa.
        spotify_genres:  Optional comma-separated Spotify genre tags.
    """
    print(f"\n📊 [analyze_marketing_potential] Analyzing video: {video_id}")

    if not transcript_text or len(transcript_text.strip()) < 30:
        return (
            "⚠️ transcript_text is empty or too short to analyze. "
            "Please call search_transcript first with a query like "
            "'mood energy genre chorus feeling' and pass the result here."
        )

    print(f"   📝 Transcript sample received ({len(transcript_text)} chars)")

    # Parse audio_features JSON string
    parsed_audio = {}
    if audio_features:
        try:
            parsed_audio = json.loads(audio_features)
            print(f"   🎵 Audio features: BPM={parsed_audio.get('bpm')} | "
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

    # Search marketing knowledge base
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
- FIRST: detect the language of the lyrics. This is your most important signal.
- Map language to regional genre context BEFORE looking at audio features:
    - Lithuanian / Latvian / Estonian → Baltic/Eastern European pop
    - Spanish → Latin pop / reggaeton / Latin trap
    - French → French rap / chanson / afro-French
    - Portuguese (BR) → pagode / funk carioca / sertanejo / Brazilian pop
    - Arabic → khaleeji / shaabi / Arabic pop
    - Korean → K-pop / K-hip-hop
    - Non-English in general → regional pop of that language's origin country
- SECOND: use lyrical themes and mood to narrow the subgenre (e.g. children's themes → children's pop)
- THIRD: use BPM + energy to confirm energy level only — never use them to override language-based genre
- If Spotify genres are present: use them to confirm or narrow further
- Always name both a GENRE and a SUBGENRE (e.g. "Baltic Pop / Children's Pop", "Latin Pop / Reggaeton")

"""

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
