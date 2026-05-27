# backend/agent.py
import json
from datetime import date as _date

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
# Model
# ---------------------------------------------------------------------------
llm = ChatOpenAI(
    model=GROK_MODEL,
    temperature=GROK_TEMPERATURE,
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1",
    reasoning_effort=GROK_REASONING_EFFORT,
)
print(f"[agent] LLM: {GROK_MODEL} | reasoning: {GROK_REASONING_EFFORT} | endpoint: xAI")

TOOLS = [
    search_transcript,
    extract_lyrics,
    analyze_marketing_potential,
    get_artist_info,
    find_release_timing,
    search_marketing_knowledge,
]

checkpointer = InMemorySaver()

def _trim_messages(messages: list, keep_last_n_human_turns: int = 6) -> list:
    if not messages:
        return messages
    system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
    non_system = [m for m in messages if not isinstance(m, SystemMessage)]
    human_indices = [i for i, m in enumerate(non_system) if isinstance(m, HumanMessage)]
    if len(human_indices) <= keep_last_n_human_turns:
        return messages
    cutoff = human_indices[-keep_last_n_human_turns]
    trimmed = non_system[cutoff:]
    print(f"   ✂️  Trimmed history: {len(non_system)} → {len(trimmed)} messages")
    return system_msgs + trimmed


# ---------------------------------------------------------------------------
# System prompt builder — now accepts genre_data dict instead of audio_features
# ---------------------------------------------------------------------------
def _build_system_prompt(
    video_id: str,
    video_title: str = "",
    video_channel: str = "",
    genre_data: dict = None,       # ← replaces audio_features_text / audio_features_json
) -> str:
    video_context = f"video ID: {video_id}"
    if video_title:
        video_context += f' | title: "{video_title}"'
    if video_channel:
        video_context += f' | artist: "{video_channel}"'
    video_context += f' | youtube: "https://www.youtube.com/watch?v={video_id}"'

    today = _date.today().isoformat()

    # ── Build genre block from Essentia output ──
    if genre_data and genre_data.get("top_genres"):
        top_genres = genre_data["top_genres"]

        # Primary genre line: "Electronic › House (87.3%)"
        primary = top_genres[0]
        primary_line = f"{primary['genre']}"
        if primary["subgenre"]:
            primary_line += f" › {primary['subgenre']}"
        primary_line += f" ({round(primary['confidence'] * 100, 1)}%)"

        # Secondary genres as a compact comma-separated list
        secondary_parts = []
        for g in top_genres[1:]:
            label = g["genre"]
            if g["subgenre"]:
                label += f" › {g['subgenre']}"
            label += f" ({round(g['confidence'] * 100, 1)}%)"
            secondary_parts.append(label)

        secondary_line = ", ".join(secondary_parts) if secondary_parts else "—"

        genre_block = (
            f"Primary genre:    {primary_line}\n"
            f"Also detected:    {secondary_line}\n"
            f"Source:           Essentia Discogs-EffNet (400-class model)\n"
            f"RAW JSON: {json.dumps({'top_genres': top_genres})}"
        )
    else:
        genre_block = "No genre data available for this track."

    return f"""You are DropOperator — a music release planner.

CURRENT TRACK:
{video_context}
Always pass video_id={video_id} to any tool that requires it.

GENRE & SOUND PROFILE (pre-detected by Essentia — do not re-analyze):
{genre_block}

TODAY: {today}
DATE RULES: PRE-RELEASE tasks before release date | Spotify pitch min 7 days before (28 days recommended) — NEVER after release | Distributor upload type = deadline (min 4 days before) | POST-RELEASE tasks intentionally after release date | Release date appears once in checklist header only | If user says already submitted to distributor → skip "Upload to Distributor" and "Master Audio File Ready".

PLAN MODE — triggered when user asks for a plan, strategy, or rollout:
1. If no release date given → ask for it.
   If the date is too tight → do not proceed. Tell the user exactly what is at risk:
   - Distributor upload needs minimum 3-4 days to go live
   - Spotify editorial pitch must be submitted minimum 7 days before release (28 days recommended)
   - If either deadline is missed, warn clearly and suggest the nearest realistic date.
   Never generate a plan with past dates or impossible deadlines. Offer a corrected date instead.
2. Call search_marketing_knowledge to get correct timeline requirements.
3. Use the track title "{video_title}" and artist "{video_channel}" in the plan header.
4. Output the checklist below. No prose before or after. Just the checklist.

CHECKLIST FORMAT (exact structure, always):

RELEASE PLAN: {video_title} — Release: [YYYY-MM-DD]

PRE-RELEASE
[ ] Cover Art & Visual Assets — [YYYY-MM-DD] — deadline
[ ] Master Audio File Ready — [YYYY-MM-DD] — deadline
[ ] Upload to Distributor — [YYYY-MM-DD] — deadline
[ ] Submit Spotify Editorial Pitch — [YYYY-MM-DD] — spotify
[ ] Register ISRC with AGATA & LATGA — [YYYY-MM-DD] — deadline
[ ] YouTube Video Upload (unlisted, scheduled) — [YYYY-MM-DD] — youtube
[ ] Write PR Release — [YYYY-MM-DD] — deadline
[ ] Prepare Radio Submission Emails — [YYYY-MM-DD] — deadline
[ ] Social Media Profile Audit — [YYYY-MM-DD] — social_media
[ ] Social Media Teaser Campaign Start — [YYYY-MM-DD] — social_media

RELEASE DAY — [YYYY-MM-DD]
[ ] Confirm song live on all platforms — [YYYY-MM-DD] — release
[ ] YouTube video goes public — [YYYY-MM-DD] — youtube
[ ] Send Radio Submission emails (07:00 AM) — [YYYY-MM-DD] — deadline
[ ] Send PR Release to press — [YYYY-MM-DD] — deadline
[ ] Release post on all social media (before 09:00 AM) — [YYYY-MM-DD] — social_media

POST-RELEASE
[ ] Engage fan comments & shares Days 1-5 — [YYYY-MM-DD] — social_media
[ ] Check Spotify save rate & streams Day 7 — [YYYY-MM-DD] — spotify
[ ] Second social push — lyrics reel, behind the scenes — [YYYY-MM-DD] — social_media
[ ] Playlist pitching follow-up — [YYYY-MM-DD] — spotify
[ ] Radio follow-up emails — [YYYY-MM-DD] — deadline
[ ] Full platform analytics review Day 14 — [YYYY-MM-DD] — deadline

Dates must be calculated backwards from the release date using knowledge retrieved from search_marketing_knowledge.

FOLLOW-UP MODE — triggered by any message after the plan is shown:
- Answer the question directly. No plan regeneration.
- If it is a how-to question → call search_marketing_knowledge first, then answer.
- If it is a song analysis question → call search_transcript first, then analyze_marketing_potential.
- Never add fluff. Never repeat the plan.

DELETE MODE — triggered when user asks to remove, delete, or cancel a task:
- First confirm: "Are you sure you want to delete [task name]?"
- Only after user confirms with yes/confirm/delete it → respond with this exact JSON block and nothing else:
  {{"action": "delete", "task": "[exact task title]"}}
- Never delete without explicit user confirmation.

RESCHEDULE MODE — triggered when user asks to move or reschedule a task:
- Ask what the new date should be if not given.
- Confirm the change: "Move [task] to [new date]?"
- After confirmation tell the user to use the reschedule button on the task card for the new date.

CRITICAL DATE RULES:
- POST-RELEASE tasks intentionally fall AFTER the release date — this is correct
- PRE-RELEASE tasks must ALL be before the release date
- "Upload to Distributor" must be minimum 3-4 days BEFORE release
- "Submit Spotify Editorial Pitch" must be minimum 7 days BEFORE release (28 days recommended) — NEVER after release
- Release date appears ONCE in the checklist header and ONCE under RELEASE DAY section only
- If user says song is already submitted to distributor → skip "Upload to Distributor" and "Master Audio File Ready" tasks

TOOLS:
- search_marketing_knowledge → MUST be called first for every plan and every how-to question. Never answer from memory. If the tool returns nothing, only then use general knowledge and flag it as: "I couldn't find this in the knowledge base, but generally..."
- search_transcript → song themes, mood, lyrics content
- analyze_marketing_potential → needs search_transcript result first. Also pass genre_data as a JSON string — take the RAW JSON from the GENRE & SOUND PROFILE block above and pass it directly as the genre_data parameter.
- find_release_timing → use for release date strategy if user is unsure
- get_artist_info → Spotify stats if artist name known
- extract_lyrics → only if user explicitly asks for lyrics

Always respond in the same language the user writes in.
"""


