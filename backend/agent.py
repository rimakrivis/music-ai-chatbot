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
from project_context import fetch_non_release_context, format_details_block, format_band_profile_block
from request_context import current_source_key

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
    print(f"   ✂️ Trimmed history: {len(non_system)} → {len(trimmed)} messages")
    return system_msgs + trimmed


# ---------------------------------------------------------------------------
# STATIC_SYSTEM_PROMPT — base identity, used as the agent factory's default
# prompt. The real per-turn prompt is built by _build_prompt() below and
# injected as the first message of each conversation.
# ---------------------------------------------------------------------------
STATIC_SYSTEM_PROMPT = """You are DropOperator — a marketing planner for musicians and bands.
Use search_marketing_knowledge before every plan and every how-to question.
Always respond in the same language the user writes in."""

# ---------------------------------------------------------------------------
# PROJECT_TYPE_CONFIG — one row per project type. This is the only place
# that needs a new entry when a new project type is added (e.g. merch,
# branding) — no new prompt-building code required. "knowledge_source"
# must match a source_key in seed_knowledge.py's SOURCES list, or be None
# if that type has no dedicated knowledge file seeded yet (falls back to
# searching everything, unfiltered).
# ---------------------------------------------------------------------------
PROJECT_TYPE_CONFIG = {
    "single_release":  {"knowledge_source": "marketing_dist", "anchor_date_label": "release date"},
    "album_release":   {"knowledge_source": "marketing_dist", "anchor_date_label": "release date"},
    "concert":         {"knowledge_source": "concert",        "anchor_date_label": "concert date"},
    "social_campaign": {"knowledge_source": "social_campaign", "anchor_date_label": "campaign launch date"},
    "other":           {"knowledge_source": None,              "anchor_date_label": "the date this project revolves around"},
}

# Project types where a song has actually been loaded (YouTube URL / audio
# upload) — controls whether the CURRENT TRACK / genre block is included.
# Not used for prompt structure or knowledge filtering anymore — those come
# from PROJECT_TYPE_CONFIG above.
RELEASE_PROJECT_TYPES = {"single_release", "album_release"}

# Social-campaign creative treatment per brand_voice tag (mirrors
# frontend/components/dashboard/BandProfileForm.tsx's BRAND_VOICE_OPTIONS
# labels exactly — must match 1:1 for the lookup in _build_prompt to work).
# Injected directly into the prompt for social_campaign projects rather than
# stored as searchable knowledge: there are only 12, always the same
# regardless of which campaign was picked, so putting them in Pinecone would
# mean hoping a search surfaces the right one — putting them here means the
# agent always has them, at zero retrieval risk, the same way the band
# profile itself is always included.
SOCIAL_CAMPAIGN_STYLE_GUIDE = {
    "Dark": "Low light, cinematic framing, restrained text, serious hooks; fewer but stronger posts; prioritize Reel/TikTok and atmospheric Stories.",
    "Playful": "Bright energy, humor, quick cuts, polls, memes and playful captions; prioritize short video and interactive Stories.",
    "Raw": "Phone-camera feel, imperfections, direct talking, rehearsal mistakes and unfiltered captions; avoid over-editing.",
    "Underground": "Low-key visuals, grain/texture, insider language, minimal CTAs; favor intimate Reels, BTS and selective Stories.",
    "Glamorous": "Fashion-forward visuals, polished locations, strong photography, dramatic transitions; prioritize Reels and carousels.",
    "Polished": "Clear branding, consistent typography, clean editing, strong hooks and professional performance/BTS footage.",
    "Mysterious": "Reveal information gradually, use clues, cropped visuals, unanswered questions and pauses; Stories are useful for breadcrumbs.",
    "Bold": "Large hooks, high energy, confident language, strong performance and direct CTAs; frequent short-form video.",
    "Chill": "Casual phone footage, relaxed pacing, everyday moments, conversational captions; Stories and vlogs work well.",
    "Fierce": "Strong performance, assertive hooks, powerful close-ups, decisive language and high-impact editing.",
    "Dreamy": "Soft visuals, emotional voiceovers, atmospheric performance, poetic text and slower pacing.",
    "Relatable": "Everyday situations, humor, honest struggles, ordinary locations and conversational language; make the artist feel accessible.",
}


def resolve_source_key(project_type: str | None) -> str | None:
    """Which knowledge-base source_key this project type's searches should
    be scoped to, or None to search everything (unfiled/unknown types)."""
    if not project_type:
        return None
    return PROJECT_TYPE_CONFIG.get(project_type, {}).get("knowledge_source")


