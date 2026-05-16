# backend/tools/find_release_timing.py
# Tool 5: find_release_timing
# Generates a music release strategy based on genre and audience size.
# IMPORTANT ARCHITECTURE NOTE:
# - Date math and timeline calculations = plain Python (no LLM needed)
# - Strategic recommendations = GPT-4o
# This split is intentional: use LLMs only where reasoning adds value.

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from datetime import datetime, timedelta
from config import OPENAI_API_KEY

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.3,
    api_key=OPENAI_API_KEY
)

# Plain Python lookup tables — no LLM needed for this logic
BEST_RELEASE_DAYS = {
    "friday": "Friday is the music industry standard — all major labels release on Fridays. "
              "Spotify editorial playlists refresh on Fridays, maximising first-week streams.",
    "wednesday": "Wednesday works well for independent artists — less competition than Friday, "
                 "gives 2 days of momentum before the weekend listening spike.",
    "tuesday": "Tuesday suits niche or genre-specific releases targeting blog coverage "
               "and radio adds, which traditionally happen mid-week."
}

PLATFORM_PRIORITY_BY_GENRE = {
    "pop": ["TikTok", "Instagram Reels", "Spotify", "YouTube", "Apple Music"],
    "hip-hop": ["TikTok", "YouTube", "Spotify", "Instagram Reels", "Apple Music"],
    "rap": ["TikTok", "YouTube", "Spotify", "Instagram Reels", "Apple Music"],
    "electronic": ["Spotify", "SoundCloud", "YouTube", "Instagram Reels", "TikTok"],
    "edm": ["Spotify", "SoundCloud", "YouTube", "Instagram Reels", "TikTok"],
    "rock": ["Spotify", "YouTube", "Instagram", "Facebook", "Apple Music"],
    "indie": ["Spotify", "Instagram", "YouTube", "Bandcamp", "TikTok"],
    "r&b": ["TikTok", "Instagram Reels", "Spotify", "YouTube", "Apple Music"],
    "latin": ["TikTok", "YouTube", "Spotify", "Instagram Reels", "Apple Music"],
    "country": ["Spotify", "YouTube", "Facebook", "Instagram", "Apple Music"],
    "default": ["Spotify", "TikTok", "Instagram Reels", "YouTube", "Apple Music"]
}

MINIMUM_PREP_DAYS = {
    "micro": 14,    # 0–1k followers — no Spotify pitch needed
    "small": 21,    # 1k–10k followers — basic campaign
    "medium": 28,   # 10k–100k followers — full campaign with Spotify pitch
    "large": 35     # 100k+ followers — full campaign with music video window
}


def _classify_audience(audience_size: str) -> str:
    """
    Classifies audience size string into a category for timeline logic.
    Accepts numbers or descriptive strings.
    Pure Python — no LLM.
    """
    size_lower = audience_size.lower().strip()

    # Handle descriptive inputs
    if any(word in size_lower for word in ["micro", "tiny", "starting", "0", "none"]):
        return "micro"
    if any(word in size_lower for word in ["small", "growing"]):
        return "small"
    if any(word in size_lower for word in ["medium", "mid"]):
        return "medium"
    if any(word in size_lower for word in ["large", "big", "established"]):
        return "large"

    # Handle numeric inputs — strip non-numeric chars and parse
    numeric = "".join(c for c in size_lower if c.isdigit())
    if numeric:
        n = int(numeric)
        if n < 1000:
            return "micro"
        elif n < 10000:
            return "small"
        elif n < 100000:
            return "medium"
        else:
            return "large"

    return "small"  # safe default


def _get_platform_priority(genre: str) -> list[str]:
    """
    Returns platform priority list for a given genre.
    Tries exact match first, then partial match, then falls back to default.
    Pure Python — no LLM.
    """
    genre_lower = genre.lower().strip()

    # Exact match
    if genre_lower in PLATFORM_PRIORITY_BY_GENRE:
        return PLATFORM_PRIORITY_BY_GENRE[genre_lower]

    # Partial match — e.g. "indie pop" matches "pop"
    for key in PLATFORM_PRIORITY_BY_GENRE:
        if key in genre_lower or genre_lower in key:
            return PLATFORM_PRIORITY_BY_GENRE[key]

    return PLATFORM_PRIORITY_BY_GENRE["default"]


