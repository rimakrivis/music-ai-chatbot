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

def _format_genre_data(genre_data: dict) -> str:
    if not genre_data or not genre_data.get("top_genres"):
        return ""

    top_genres = genre_data["top_genres"]
    primary = top_genres[0]

    primary_line = primary["genre"]
    if primary.get("subgenre"):
        primary_line += f" › {primary['subgenre']}"
    primary_line += f" ({round(primary.get('confidence', 0) * 100, 1)}%)"

    secondary_parts = []
    for g in top_genres[1:]:
        label = g["genre"]
        if g.get("subgenre"):
            label += f" › {g['subgenre']}"
        label += f" ({round(g.get('confidence', 0) * 100, 1)}%)"
        secondary_parts.append(label)

    secondary_line = ", ".join(secondary_parts) if secondary_parts else "—"

    return f"""GENRE DATA (detected by Essentia Discogs-EffNet 400-class model):
  Primary:  {primary_line}
  Also:     {secondary_line}

Use these as strong genre signals. Cross-reference with lyrical language and themes."""


# ---------------------------------------------------------------------------
# Tool — analyze_marketing_potential (single definition)
# ---------------------------------------------------------------------------
@tool
def analyze_marketing_potential(
    video_id: str,
    transcript_text: str,
    genre_data: str = "",
    spotify_genres: str = "",
     marketing_assets: str = "",
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
        genre_data:      Optional JSON string with Essentia top_genres list.
        spotify_genres:  Optional comma-separated Spotify genre tags.
    """
    print(f"\n📊 [analyze_marketing_potential] Analyzing video: {video_id}")

    if not transcript_text or len(transcript_text.strip()) < 30:
        return (
            "⚠️ transcript_text is empty or too short to analyze. "
            "Please call search_transcript first with a query like "
            "'mood energy genre chorus feeling' and pass the result here."
        )
    
    if not marketing_assets or marketing_assets.strip().lower() in ("", "none", "not provided", "unknown"):
        return (
            "MISSING_INFO: Before I can complete the Spotify pitch, I need one more thing:\n\n"
            "Do you have any marketing assets planned for this release?\n"
            "For example: music video, radio campaign, Meta/TikTok ad budget, PR outreach, playlist pitching.\n\n"
            "If yes — describe briefly. If nothing is planned yet, just say **skip**."
        )
    print(f"   📝 Transcript sample received ({len(transcript_text)} chars)")

 # Parse genre_data JSON string
    parsed_genre = {}
    if genre_data:
        try:
            if isinstance(genre_data, dict):
                parsed_genre = genre_data
            else: 
                parsed_genre = json.loads(genre_data)
            if parsed_genre.get("top_genres"):
                top = parsed_genre["top_genres"][0]
                print(f"   🎵 Genre data: {top.get('genre')} › {top.get('subgenre')} "
                      f"({round(top.get('confidence', 0) * 100, 1)}%)")
        except Exception:
            print("   ⚠️ Could not parse genre_data JSON — ignoring")

    genre_block = _format_genre_data(parsed_genre)   

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
{genre_block}

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