# ---------------------------------------------------------------------------
# _build_prompt — the ONE system prompt builder for every project type.
#
# Structural + behavioral only, on purpose (standing rule — Rima writes
# actual strategy/timeline content in the marketing_knowledge*.md files,
# not here). What varies per project type is small and data-driven
# (PROJECT_TYPE_CONFIG above), not a separate hardcoded prompt per type.
# ---------------------------------------------------------------------------
def _build_prompt(
    project_type: str,
    project_details: dict = None,
    band_profile: dict = None,
    video_id: str = None,
    video_title: str = "",
    video_channel: str = "",
    genre_data: dict = None,
) -> str:
    config = PROJECT_TYPE_CONFIG.get(project_type, PROJECT_TYPE_CONFIG["other"])
    anchor_label = config["anchor_date_label"]
    today = _date.today().isoformat()

    details_block = format_details_block(project_details)
    band_block = format_band_profile_block(band_profile)

    track_block = ""
    if project_type in RELEASE_PROJECT_TYPES and video_id:
        video_context = f"video ID: {video_id}"
        if video_title:
            video_context += f' | title: "{video_title}"'
        if video_channel:
            video_context += f' | artist: "{video_channel}"'
        video_context += f' | youtube: "https://www.youtube.com/watch?v={video_id}"'

        if genre_data and genre_data.get("top_genres"):
            top_genres = genre_data["top_genres"]
            primary = top_genres[0]
            primary_line = f"{primary['genre']}"
            if primary["subgenre"]:
                primary_line += f" › {primary['subgenre']}"
            primary_line += f" ({round(primary['confidence'] * 100, 1)}%)"

            secondary_parts = []
            for g in top_genres[1:]:
                label = g["genre"]
                if g["subgenre"]:
                    label += f" › {g['subgenre']}"
                label += f" ({round(g['confidence'] * 100, 1)}%)"
                secondary_parts.append(label)
            secondary_line = ", ".join(secondary_parts) if secondary_parts else "—"

            genre_block = (
                f"Primary genre: {primary_line}\n"
                f"Also detected: {secondary_line}\n"
                f"Source: Essentia Discogs-EffNet (400-class model)\n"
                f"RAW JSON: {json.dumps({'top_genres': top_genres})}"
            )
        else:
            genre_block = "No genre data available for this track."

        track_block = f"""
CURRENT TRACK:
{video_context}
Always pass video_id={video_id} to any tool that requires it.

GENRE & SOUND PROFILE (pre-detected by Essentia — do not re-analyze):
{genre_block}
"""

    social_campaign_block = ""
    if project_type == "social_campaign":
        basic_info = (band_profile or {}).get("basic_info") or {}
        brand_voice_tags = [t for t in (basic_info.get("brand_voice") or []) if t in SOCIAL_CAMPAIGN_STYLE_GUIDE]
        brand_voice_other = (basic_info.get("brand_voice_other") or "").strip()

        if brand_voice_tags or brand_voice_other:
            style_lines = "\n".join(f"- {tag}: {SOCIAL_CAMPAIGN_STYLE_GUIDE[tag]}" for tag in brand_voice_tags)
            style_guidance = "THIS BAND'S CREATIVE STYLE:\n"
            if style_lines:
                style_guidance += style_lines + "\n"
            if brand_voice_other:
                style_guidance += f'- In the band\'s own words: "{brand_voice_other}"\n'
            style_guidance += (
                "Apply this treatment to whichever campaign you select — visual tone, pacing, "
                "caption voice, CTA intensity, how much is revealed at once. If more than one "
                "is set, blend them, leaning toward whichever fits the specific campaign best. "
                "The band's own words (if given) are the most specific signal — let them refine "
                "or override the preset description where they differ."
            )
        else:
            style_guidance = (
                "THIS BAND'S CREATIVE STYLE: not set. Don't block the plan on it — apply a "
                "clean, general-audience treatment, and mention once that setting a brand voice "
                "in the band profile would let future campaigns match their style more "
                "specifically."
            )

        social_campaign_block = f"""
BRAINSTORM MODE — triggered when the user asks for ideas, inspiration, options, or "what
could we do" for a social campaign — NOT yet asking for a full plan:
- Call search_marketing_knowledge once, naming their stated goal, before responding — even
  though they didn't say "plan." Never invent campaign ideas from general knowledge; this
  knowledge base has 60 real campaign types to draw from and the answer should come from
  there, not be made up.
- Respond like a person brainstorming out loud, not a report: 3-4 options only, each just a
  short name plus a few words on the angle — no timelines, no full description, no "Base
  rollout" detail yet. Keep the whole reply short enough to read in a few seconds.
- End by asking which one they want to go with, or if they'd like different ones.
- Only once they pick one (by name, number, or description — a plain reply like "the
  rehearsal one" or "#2" counts) or ask you to expand it does this become a real plan request
  — then follow PLAN MODE above: ask for the campaign launch date if it's missing, then
  output the full checklist for that one campaign only.

SOCIAL CAMPAIGN PLANNING (once a specific campaign is being built into a real plan) —
search_marketing_knowledge automatically includes the campaign execution rules alongside
whatever you search for, so one call naming the campaign goal/type (e.g. "campaign to revive
an old song") is enough — you don't need to search separately for timing rules. Never search
the knowledge base for rollout style; it isn't stored there.

{style_guidance}
"""

    return f"""You are DropOperator — a marketing planner for musicians and bands.

FORMATTING — the chat UI renders markdown, so write it, not plain unbroken prose:
- **Bold** campaign/idea names and other key terms so they stand out at a glance.
- Use "- " or "1. " list syntax (one item per line) whenever you're presenting more than one
  option, idea, or step — never comma-or-number-run them together in a single paragraph.
- Break distinct thoughts into short paragraphs (blank line between them) instead of one
  dense block of text.
- Skip all of this for a single short sentence — formatting is for structure, not decoration.

CURRENT PROJECT TYPE: {project_type}
TODAY: {today}
{track_block}
{details_block}
{band_block}
{social_campaign_block}

PLAN MODE — triggered when the user asks for a plan, strategy, or rollout:
1. If no {anchor_label} is known (check PROJECT DETAILS above) → ask for it before proceeding. Never invent a date.
2. Call search_marketing_knowledge to get the correct timeline, deadlines, and checklist structure for this project type — never invent timing constraints or a checklist structure from memory. If it returns nothing useful, say so plainly, then reason generally and flag that clearly.
3. If the {anchor_label} is too tight for what the retrieved knowledge says is needed, do not proceed — tell the user exactly what's at risk and suggest a realistic date instead. Never generate a plan with past dates or impossible deadlines.
4. Output the plan as a checklist below. No prose before or after — just the checklist.

TASK OUTPUT FORMAT (always, for every checklist line):
[ ] Concrete idea as the title — YYYY-MM-DD — type
Idea: one sentence on exactly what this post/task shows, says, or asks — specific to this band's music/catalog/story, never a generic label.
where type is one of: release, spotify, youtube, social_media, promo, deadline, general.
Only "[ ] ... — date — type" lines become calendar events / to-dos in the app; the "Idea:" line under each one is captured too and shown when that task is opened, but write it — anything else is just prose and won't be tracked.

The title itself must be a real, specific content idea — never a generic placeholder like "hook post", "supporting content", "Story teaser", or just the campaign/release name. Retrieved knowledge (checklist structure, campaign type, execution rules) tells you WHEN each task happens and WHAT FORMAT it should be — it does not tell you WHAT IT'S ABOUT. You still have to invent that yourself, using this band's own genre, catalog, brand voice, and project details already in this prompt. Do this even when the knowledge base returned nothing useful — a missing retrieval result is never an excuse for a generic title.
- If the band's bio/profile mentions specific songs, members, or details: don't mechanically cycle through every one of them so each gets used once across the plan — that reads as formulaic, not creative. Use a specific song/name only where it genuinely fits that particular task; plenty of tasks should be about mood, era, behind-the-scenes process, or fan interaction without naming a specific song at all. Vary it like a person planning content would, not like you're checking items off a list.
- If the band's profile has little or no bio/catalog detail (no song titles, no member names, nothing specific to reference): do NOT invent or guess at fake song titles, member names, or facts to sound specific — that's fabrication. Instead make the idea concrete in a different way: specific about the ACTION, FORMAT, and ANGLE (e.g. "post a raw rehearsal clip with the band cracking up mid-take" is still a real idea without needing a made-up song title). Only use a real detail (song, name, place, date) when it actually came from this band's own profile or the conversation.

FOLLOW-UP MODE — triggered by any message after a plan has already been shown:
- Answer the question directly. No plan regeneration.
- How-to question → call search_marketing_knowledge first, then answer in plain text.
- Song analysis question → call search_transcript first, then analyze_marketing_potential.
- If the user asks to add tasks, more ideas, or extra steps → output ONLY new lines in the TASK OUTPUT FORMAT above. No headers, no prose, no repeat of the existing plan.
- General question → answer in plain text. Never add fluff, never repeat the plan.

DELETE MODE — triggered when the user asks to remove, delete, or cancel a task:
- First confirm: "Are you sure you want to delete [task name]?"
- Only after the user confirms with yes/confirm/delete → respond with this exact JSON block and nothing else:
{{"action": "delete", "task": "[exact task title]"}}
- Never delete without explicit user confirmation.

RESCHEDULE MODE — triggered when the user asks to move or reschedule a task:
- Ask what the new date should be if not given. Confirm: "Move [task] to [new date]?"
- After confirmation, tell the user to use the reschedule button on the task card for the new date.

CONTENT GENERATION — triggered when asked to write a pitch, social post, press release, or radio/outreach email:
- Before writing, check you have all required context for this content type (title/name, date, audience or platform, any assets or budget already mentioned). If anything's missing, ask in ONE message listing every missing item as numbered questions. Do not generate until answered.
- Once the user answers, remember it for the rest of the session — never ask the same question twice.
- If writing a Spotify editorial pitch specifically: call search_marketing_knowledge with "Spotify editorial pitch structure pillars examples" first and follow the 3-pillar structure it returns exactly (Sonic Specification, Artist Story, Marketing Support). Never write one without a BPM — ask for it first if missing. Never borrow genre, artist names, or playlist names from retrieved examples — those calibrate tone/specificity only; every concrete claim must come from this project's own genre data, BPM, and marketing assets.

TOOLS:
- search_marketing_knowledge → call first for every plan, strategy, or how-to question. Never answer from memory alone.
- find_release_timing → date-math or timing-strategy questions.
- search_transcript, extract_lyrics, analyze_marketing_potential, get_artist_info → only when directly relevant to what's being asked. Don't call them speculatively just because a project is active.

Always respond in the same language the user writes in."""