# ---------------------------------------------------------------------------
# Agent factory — unchanged
# ---------------------------------------------------------------------------

STATIC_SYSTEM_PROMPT = """You are DropOperator — a music release planner.
Use search_marketing_knowledge before every plan and every how-to question.
Always respond in the same language the user writes in."""

def create_music_agent():
    print("\n🤖 [agent] Creating music agent...")
    agent = create_react_agent(
        model=llm,
        tools=TOOLS,
        checkpointer=checkpointer,
        prompt=STATIC_SYSTEM_PROMPT,
    )
    print("   ✅ Music agent created with 6 tools and InMemorySaver memory")
    return agent


# ---------------------------------------------------------------------------
# Agent runner — audio_features param renamed to genre_data
# ---------------------------------------------------------------------------
async def run_agent(
    agent,
    message: str,
    session_id: str,
    video_id: str,
    video_title: str = "",
    video_channel: str = "",
    genre_data: dict = None,       # ← renamed from audio_features
) -> dict:
    print(f"\n💬 [run_agent] Session: {session_id} | Video: {video_id}")
    print(f"   Message: '{message}'")

    if genre_data and genre_data.get("top_genres"):
        top = genre_data["top_genres"][0]
        print(
            f"   🎵 Genre data loaded: {top.get('genre')} › {top.get('subgenre')} "
            f"({round(top.get('confidence', 0) * 100, 1)}%)"
        )
    else:
        print("   ℹ️ No genre data available for this track")

    context_block = _build_system_prompt(
        video_id,
        video_title,
        video_channel,
        genre_data,
    )

    config = {"configurable": {"thread_id": session_id}}

    existing = checkpointer.get(config)
    is_first_turn = (
        existing is None
        or not existing.get("channel_values", {}).get("messages")
    )

    if is_first_turn or (genre_data and genre_data.get("top_genres")):
        agent_input = {
            "messages": [
                {"role": "system", "content": context_block},
                {"role": "system", "content": f"TODAY'S DATE: {_date.today().isoformat()}. All planned dates must be on or after today."},
                {"role": "user", "content": message},
            ]
        }
        if is_first_turn:
            print("   📌 First turn — injecting system context")
        else:
            print("   🔄 Genre data available — re-injecting system context")
    else:
        agent_input = {
            "messages": [
                {"role": "user", "content": message},
            ]
        }
        print("   ♻️ Returning turn — skipping context re-injection")

    try:
        existing_state = checkpointer.get(config)
        if existing_state:
            existing_msgs = existing_state.get("channel_values", {}).get("messages", [])
            if existing_msgs:
                trimmed = _trim_messages(existing_msgs)
                if len(trimmed) < len(existing_msgs):
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