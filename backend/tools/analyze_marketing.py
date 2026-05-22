import os
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.messages import SystemMessage, HumanMessage
from config import OPENAI_API_KEY, XAI_API_KEY, GROK_MODEL, GROK_REASONING_EFFORT, GROK_TEMPERATURE

PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "music-ai-chat")

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=OPENAI_API_KEY
)

llm = ChatOpenAI(
    model=GROK_MODEL,
    temperature=GROK_TEMPERATURE,
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1",
    reasoning_effort=GROK_REASONING_EFFORT,
)
print(f"[analyze_marketing] LLM: {GROK_MODEL} | reasoning: {GROK_REASONING_EFFORT}")


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


@tool
def analyze_marketing_potential(video_id: str, transcript_text: str) -> str:
    """
    Analyze the marketing potential of a song based on its transcript content.
    IMPORTANT: You must call search_transcript first to get transcript_text.
    Never call this tool without transcript_text — genre and mood must come
    from actual lyrical content, not from the song title or artist name.
    Use this tool when the user asks about marketing strategy, TikTok or Reels
    potential, target audience, platforms, or commercial appeal.
    Args:
        video_id: The YouTube video ID (e.g. 'H5v3kku4y6Q').
        transcript_text: Transcript content retrieved by search_transcript.
    """
    print(f"\n📊 [analyze_marketing_potential] Analyzing video: {video_id}")

    if not transcript_text or len(transcript_text.strip()) < 30:
        return (
            "⚠️ transcript_text is empty or too short to analyze. "
            "Please call search_transcript first with a query like "
            "'mood energy genre chorus feeling' and pass the result here."
        )

    print(f"   📝 Transcript sample received ({len(transcript_text)} chars) — proceeding with analysis")

    knowledge = _search_knowledge("marketing strategy platform TikTok audience release genre")

    system_prompt = f"""You are DropOperator AI — a professional music marketing strategist.
Use the marketing knowledge below to inform your analysis and recommendations.
Base ALL genre and mood conclusions strictly on the transcript provided.
Never invent or assume genre from the song title or artist name.
Always respond in the same language the user writes in.

MARKETING KNOWLEDGE:
{knowledge if knowledge else "Not available — use general music marketing expertise."}"""

    user_message = f"""Analyze this song transcript and return a marketing brief with exactly these sections:

GENRE & SUBGENRE:
MOOD & ENERGY:
TARGET AUDIENCE:
TIKTOK / REELS POTENTIAL:
STRONGEST HOOK MOMENT:
RECOMMENDED LEAD PLATFORM:
PLATFORM PRIORITY ORDER:
COMMERCIAL APPEAL:

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