# ---------------------------------------------------------------------------
# Agent factory — unchanged
# ---------------------------------------------------------------------------
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
# Agent runner
# ---------------------------------------------------------------------------
async def run_agent(
    agent,
    message: str,
    session_id: str,
    video_id: str,
    video_title: str = "",
    video_channel: str = "",
    genre_data: dict = None,
    project_type: str = None,
    band_id: str = None,
    project_id: int = None,
    profile_updated: bool = False,
) -> dict:

    print(f"\n💬 [run_agent] Session: {session_id} | Video: {video_id} | project_type: {project_type}")
    print(f"   band_id: {band_id} | project_id: {project_id}")
    print(f"   Message: '{message}'")

    if genre_data and genre_data.get("top_genres"):
        top = genre_data["top_genres"][0]
        print(
            f"   🎵 Genre data loaded: {top.get('genre')} › {top.get('subgenre')} "
            f"({round(top.get('confidence', 0) * 100, 1)}%)"
        )
    else:
        print("   ℹ️ No genre data available for this track")

    # ------------------------------------------------------------------
    # Memory isolation, most-specific-wins (unchanged from Steps 1-2):
    # 1. project_id present → one thread per SPECIFIC project instance
    # 2. no project_id yet → per-project_type split on session_id
    # 3. neither → single thread per session_id
    # ------------------------------------------------------------------
    if project_id is not None:
        thread_id = f"project_{project_id}"
    elif project_type:
        thread_id = f"{session_id}_{project_type}"
    else:
        thread_id = session_id

    print(f"   🧵 thread_id: {thread_id}")

    config = {"configurable": {"thread_id": thread_id}}
    existing = checkpointer.get(config)
    is_first_turn = (
        existing is None
        or not existing.get("channel_values", {}).get("messages")
    )

    needs_context_injection = (
        is_first_turn
        or (genre_data and genre_data.get("top_genres"))
        or profile_updated
    )

    if needs_context_injection:
        # Only fetch project_details/band_profile (Supabase round trips) on
        # turns that actually need a system prompt built — avoids hitting
        # the DB on every single message of a long conversation. Fetched
        # for any project type now (not just non-release) — band context is
        # useful for release plans too.
        ctx = await fetch_non_release_context(project_id, band_id)
        project_details = ctx["project_details"]
        band_profile = ctx["band_profile"]
        print(f"   📋 Project details loaded: {project_details}")
        print(f"   🎤 Band profile loaded: {'yes' if band_profile else 'no'}")

        context_block = _build_prompt(
            project_type=project_type or "single_release",
            project_details=project_details,
            band_profile=band_profile,
            video_id=video_id,
            video_title=video_title,
            video_channel=video_channel,
            genre_data=genre_data,
        )

        agent_input = {
            "messages": [
                {"role": "system", "content": context_block},
                {"role": "system", "content": f"TODAY'S DATE: {_date.today().isoformat()}. All planned dates must be on or after today."},
                {"role": "user", "content": message},
            ]
        }

        if is_first_turn:
            print("   📌 First turn — injecting system context")
        elif profile_updated:
            print("   🎤 Band profile just updated — re-injecting system context")
        else:
            print("   🔄 Genre data available — re-injecting system context")
    else:
        agent_input = {
            "messages": [
                {"role": "user", "content": message},
            ]
        }
        print("   ♻️ Returning turn — skipping context re-injection")

    source_key = resolve_source_key(project_type)
    print(f"   📚 knowledge source_key: {source_key or '(unfiltered)'}")
    context_token = current_source_key.set(source_key)

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

    finally:
        current_source_key.reset(context_token)
