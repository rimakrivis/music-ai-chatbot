# backend/tools/analyze_marketing.py
# Tool 3: analyze_marketing_potential
#
# ARCHITECTURE NOTE:
# This tool intentionally does NOT fetch its own transcript chunks.
# It requires transcript_text to be passed in explicitly.
# This forces the agent to call search_transcript first — which is the
# correct tool call order and ensures genre/mood are based on actual
# lyrical content, not the song title or channel name.
#
# Correct agent chain:
#   search_transcript(video_id, query="mood energy genre chorus") →
#   analyze_marketing_potential(video_id, transcript_text=<result>)
#
# Uses GPT-4o-mini to reason about mood, genre, energy, target audience,
# TikTok/Reels hook potential, and recommended release platforms.
# Also pulls relevant strategy context from the marketing_knowledge ChromaDB collection.

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.messages import SystemMessage, HumanMessage
from config import OPENAI_API_KEY, IS_PRODUCTION
from pipeline import get_chroma_client
from pathlib import Path

CHROMA_PATH = str(Path(__file__).parent.parent / "chroma_db")

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=OPENAI_API_KEY
)

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.4,
    api_key=OPENAI_API_KEY
)


def _search_knowledge(query: str) -> str:
    """
    Retrieves relevant marketing strategy chunks from the seeded
    marketing_knowledge ChromaDB collection.
    Called internally — not exposed as a tool.
    """
    try:
        if IS_PRODUCTION:
            chroma_client = get_chroma_client()
            kb = Chroma(
                collection_name="marketing_knowledge",
                embedding_function=embeddings,
                client=chroma_client,
            )
        else:
            kb = Chroma(
                collection_name="marketing_knowledge",
                embedding_function=embeddings,
                persist_directory=CHROMA_PATH,
            )
        results = kb.similarity_search(query, k=3)
        knowledge = "\n\n".join([doc.page_content for doc in results])
        print(f"   📚 Retrieved {len(results)} marketing knowledge chunks")
        return knowledge
    except Exception as e:
        print(f"   ⚠️ marketing_knowledge collection not available: {str(e)}")
        return ""


@tool
def analyze_marketing_potential(video_id: str, transcript_text: str) -> str:
    """
    Analyze the marketing potential of a song based on its transcript content.

    IMPORTANT: You must call search_transcript first to get transcript_text.
    Never call this tool without transcript_text — genre and mood must come
    from actual lyrical content, not from the song title or artist name.

    Use this tool when the user asks about:
    - Marketing strategy or plan
    - TikTok or Reels potential
    - Target audience
    - Which platforms to release on
    - Commercial appeal
    - General song analysis

    Returns a structured marketing brief covering genre, mood, audience,
    platform recommendations, and hook moments.

    Args:
        video_id: The YouTube video ID (e.g. 'H5v3kku4y6Q').
        transcript_text: Transcript content retrieved by search_transcript.
                         Must not be empty — if empty, call search_transcript first.
    """
    print(f"\n📊 [analyze_marketing_potential] Analyzing video: {video_id}")

    # Guard: refuse to guess if transcript is missing or too short
    if not transcript_text or len(transcript_text.strip()) < 30:
        return (
            "⚠️ transcript_text is empty or too short to analyze. "
            "Please call search_transcript first with a query like "
            "'mood energy genre chorus feeling' and pass the result here. "
            "Genre and mood must be detected from actual lyrics — never guessed from the title."
        )

    print(f"   📝 Transcript sample received ({len(transcript_text)} chars) — proceeding with analysis")

    # Pull relevant marketing strategy knowledge from knowledge base
    knowledge = _search_knowledge("marketing strategy platform TikTok audience release genre")

    # Build the analysis prompt
    system_prompt = f"""You are DropOperator AI — a professional music marketing strategist.

Use the marketing knowledge below to inform your analysis and recommendations.
Base ALL genre and mood conclusions strictly on the transcript provided.
Never invent or assume genre from the song title or artist name.
Always respond in the same language the user writes in.

MARKETING KNOWLEDGE:
{knowledge if knowledge else "Not available — use general music marketing expertise."}"""

    user_message = f"""Analyze this song transcript and return a marketing brief with exactly these sections:

GENRE & SUBGENRE:
(Detect from lyrical themes, vocabulary, rhythm, and references in the transcript.
Do NOT use the song title or artist name to guess genre.)

MOOD & ENERGY:
(Describe the emotional tone and energy level — e.g. melancholic/low, euphoric/high.
Base this on specific lines or phrases from the transcript.)

TARGET AUDIENCE:
(Age range, interests, which platforms they use most.)

TIKTOK / REELS POTENTIAL:
(Rate as High / Medium / Low. Explain why based on the actual hook lines you found.)

STRONGEST HOOK MOMENT:
(Quote the most emotionally powerful or catchy line directly from the transcript.
Explain why it would work as a 15–30 second clip.)

RECOMMENDED LEAD PLATFORM:
(Which single platform should drive the release campaign and why.)

PLATFORM PRIORITY ORDER:
(List platforms in order, e.g. TikTok > Instagram Reels > Spotify > YouTube)

COMMERCIAL APPEAL:
(Rate as High / Medium / Low with a one-sentence reason grounded in the transcript.)

---
TRANSCRIPT CONTENT:
{transcript_text}"""

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
