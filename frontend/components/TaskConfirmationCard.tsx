"use client";

import { useState } from "react";

interface CalendarEvent {
  title: string;
  date: string;
  type: string;
}

interface TodoItem {
  title: string;
  due_date: string | null;
}

interface TaskConfirmationCardProps {
  sessionId: string;
  videoId: string;
  calendarEvents: CalendarEvent[];
  todoItems: TodoItem[];
  onConfirm: () => void;
  onDismiss: () => void;
}

const TYPE_PILL: Record<string, string> = {
  release:      "bg-violet-100 text-violet-700 border-violet-200",
  deadline:     "bg-rose-100 text-rose-700 border-rose-200",
  promo:        "bg-sky-100 text-sky-700 border-sky-200",
  general:      "bg-amber-50 text-amber-700 border-amber-200",
  social_media: "bg-pink-50 text-pink-700 border-pink-200",
  spotify:      "bg-green-50 text-green-700 border-green-200",
  youtube:      "bg-red-50 text-red-700 border-red-200",
};

export default function TaskConfirmationCard({
  sessionId, videoId, calendarEvents, todoItems, onConfirm, onDismiss
}: TaskConfirmationCardProps) {
  const [selectedEvents, setSelectedEvents] = useState<boolean[]>(calendarEvents.map(() => true));
  const [selectedTodos, setSelectedTodos] = useState<boolean[]>(todoItems.map(() => true));
  const [saving, setSaving] = useState(false);

  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const totalSelected = selectedEvents.filter(Boolean).length + selectedTodos.filter(Boolean).length;

  async function handleConfirm() {
    setSaving(true);
    try {
      const eventsToSave = calendarEvents.filter((_, i) => selectedEvents[i]);
      const todosToSave = todoItems.filter((_, i) => selectedTodos[i]);

      if (eventsToSave.length > 0) {
        await fetch(`${API}/calendar/events`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId, video_id: videoId, events: eventsToSave }),
        });
      }
      if (todosToSave.length > 0) {
        await fetch(`${API}/todos`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId, video_id: videoId, items: todosToSave }),
        });
      }
      onConfirm();
    } catch (e) {
      console.error("Failed to save tasks", e);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-lg shadow-slate-100 p-4 mt-3 max-w-lg">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-md shadow-violet-200">
          <span className="text-white text-xs">✨</span>
        </div>
        <div>
          <p className="text-slate-800 text-sm font-semibold">Save to Calendar & Tasks</p>
          <p className="text-slate-400 text-xs">Uncheck anything you don't want to save</p>
        </div>
      </div>

      {/* Calendar events */}
      {calendarEvents.length > 0 && (
        <div className="mb-3">
          <p className="text-slate-500 text-xs font-medium uppercase tracking-wider mb-2">📅 Calendar Events</p>
          <div className="flex flex-col gap-1.5 max-h-40 overflow-y-auto pr-1">
            {calendarEvents.map((event, i) => (
              <label key={i} className={`flex items-center gap-2.5 p-2.5 rounded-xl cursor-pointer transition-colors
                ${selectedEvents[i] ? "bg-violet-50 border border-violet-100" : "bg-slate-50 border border-slate-100"}`}>
                <input
                  type="checkbox"
                  checked={selectedEvents[i]}
                  onChange={() => setSelectedEvents((prev) => prev.map((v, j) => j === i ? !v : v))}
                  className="accent-violet-600 w-3.5 h-3.5"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-slate-700 text-xs font-medium truncate">{event.title}</p>
                  <p className="text-slate-400 text-xs">{event.date}</p>
                </div>
                <span className={`text-xs border px-1.5 py-0.5 rounded-full shrink-0 ${TYPE_PILL[event.type] || TYPE_PILL.general}`}>
                  {event.type}
                </span>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Todo items */}
      {todoItems.length > 0 && (
        <div className="mb-4">
          <p className="text-slate-500 text-xs font-medium uppercase tracking-wider mb-2">✅ Tasks</p>
          <div className="flex flex-col gap-1.5 max-h-40 overflow-y-auto pr-1">
            {todoItems.map((item, i) => (
              <label key={i} className={`flex items-center gap-2.5 p-2.5 rounded-xl cursor-pointer transition-colors
                ${selectedTodos[i] ? "bg-violet-50 border border-violet-100" : "bg-slate-50 border border-slate-100"}`}>
                <input
                  type="checkbox"
                  checked={selectedTodos[i]}
                  onChange={() => setSelectedTodos((prev) => prev.map((v, j) => j === i ? !v : v))}
                  className="accent-violet-600 w-3.5 h-3.5"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-slate-700 text-xs font-medium truncate">{item.title}</p>
                  {item.due_date && <p className="text-slate-400 text-xs">Due {item.due_date}</p>}
                </div>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 justify-end">
        <button onClick={onDismiss}
          className="text-slate-400 hover:text-slate-700 text-xs px-3 py-2 rounded-xl hover:bg-slate-100 transition-colors">
          Dismiss
        </button>
        <button
          onClick={handleConfirm}
          disabled={saving || totalSelected === 0}
          className="bg-gradient-to-r from-violet-500 to-indigo-600 text-white text-xs px-4 py-2 rounded-xl shadow-md shadow-violet-200 hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? "Saving…" : `Save ${totalSelected} item${totalSelected !== 1 ? "s" : ""}`}
        </button>
      </div>
    </div>
  );
}