def _build_timeline(today: datetime, min_prep_days: int) -> dict:
    """
    Calculates all key dates in the release timeline.
    All date math done in plain Python — no LLM.
    Returns a dict of milestone name -> date string.
    """
    # Release day = next Friday after minimum prep window
    release_candidate = today + timedelta(days=min_prep_days)

    # Push forward to the next Friday (weekday 4)
    days_until_friday = (4 - release_candidate.weekday()) % 7
    if days_until_friday == 0:
        days_until_friday = 7  # Never release on "today" even if it's Friday
    release_date = release_candidate + timedelta(days=days_until_friday)

    return {
        "today": today.strftime("%B %d, %Y"),
        "cover_art_deadline": (today + timedelta(days=5)).strftime("%B %d, %Y"),
        "distributor_upload": (today + timedelta(days=6)).strftime("%B %d, %Y"),
        "spotify_pitch_deadline": (release_date - timedelta(days=7)).strftime("%B %d, %Y"),
        "spotify_pitch_ideal": (release_date - timedelta(days=28)).strftime("%B %d, %Y"),
        "pre_release_teasers_start": (release_date - timedelta(days=14)).strftime("%B %d, %Y"),
        "release_date": release_date.strftime("%B %d, %Y (%A)"),
        "post_release_review": (release_date + timedelta(days=7)).strftime("%B %d, %Y"),
        "campaign_end": (release_date + timedelta(days=14)).strftime("%B %d, %Y"),
    }


@tool
def find_release_timing(genre: str = "pop", audience_size: str = "small") -> str:
    """
    Generate a complete music release strategy with timeline and platform recommendations.
    Use this tool when the user asks when they should release a song, what the best
    release date is, how to plan a music launch, release timeline, or release strategy.
    If genre or audience size are not mentioned, use reasonable defaults.

    Args:
        genre: The genre of the song (e.g. 'pop', 'hip-hop', 'indie'). Default: 'pop'.
        audience_size: The artist's current following size (e.g. '5000', 'small', 'just starting'). Default: 'small'.
    """
    print(f"\n📅 [find_release_timing] Genre: '{genre}' | Audience: '{audience_size}'")

    # --- Plain Python section (no LLM) ---
    today = datetime.now()
    audience_category = _classify_audience(audience_size)
    min_prep_days = MINIMUM_PREP_DAYS[audience_category]
    platform_priority = _get_platform_priority(genre)
    timeline = _build_timeline(today, min_prep_days)
    platforms_str = " > ".join(platform_priority)

    print(f"   Audience category: {audience_category} | Min prep: {min_prep_days} days")
    print(f"   Calculated release date: {timeline['release_date']}")

    # --- GPT-4o section (strategic reasoning only) ---
    print("   Sending to GPT-4o for release strategy recommendations...")

    system_prompt = """You are DropOperator AI — a professional music release manager
and marketing strategist for independent artists.
Give practical, specific, actionable advice.
Never invent streaming statistics or chart positions.
Keep your tone professional but warm — expert manager and mentor.
Always respond in the same language the user writes in."""

    user_message = f"""Generate a release strategy for this artist:

Genre: {genre}
Audience size: {audience_size} (classified as: {audience_category})
Platform priority for this genre: {platforms_str}

Timeline already calculated:
- Today: {timeline['today']}
- Cover art deadline: {timeline['cover_art_deadline']}
- Upload to distributor: {timeline['distributor_upload']}
- Spotify pitch ideal date: {timeline['spotify_pitch_ideal']}
- Spotify pitch last chance: {timeline['spotify_pitch_deadline']}
- Teaser campaign starts: {timeline['pre_release_teasers_start']}
- RELEASE DATE: {timeline['release_date']}
- 7-day review: {timeline['post_release_review']}
- Campaign end: {timeline['campaign_end']}

Using this timeline, write a release strategy that includes:
1. Why Friday is recommended for this genre
2. What to do in the 2 weeks before release (3-4 specific actions)
3. What to do on release day (3-4 specific actions)
4. What to do in the 7 days after release (3-4 specific actions)
5. One honest piece of advice specific to a {audience_category}-sized artist releasing {genre}

Keep each section to 3-5 sentences maximum. Be specific and actionable."""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ])

        strategy = response.content.strip()

        # Combine the calculated timeline with the LLM strategy
        result = f"""RELEASE STRATEGY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Genre:           {genre}
Audience:        {audience_size}
Platform Order:  {platforms_str}

KEY DATES:
  Today:                  {timeline['today']}
  Cover art due:          {timeline['cover_art_deadline']}
  Upload to distributor:  {timeline['distributor_upload']}
  Spotify pitch (ideal):  {timeline['spotify_pitch_ideal']}
  Spotify pitch (latest): {timeline['spotify_pitch_deadline']}
  Teasers start:          {timeline['pre_release_teasers_start']}
  🎵 RELEASE DAY:         {timeline['release_date']}
  7-day review:           {timeline['post_release_review']}
  Campaign ends:          {timeline['campaign_end']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRATEGY:

{strategy}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

        print(f"   ✅ Release strategy generated")
        return result

    except Exception as e:
        # If LLM fails, still return the calculated timeline — it's useful on its own
        error_note = f"\n\n[Strategy generation failed: {str(e)}]"
        fallback = f"""RELEASE TIMELINE (strategy unavailable)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Platform Order: {platforms_str}
Release Date:   {timeline['release_date']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{error_note}"""
        print(f"   ⚠️  LLM failed, returning timeline only")
        return fallback