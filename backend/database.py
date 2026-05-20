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
# Calendar Events
# ---------------------------------------------------------------------------

async def save_calendar_events(session_id: str, video_id: str, events: list) -> int:
    """Insert multiple calendar events. Returns count saved."""
    print(f"📅 Saving {len(events)} calendar events for session {session_id}")

    if not events:
        return 0

    try:
        supabase = get_supabase()
        rows = [
            {
                "session_id": session_id,
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


async def get_calendar_events(session_id: str) -> list:
    """Fetch all calendar events for a session, ordered by date."""
    try:
        supabase = get_supabase()
        result = (
            supabase.table("calendar_events")
            .select("*")
            .eq("session_id", session_id)
            .order("date")
            .execute()
        )
        print(f"📅 Fetched {len(result.data)} calendar events for session {session_id}")
        return result.data
    except Exception as e:
        print(f"❌ Error fetching calendar events: {e}")
        raise


async def update_calendar_event(event_id: int, updates: dict) -> bool:
    """Update title and/or date of a calendar event."""
    try:
        supabase = get_supabase()
        allowed = {k: v for k, v in updates.items() if k in ("title", "date")}
        if not allowed:
            return False
        supabase.table("calendar_events").update(allowed).eq("id", event_id).execute()
        print(f"✅ Updated calendar event {event_id}")
        return True
    except Exception as e:
        print(f"❌ Error updating calendar event: {e}")
        raise


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

async def save_todos(session_id: str, video_id: str, items: list) -> int:
    """Insert multiple todo items. Returns count saved."""
    print(f"✅ Saving {len(items)} todos for session {session_id}")

    if not items:
        return 0

    try:
        supabase = get_supabase()
        rows = [
            {
                "session_id": session_id,
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


async def get_todos(session_id: str) -> list:
    """Fetch all todos for a session, ordered by created_at."""
    try:
        supabase = get_supabase()
        result = (
            supabase.table("todos")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at")
            .execute()
        )
        print(f"✅ Fetched {len(result.data)} todos for session {session_id}")
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