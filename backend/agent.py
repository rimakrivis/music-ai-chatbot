# backend/agent.py
# The LangChain agent — the AI brain of the music chatbot.
# Wires all 6 tools into create_agent (LangChain 1.0).
# Uses InMemorySaver for per-session conversation memory.
# Injects video_id into the system prompt at runtime so tools
# know which Pinecone namespace to query.
# Tracks tools_used[] so the frontend can show tool badges.

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from tools.search_transcript import search_transcript
from tools.extract_lyrics import extract_lyrics
from tools.analyze_marketing import analyze_marketing_potential
from tools.get_artist_info import get_artist_info
from tools.find_release_timing import find_release_timing
from tools.search_marketing_knowledge import search_marketing_knowledge
from config import OPENAI_API_KEY

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.3,
    api_key=OPENAI_API_KEY
)

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
TOOLS = [
    search_transcript,
    extract_lyrics,
    analyze_marketing_potential,
    get_artist_info,
    find_release_timing,
    search_marketing_knowledge,
]

# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------
checkpointer = InMemorySaver()

# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------
def _build_system_prompt(video_id: str, video_title: str = "", video_channel: str = "") -> str:
    video_context = f"video ID: {video_id}"
    if video_title:
        video_context += f' | title: "{video_title}"'
    if video_channel:
        video_context += f' | artist: "{video_channel}"'
    video_context += f' | youtube: "https://www.youtube.com/watch?v={video_id}"'

    return f"""You are DropOperator AI — a professional music release manager and marketing strategist.

CURRENT VIDEO:
{video_context}
Always pass video_id={video_id} to any tool that requires it.

TEMPLATE VARIABLES — use these exactly when filling in any template:
- Song Title: "{video_title}"
- Artist Name: "{video_channel}"
- YouTube Link: "https://www.youtube.com/watch?v={video_id}"
- Spotify Link: ask the user "Do you have a Spotify pre-save or release link?" BEFORE generating any template that includes it. Never leave [Spotify Link] blank or invented.
Never leave [Song Title], [Artist Name], or [YouTube Link] as placeholders — you already have this data.

SCOPE: Only answer music-related questions. Politely decline anything else.

TOOLS:
- search_transcript → search song content, themes, mood, lyrics
- extract_lyrics → full cleaned lyrics
- analyze_marketing_potential → requires transcript_text from search_transcript
- get_artist_info → Spotify stats, popularity, top tracks, genres
- find_release_timing → release date strategy, teaser schedule
- search_marketing_knowledge → YOUR PRIMARY KNOWLEDGE SOURCE. Call this first for any marketing, release, social media, playlist, radio, press, budget, or deadline question. Never answer these from general knowledge — always check this tool first.

KNOWLEDGE BASE FIRST — CRITICAL RULE:
For ANY marketing, release, social media, playlist, radio, press, budget, or deadline question:
ALWAYS call search_marketing_knowledge FIRST.
If it returns relevant content → use it as primary source.
If nothing relevant → then use general knowledge.
Never skip this. Never answer marketing questions from memory alone.

MANDATORY TOOL CALL ORDER:

1. MARKETING PLAN / STRATEGY:
   STEP 1 → search_marketing_knowledge(query=<user question summarized>)
   STEP 2 → search_transcript(video_id="{video_id}", query="mood energy genre chorus hook feeling")
   STEP 3 → analyze_marketing_potential(video_id="{video_id}", transcript_text=<step 2 result>)
   STEP 4 → find_release_timing(genre=<from step 2>, audience_size=<known or ask>)

2. RELEASE STRATEGY / TIMELINE / DEADLINES:
   STEP 1 → search_marketing_knowledge(query=<user question>)
   STEP 2 → find_release_timing(genre=<known>, audience_size=<known or ask>)

3. HOW-TO QUESTIONS (pitching, radio, press release, social plan, playlist, budget):
   STEP 1 → search_marketing_knowledge(query=<user question>)

4. SONG ANALYSIS:
   STEP 1 → search_transcript(video_id="{video_id}", query="mood energy genre chorus hook feeling")
   STEP 2 → analyze_marketing_potential(video_id="{video_id}", transcript_text=<step 1 result>)

5. LYRICS REQUEST:
   STEP 1 → extract_lyrics(video_id="{video_id}")

   If search_marketing_knowledge returns weak, generic, or unrelated information:
- acknowledge the limitation internally
- use general marketing expertise instead
- only incorporate the useful parts of the knowledge base
"""

# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------
def create_music_agent():
    print("\n🤖 [agent] Creating music agent...")

    agent = create_agent(
        model="openai:gpt-4o",
        tools=TOOLS,
        checkpointer=checkpointer,
    )

    print("   ✅ Music agent created with 6 tools and InMemorySaver memory")
    return agent


# ---------------------------------------------------------------------------
# Agent runner
# ---------------------------------------------------------------------------
async def run_agent(
    agent,
    message: str,
    session_id: str,
    video_id: str,
    video_title: str = "",
    video_channel: str = ""
) -> dict:
    print(f"\n💬 [run_agent] Session: {session_id} | Video: {video_id}")
    print(f"   Message: '{message}'")

    system_prompt = _build_system_prompt(video_id, video_title, video_channel)

    config = {
        "configurable": {
            "thread_id": session_id
        }
    }

    agent_input = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
    }

    try:
        result = await agent.ainvoke(agent_input, config=config)

        all_messages = result.get("messages", [])

        # Extract the last non-empty AI response
        response_text = ""
        for msg in reversed(all_messages):
            if isinstance(msg, AIMessage) and msg.content:
                if isinstance(msg.content, str) and msg.content.strip():
                    response_text = msg.content.strip()
                    break

        if not response_text:
            response_text = "I processed your request but could not generate a response. Please try again."

        # Collect tool names from ToolMessages
        tools_used = []
        for msg in all_messages:
            if isinstance(msg, ToolMessage):
                tool_name = msg.name if hasattr(msg, "name") else "unknown_tool"
                if tool_name not in tools_used:
                    tools_used.append(tool_name)

        print(f"   ✅ Response generated ({len(response_text)} chars)")
        print(f"   🔧 Tools used: {tools_used if tools_used else 'none'}")

        return {
            "response": response_text,
            "tools_used": tools_used,
            "session_id": session_id
        }

    except Exception as e:
        error_msg = f"Agent error: {str(e)}"
        print(f"   ❌ {error_msg}")
        return {
            "response": "Sorry, I encountered an error processing your request. Please try again.",
            "tools_used": [],
            "session_id": session_id,
            "error": error_msg
        } 

