# backend/agent.py
import json

from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

from tools.search_transcript import search_transcript
from tools.extract_lyrics import extract_lyrics
from tools.analyze_marketing import analyze_marketing_potential
from tools.get_artist_info import get_artist_info
from tools.find_release_timing import find_release_timing
from tools.search_marketing_knowledge import search_marketing_knowledge
from config import OPENAI_API_KEY, XAI_API_KEY, GROK_MODEL, GROK_REASONING_EFFORT, GROK_TEMPERATURE

# ---------------------------------------------------------------------------
# Model — Grok via xAI (OpenAI-compatible endpoint)
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
# Tools — 6 tools, no extract_audio_features (that's a pipeline function, not agent tool)
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

def _trim_messages(messages: list, keep_last_n_human_turns: int = 6) -> list:
    """
    Keep the system message (always first) + last N human/assistant pairs.
    Drop intermediate ToolMessages and tool-call AIMessages older than that window.
    This caps token growth without losing conversational context.
    """
    if not messages:
        return messages

    system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
    non_system = [m for m in messages if not isinstance(m, SystemMessage)]

    # Find human message indices
    human_indices = [i for i, m in enumerate(non_system) if isinstance(m, HumanMessage)]

    if len(human_indices) <= keep_last_n_human_turns:
        return messages  # Within budget, keep everything

    # Only keep messages from the Nth-last human turn onward
    cutoff = human_indices[-keep_last_n_human_turns]
    trimmed = non_system[cutoff:]

    print(f"   ✂️  Trimmed history: {len(non_system)} → {len(trimmed)} messages")
    return system_msgs + trimmed


# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------
def _build_system_prompt(
    video_id: str,
    video_title: str = "",
    video_channel: str = "",
    audio_features_text: str = "",
    audio_features_json: str = "",
) -> str:
    video_context = f"video ID: {video_id}"
    if video_title:
        video_context += f' | title: "{video_title}"'
    if video_channel:
        video_context += f' | artist: "{video_channel}"'
    video_context += f' | youtube: "https://www.youtube.com/watch?v={video_id}"'

    # Build the audio facts block shown to the agent
    if audio_features_text and audio_features_json:
        audio_block = (
            f"{audio_features_text}\n"
            f"RAW JSON for tool call: {audio_features_json}"
        )
        audio_step2_instruction = (
            f'analyze_marketing_potential(video_id="{video_id}", '
            f"transcript_text=<step 1 result>, "
            f"audio_features='{audio_features_json}')"
        )
    else:
        audio_block = "No raw audio data available for this track."
        audio_step2_instruction = (
            f'analyze_marketing_potential(video_id="{video_id}", '
            f'transcript_text=<step 1 result>, audio_features="")'
        )

    return f"""You are DropOperator AI — a professional music release manager and marketing strategist.

CURRENT VIDEO:
{video_context}
Always pass video_id={video_id} to any tool that requires it.

AUDIO ANALYSIS FACTS (Provided by backend system — extracted by librosa from the actual audio file):
{audio_block}

CRITICAL BOUNDARIES & INTENT RECOGNITION:
You must strictly answer ONLY what the user explicitly asks. Do not over-generate.
- If user asks for GENRE or MOOD → Only answer with the musical analysis. DO NOT generate marketing plans or dates.
- If user asks for MARKETING PLAN → Proceed with the full marketing pipeline.

DROPOPERATOR TASK ROUTING:
When discussing specific action items (e.g. after a marketing plan), you MUST suggest which Calendar Event the user should open:
- Cover art/photoshoots → "Cover Art Deadline"
- Press release/Bio → "Prepare PR Release"
- Playlist pitching → "Spotify Pitch"
- Social media content → "Social Media / Promo"
- Distribution → "Release Upload"

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
- search_marketing_knowledge → YOUR PRIMARY KNOWLEDGE SOURCE for how-to questions

MANDATORY TOOL CALL ORDER:

1. SONG ANALYSIS (If user asks ONLY for Genre, Mood, or "Analyze this song"):
   STEP 1 → search_transcript(video_id="{video_id}", query="mood energy genre chorus hook feeling")
   STEP 2 → {audio_step2_instruction}
   (🛑 STOP HERE. DO NOT call find_release_timing. DO NOT generate a release schedule.)

2. FULL MARKETING PLAN / STRATEGY (If user explicitly asks for a plan, dates, or strategy):
   STEP 1 → search_transcript(video_id="{video_id}", query="mood energy genre chorus hook feeling")
   STEP 2 → {audio_step2_instruction}
   STEP 3 → find_release_timing(genre=<genre from step 2>, audience_size=<known or ask>)
   STEP 4 → Suggest DropOperator Calendar Events for the user to execute the plan.

3. HOW-TO / SPECIFIC ADVICE (e.g., radio, PR, social media):
   STEP 1 → search_marketing_knowledge(query=<user question>)
"""


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------

