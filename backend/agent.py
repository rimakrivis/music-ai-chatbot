# backend/agent.py
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from tools.search_transcript import search_transcript
from tools.extract_lyrics import extract_lyrics
from tools.analyze_marketing import analyze_marketing_potential, extract_audio_features
from tools.get_artist_info import get_artist_info
from tools.find_release_timing import find_release_timing
from tools.search_marketing_knowledge import search_marketing_knowledge
from config import OPENAI_API_KEY, XAI_API_KEY, GROK_MODEL, GROK_REASONING_EFFORT, GROK_TEMPERATURE

# ---------------------------------------------------------------------------
# Model — Grok 4.3 via xAI (OpenAI-compatible endpoint)
# reasoning_effort="medium" gives quality press releases and pitches
# without the cost of full reasoning mode
# ---------------------------------------------------------------------------
llm = ChatOpenAI(
    model=GROK_MODEL,
    temperature=GROK_TEMPERATURE,
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1",
    reasoning_effort=GROK_REASONING_EFFORT,
)
print(f"[agent] LLM: {GROK_MODEL} | reasoning: {GROK_REASONING_EFFORT} | endpoint: xAI")

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
# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------
def _build_system_prompt(
    video_id: str, 
    video_title: str = "", 
    video_channel: str = "",
    audio_features_text: str = ""
) -> str:
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

AUDIO ANALYSIS FACTS (Provided by backend system):
{audio_features_text if audio_features_text else "No raw audio data available for this track."}

CRITICAL BOUNDARIES & INTENT RECOGNITION:
You must strictly answer ONLY what the user explicitly asks. Do not over-generate.
- If user asks for GENRE or MOOD -> Only answer with the musical analysis. DO NOT generate marketing plans or dates.
- If user asks for MARKETING PLAN -> Proceed with the full marketing pipeline.

DROPOPERATOR TASK ROUTING:
When discussing specific action items (e.g. after a marketing plan), you MUST suggest which Calendar Event the user should open:
- Cover art/photoshoots -> "Cover Art Deadline"
- Press release/Bio -> "Prepare PR Release"
- Playlist pitching -> "Spotify Pitch"
- Social media content -> "Social Media / Promo"
- Distribution -> "Release Upload"

TEMPLATE VARIABLES — use these exactly when filling in any template:
- Song Title: "{video_title}"
- Artist Name: "{video_channel}"
- YouTube Link: "https://www.youtube.com/watch?v={video_id}"
- Spotify Link: ask the user "Do you have a Spotify pre-save or release link?" BEFORE generating any template.

TOOLS:
- search_transcript → search song content, themes, mood, lyrics
- extract_lyrics → full cleaned lyrics
- analyze_marketing_potential → requires transcript_text from search_transcript
- get_artist_info → Spotify stats, popularity, top tracks, genres
- find_release_timing → release date strategy, teaser schedule
- search_marketing_knowledge → YOUR PRIMARY KNOWLEDGE SOURCE.

MANDATORY TOOL CALL ORDER:

1. SONG ANALYSIS (If user asks ONLY for Genre, Mood, or "Analyze this song"):
   STEP 1 → search_transcript(video_id="{video_id}", query="mood energy genre chorus hook feeling")
   STEP 2 → analyze_marketing_potential(video_id="{video_id}", transcript_text=<step 1 result>, audio_features="Use the AUDIO ANALYSIS FACTS provided above")
   (🛑 STOP HERE. DO NOT call find_release_timing. DO NOT generate a release schedule.)

2. FULL MARKETING PLAN / STRATEGY (If user explicitly asks for a plan, dates, or strategy):
   STEP 1 → search_transcript(video_id="{video_id}", query="mood energy genre chorus hook feeling")
   STEP 2 → analyze_marketing_potential(video_id="{video_id}", transcript_text=<step 1 result>, audio_features="Use the AUDIO ANALYSIS FACTS provided above")
   STEP 3 → find_release_timing(genre=<genre from step 2>, audience_size=<known or ask>)
   STEP 4 → Suggest DropOperator Calendar Events (e.g., "Cover Art Deadline", "Prepare PR Release") for the user to execute the plan.

3. HOW-TO / SPECIFIC ADVICE (e.g., radio, PR, social media):
   STEP 1 → search_marketing_knowledge(query=<user question>)
"""

# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------
def create_music_agent():
    print("\n🤖 [agent] Creating music agent...")

    agent = create_agent(
        model=llm,
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
    video_channel: str = "",
    audio_features_dict: dict = None
) -> dict:
    print(f"\n💬 [run_agent] Session: {session_id} | Video: {video_id}")
    print(f"   Message: '{message}'")

    # Convert audio features to a string for the prompt
    audio_features_text = ""
    if audio_features_dict and audio_features_dict.get('bpm'):
        import json
        audio_features_text = json.dumps(audio_features_dict)

    system_prompt = _build_system_prompt(video_id, video_title, video_channel, audio_features_text)

    config = {
        "configurable": {
            "thread_id": session_id
        }
    }
    
    # ... (TOLIAU EINA TAVO SENAS KODAS: agent_input = { "messages": [...] } ir t.t. Nieko daugiau netrink!)

    agent_input = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
    }

    try:
        result = await agent.ainvoke(agent_input, config=config)

        all_messages = result.get("messages", [])

        response_text = ""
        for msg in reversed(all_messages):
            if isinstance(msg, AIMessage) and msg.content:
                if isinstance(msg.content, str) and msg.content.strip():
                    response_text = msg.content.strip()
                    break

        if not response_text:
            response_text = "I processed your request but could not generate a response. Please try again."

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