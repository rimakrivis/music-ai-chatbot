"""
database.py — Supabase Postgres client for Music AI Chatbot.

Same function signatures as the old aiosqlite version.
main.py imports these functions directly — no changes needed there.
"""

from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_ANON_KEY

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise RuntimeError("❌ SUPABASE_URL or SUPABASE_ANON_KEY is missing from .env")
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

async def create_tables():
    """
    No-op for Supabase — tables already created via SQL Editor in dashboard.
    Kept so main.py startup code doesn't need to change.
    """
    print("📦 Supabase connected — tables already exist in cloud ✓")


# ---------------------------------------------------------------------------
# Bands
# ---------------------------------------------------------------------------

async def get_or_create_band(owner_id: str) -> str:
    """
    Look up the band belonging to this owner_id (the persistent browser UUID).
    If none exists yet, create one. Returns the band's id (as a string).

    This is the ONLY place a new band gets created right now — one band per
    owner_id. When multi-band support is added later, this function stays,
    it just stops being the only way a band gets created.
    """
    if not owner_id:
        raise ValueError("❌ get_or_create_band called with empty owner_id")

    try:
        supabase = get_supabase()

        result = (
            supabase.table("bands")
            .select("id")
            .eq("owner_id", owner_id)
            .limit(1)
            .execute()
        )

        if result.data:
            band_id = result.data[0]["id"]
            print(f"🎸 Found existing band {band_id} for owner {owner_id}")
            return band_id

        insert_result = (
            supabase.table("bands")
            .insert({"owner_id": owner_id})
            .execute()
        )

        if not insert_result.data:
            raise RuntimeError("❌ Band insert returned no data")

        band_id = insert_result.data[0]["id"]
        print(f"🎸 Created new band {band_id} for owner {owner_id}")
        return band_id

    except Exception as e:
        print(f"❌ Error in get_or_create_band: {e}")
        raise


# ---------------------------------------------------------------------------
# Calendar Events
# ---------------------------------------------------------------------------

async def save_calendar_events(band_id: str, video_id: str | None, events: list) -> int:
    """Insert multiple calendar events for a band. video_id is optional —
    only present when the event is tied to a specific uploaded song."""
    print(f"📅 Saving {len(events)} calendar events for band {band_id}")

    if not events:
        return 0

    try:
        supabase = get_supabase()
        rows = [
            {
                "band_id": band_id,
                "video_id": video_id,
                "title": event["title"],
                "date": event["date"],
                "type": event.get("type", "general"),
            }
            for event in events
        ]
        supabase.table("calendar_events").insert(rows).execute()
        print(f"✅ Saved {len(rows)} calendar events")
        return len(rows)
    except Exception as e:
        print(f"❌ Error saving calendar events: {e}")
        raise


async def get_calendar_events(band_id: str) -> list:
    """Fetch all calendar events for a band, ordered by date."""
    try:
        supabase = get_supabase()
        result = (
            supabase.table("calendar_events")
            .select("*")
            .eq("band_id", band_id)
            .order("date")
            .execute()
        )
        print(f"📅 Fetched {len(result.data)} calendar events for band {band_id}")
        return result.data
    except Exception as e:
        print(f"❌ Error fetching calendar events: {e}")
        raise


async def update_calendar_event(event_id: int, updates: dict) -> bool:
    """Update title and/or date of a calendar event."""
    try:
        supabase = get_supabase()
        allowed = {k: v for k, v in updates.items() if k in ("title", "date", "saved_content")}
        if not allowed:
            return False
        supabase.table("calendar_events").update(allowed).eq("id", event_id).execute()
        print(f"✅ Updated calendar event {event_id}")
        return True
    except Exception as e:
        print(f"❌ Error updating calendar event: {e}")
        raise


async def delete_band_data(band_id: str) -> bool:
    """Delete all calendar events + todos belonging to a band (used by the
    'reset' button). Renamed from delete_session_data — same behavior,
    now scoped by band_id instead of session_id."""
    try:
        supabase = get_supabase()
        supabase.table("calendar_events").delete().eq("band_id", band_id).execute()
        supabase.table("todos").delete().eq("band_id", band_id).execute()
        print(f"✅ Deleted all data for band {band_id}")
        return True
    except Exception as e:
        print(f"❌ delete_band_data error: {e}")
        return False


async def delete_calendar_event(event_id: int) -> bool:
    """Delete a calendar event by id."""
    try:
        supabase = get_supabase()
        supabase.table("calendar_events").delete().eq("id", event_id).execute()
        print(f"✅ Deleted calendar event {event_id}")
        return True
    except Exception as e:
        print(f"❌ Error deleting calendar event: {e}")
        raise


# ---------------------------------------------------------------------------
# Todos
# ---------------------------------------------------------------------------

async def save_todos(band_id: str, video_id: str | None, items: list) -> int:
    """Insert multiple todo items for a band. video_id is optional —
    only present when the todo is tied to a specific uploaded song."""
    print(f"✅ Saving {len(items)} todos for band {band_id}")

    if not items:
        return 0

    try:
        supabase = get_supabase()
        rows = [
            {
                "band_id": band_id,
                "video_id": video_id,
                "title": item["title"],
                "due_date": item.get("due_date"),
            }
            for item in items
        ]
        supabase.table("todos").insert(rows).execute()
        print(f"✅ Saved {len(rows)} todos")
        return len(rows)
    except Exception as e:
        print(f"❌ Error saving todos: {e}")
        raise


async def get_todos(band_id: str) -> list:
    """Fetch all todos for a band, ordered by created_at."""
    try:
        supabase = get_supabase()
        result = (
            supabase.table("todos")
            .select("*")
            .eq("band_id", band_id)
            .order("created_at")
            .execute()
        )
        print(f"✅ Fetched {len(result.data)} todos for band {band_id}")
        return result.data
    except Exception as e:
        print(f"❌ Error fetching todos: {e}")
        raise


async def update_todo(todo_id: int, updates: dict) -> bool:
    """Update title, due_date, and/or status of a todo."""
    try:
        supabase = get_supabase()
        allowed = {k: v for k, v in updates.items() if k in ("title", "due_date", "status")}
        if not allowed:
            return False
        supabase.table("todos").update(allowed).eq("id", todo_id).execute()
        print(f"✅ Updated todo {todo_id}")
        return True
    except Exception as e:
        print(f"❌ Error updating todo: {e}")
        raise


async def delete_todo(todo_id: int) -> bool:
    """Delete a todo by id."""
    try:
        supabase = get_supabase()
        supabase.table("todos").delete().eq("id", todo_id).execute()
        print(f"✅ Deleted todo {todo_id}")
        return True
    except Exception as e:
        print(f"❌ Error deleting todo: {e}")
        raise