STATIC_SYSTEM_PROMPT = """You are DropOperator AI — a professional music release manager and marketing strategist.

DROPOPERATOR TASK ROUTING:
When discussing specific action items, suggest which Calendar Event the user should open:
- Cover art/photoshoots → "Cover Art Deadline"
- Press release/Bio → "Prepare PR Release"
- Playlist pitching → "Spotify Pitch"
- Social media content → "Social Media / Promo"
- Distribution → "Release Upload"

TOOLS:
- search_transcript → search song content, themes, mood, lyrics
- extract_lyrics → full cleaned lyrics
- analyze_marketing_potential → requires transcript_text from search_transcript
- get_artist_info → Spotify stats, popularity, top tracks, genres
- find_release_timing → release date strategy, teaser schedule
- search_marketing_knowledge → YOUR PRIMARY KNOWLEDGE SOURCE for how-to questions

CRITICAL BOUNDARIES:
- If user asks for GENRE or MOOD only → search_transcript + analyze_marketing_potential. STOP. No dates, no plan.
- If user asks for FULL PLAN → full chain including find_release_timing.
- If user asks HOW-TO → search_marketing_knowledge first.

Always respond in the same language the user writes in.
"""


def create_music_agent():
    print("\n🤖 [agent] Creating music agent...")

    agent = create_react_agent(
        model=llm,
        tools=TOOLS,
        checkpointer=checkpointer,
        prompt=STATIC_SYSTEM_PROMPT,  # type: ignore
    )

    print("   ✅ Music agent created with 6 tools and InMemorySaver memory")
    return agent
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
    audio_features: dict = None,
) -> dict:
    print(f"\n💬 [run_agent] Session: {session_id} | Video: {video_id}")
    print(f"   Message: '{message}'")

    # Build audio features strings for system prompt
    audio_features_text = ""
    audio_features_json = ""

    if audio_features and isinstance(audio_features, dict) and audio_features.get("bpm"):
        audio_features_json = json.dumps(audio_features)
        bpm = audio_features.get("bpm", "?")
        energy = audio_features.get("energy", "?")
        key = audio_features.get("key", "?")
        mode = audio_features.get("mode", "?")
        duration = audio_features.get("duration_seconds", "?")
        audio_features_text = (
            f"BPM: {bpm} | Energy: {energy} | Key: {key} {mode} | Duration: {duration}s"
        )
        print(f"   🎵 Audio features loaded: BPM={bpm}, Energy={energy}, Key={key} {mode}")
    else:
        print("   ℹ️ No audio features available for this track")

    context_block = _build_system_prompt(
        video_id,
        video_title,
        video_channel,
        audio_features_text,
        audio_features_json,
    )

    config = {
        "configurable": {
            "thread_id": session_id
        }
    }

    # Check if this thread already has history — if so, skip re-injecting context
    existing = checkpointer.get(config)
    is_first_turn = (
        existing is None
        or not existing.get("channel_values", {}).get("messages")
    )

    if is_first_turn:
        # First message: inject full context as system + clean user message
        agent_input = {
            "messages": [
                {"role": "system", "content": context_block},
                {"role": "user", "content": message},
            ]
        }
        print("   📌 First turn — injecting system context")
    else:
        # Subsequent turns: bare user message only, context already in history
        agent_input = {
            "messages": [
                {"role": "user", "content": message},
            ]
        }
        print("   ♻️  Returning turn — skipping context re-injection")

    try:
        # Apply history trimming to cap token growth on long sessions
        existing_state = checkpointer.get(config)
        if existing_state:
            existing_msgs = existing_state.get("channel_values", {}).get("messages", [])
            if existing_msgs:
                trimmed = _trim_messages(existing_msgs)
                if len(trimmed) < len(existing_msgs):
                    # Overwrite the stored messages with the trimmed set
                    existing_state["channel_values"]["messages"] = trimmed

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
            "session_id": session_id,
        }

    except Exception as e:
        error_msg = f"Agent error: {str(e)}"
        print(f"   ❌ {error_msg}")
        return {
            "response": "Sorry, I encountered an error processing your request. Please try again.",
            "tools_used": [],
            "session_id": session_id,
            "error": error_msg,
        }