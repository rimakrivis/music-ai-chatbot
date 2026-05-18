import aiosqlite
import os
from pathlib import Path

# Database path — stored in ./data/app.db so it survives Render restarts
DB_DIR = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "app.db"

async def create_tables():
    """Create tables on startup if they don't exist."""
    print(f"📦 Setting up database at {DB_PATH}")
    
    # Make sure the data/ folder exists
    DB_DIR.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                video_id TEXT NOT NULL,
                title TEXT NOT NULL,
                date TEXT NOT NULL,
                type TEXT DEFAULT 'general',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                video_id TEXT NOT NULL,
                title TEXT NOT NULL,
                due_date TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        await db.commit()
        print("✅ Database tables ready")


async def get_db():
    """Get a database connection."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


# ── Calendar Events ────────────────────────────────────────────────────────────

async def save_calendar_events(session_id: str, video_id: str, events: list) -> int:
    """Insert multiple calendar events. Returns count saved."""
    print(f"📅 Saving {len(events)} calendar events for session {session_id}")
    
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            for event in events:
                await db.execute(
                    "INSERT INTO calendar_events (session_id, video_id, title, date, type) VALUES (?, ?, ?, ?, ?)",
                    (session_id, video_id, event["title"], event["date"], event.get("type", "general"))
                )
            await db.commit()
            print(f"✅ Saved {len(events)} calendar events")
            return len(events)
        except Exception as e:
            print(f"❌ Error saving calendar events: {e}")
            raise


async def get_calendar_events(session_id: str) -> list:
    """Fetch all calendar events for a session."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        try:
            cursor = await db.execute(
                "SELECT * FROM calendar_events WHERE session_id = ? ORDER BY date ASC",
                (session_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"❌ Error fetching calendar events: {e}")
            raise


async def update_calendar_event(event_id: int, updates: dict) -> bool:
    """Update title and/or date of a calendar event."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            fields = []
            values = []
            if "title" in updates:
                fields.append("title = ?")
                values.append(updates["title"])
            if "date" in updates:
                fields.append("date = ?")
                values.append(updates["date"])
            
            if not fields:
                return False
            
            values.append(event_id)
            await db.execute(
                f"UPDATE calendar_events SET {', '.join(fields)} WHERE id = ?",
                values
            )
            await db.commit()
            print(f"✅ Updated calendar event {event_id}")
            return True
        except Exception as e:
            print(f"❌ Error updating calendar event: {e}")
            raise


async def delete_calendar_event(event_id: int) -> bool:
    """Delete a calendar event by id."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
            await db.commit()
            print(f"✅ Deleted calendar event {event_id}")
            return True
        except Exception as e:
            print(f"❌ Error deleting calendar event: {e}")
            raise


# ── Todos ──────────────────────────────────────────────────────────────────────

async def save_todos(session_id: str, video_id: str, items: list) -> int:
    """Insert multiple todo items. Returns count saved."""
    print(f"✅ Saving {len(items)} todos for session {session_id}")
    
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            for item in items:
                await db.execute(
                    "INSERT INTO todos (session_id, video_id, title, due_date) VALUES (?, ?, ?, ?)",
                    (session_id, video_id, item["title"], item.get("due_date"))
                )
            await db.commit()
            print(f"✅ Saved {len(items)} todos")
            return len(items)
        except Exception as e:
            print(f"❌ Error saving todos: {e}")
            raise


async def get_todos(session_id: str) -> list:
    """Fetch all todos for a session."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        try:
            cursor = await db.execute(
                "SELECT * FROM todos WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"❌ Error fetching todos: {e}")
            raise


async def update_todo(todo_id: int, updates: dict) -> bool:
    """Update title, due_date, and/or status of a todo."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            fields = []
            values = []
            for field in ["title", "due_date", "status"]:
                if field in updates:
                    fields.append(f"{field} = ?")
                    values.append(updates[field])
            
            if not fields:
                return False
            
            values.append(todo_id)
            await db.execute(
                f"UPDATE todos SET {', '.join(fields)} WHERE id = ?",
                values
            )
            await db.commit()
            print(f"✅ Updated todo {todo_id}")
            return True
        except Exception as e:
            print(f"❌ Error updating todo: {e}")
            raise


async def delete_todo(todo_id: int) -> bool:
    """Delete a todo by id."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            await db.commit()
            print(f"✅ Deleted todo {todo_id}")
            return True
        except Exception as e:
            print(f"❌ Error deleting todo: {e}")
            raise