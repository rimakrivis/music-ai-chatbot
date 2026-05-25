"use client";

import { useState, useEffect } from "react";
import {
  format, startOfMonth, endOfMonth, eachDayOfInterval,
  getDay, addMonths, subMonths, isSameDay, parseISO, isToday
} from "date-fns";

interface CalendarEvent {
  id: number;
  title: string;
  date: string;
  type: string;
}

interface CalendarPanelProps {
  sessionId: string;
  refreshTrigger?: number;
}

const TYPE_DOT: Record<string, string> = {
  release:      "bg-violet-500",
  deadline:     "bg-rose-500",
  promo:        "bg-sky-500",
  general:      "bg-amber-400",
  social_media: "bg-pink-500",
  spotify:      "bg-green-500",
  youtube:      "bg-red-500",
};

const TYPE_PILL: Record<string, string> = {
  release:      "bg-violet-100 text-violet-700 border-violet-200",
  deadline:     "bg-rose-100 text-rose-700 border-rose-200",
  promo:        "bg-sky-100 text-sky-700 border-sky-200",
  general:      "bg-amber-50 text-amber-700 border-amber-200",
  social_media: "bg-pink-50 text-pink-700 border-pink-200",
  spotify:      "bg-green-50 text-green-700 border-green-200",
  youtube:      "bg-red-50 text-red-700 border-red-200",
};

export default function CalendarPanel({ sessionId, refreshTrigger }: CalendarPanelProps) {
  const [currentMonth, setCurrentMonth] = useState<Date>(new Date());
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDay, setSelectedDay] = useState<Date | null>(null);
  const [editingEvent, setEditingEvent] = useState<CalendarEvent | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDate, setEditDate] = useState("");
  useEffect(() => {
  setCurrentMonth(new Date());
}, []);


  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  async function fetchEvents() {
    try {
      const res = await fetch(`${API}/calendar/events/${sessionId}`);
      const data = await res.json();
      setEvents(data.events || []);
    } catch (e) {
      console.error("Failed to fetch calendar events", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchEvents(); }, [sessionId, refreshTrigger]);

  async function handleDelete(id: number) {
    try {
      await fetch(`${API}/calendar/events/${id}`, { method: "DELETE" });
      setEvents((prev) => prev.filter((e) => e.id !== id));
    } catch (e) {
      console.error("Failed to delete event", e);
    }
  }

  async function handleEdit() {
    if (!editingEvent) return;
    try {
      await fetch(`${API}/calendar/events/${editingEvent.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: editTitle, date: editDate }),
      });
      setEvents((prev) =>
        prev.map((e) => e.id === editingEvent.id ? { ...e, title: editTitle, date: editDate } : e)
      );
      setEditingEvent(null);
    } catch (e) {
      console.error("Failed to update event", e);
    }
  }

  const monthStart = startOfMonth(currentMonth);
  const monthEnd = endOfMonth(currentMonth);
  const days = eachDayOfInterval({ start: monthStart, end: monthEnd });
  const startPadding = getDay(monthStart);

  const eventsOnDay = (day: Date) => events.filter((e) => isSameDay(parseISO(e.date), day));
  const selectedDayEvents = selectedDay ? eventsOnDay(selectedDay) : [];

  // Upcoming events (next 30 days)
  const upcomingEvents = events
    .filter((e) => {
      const d = parseISO(e.date);
      const now = new Date();
      return d >= now;
    })
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(0, 5);

  return (
    <div className="flex flex-col h-full">
      {/* Month navigation */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-slate-800 font-semibold text-sm tracking-wide">Calendar</h3>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setCurrentMonth((m) => subMonths(m, 1))}
            className="w-6 h-6 flex items-center justify-center rounded-full hover:bg-slate-100 text-slate-500 hover:text-slate-800 transition-colors text-sm"
          >‹</button>
          <span className="text-slate-600 text-xs font-medium w-20 text-center">
            {format(currentMonth, "MMM yyyy")}
          </span>
          <button
            onClick={() => setCurrentMonth((m) => addMonths(m, 1))}
            className="w-6 h-6 flex items-center justify-center rounded-full hover:bg-slate-100 text-slate-500 hover:text-slate-800 transition-colors text-sm"
          >›</button>
        </div>
      </div>

      {/* Day labels */}
      <div className="grid grid-cols-7 mb-1">
        {["S","M","T","W","T","F","S"].map((d, i) => (
          <div key={i} className="text-slate-400 text-xs text-center py-1 font-medium">{d}</div>
        ))}
      </div>

      {/* Calendar grid */}
      {loading ? (
        <div className="text-slate-400 text-xs text-center py-4">Loading…</div>
      ) : (
        <div className="grid grid-cols-7 gap-0.5 mb-4">
          {Array.from({ length: startPadding }).map((_, i) => <div key={`pad-${i}`} />)}
          {days.map((day) => {
            const dayEvents = eventsOnDay(day);
            const isSelected = selectedDay && isSameDay(day, selectedDay);
            const todayDay = isToday(day);
            return (
              <button
                key={day.toISOString()}
                onClick={() => setSelectedDay(isSelected ? null : day)}
                className={`relative flex flex-col items-center py-1.5 rounded-lg text-xs transition-all
                  ${isSelected
                    ? "bg-gradient-to-br from-violet-500 to-indigo-600 text-white shadow-md shadow-violet-200"
                    : todayDay
                    ? "bg-violet-50 text-violet-700 font-bold border border-violet-200"
                    : "text-slate-600 hover:bg-slate-100"
                  }`}
              >
                {format(day, "d")}
                {dayEvents.length > 0 && (
                  <div className="flex gap-0.5 mt-0.5">
                    {dayEvents.slice(0, 3).map((e) => (
                      <span
                        key={e.id}
                        className={`w-1 h-1 rounded-full ${isSelected ? "bg-white/70" : TYPE_DOT[e.type] || "bg-slate-400"}`}
                      />
                    ))}
                  </div>
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Selected day events */}
      {selectedDay && (
        <div className="flex flex-col gap-2 mb-4">
          <p className="text-slate-500 text-xs font-medium">
            {isToday(selectedDay) ? "Today" : format(selectedDay, "MMM d, yyyy")}
          </p>
          {selectedDayEvents.length === 0 ? (
            <p className="text-slate-300 text-xs italic">No events</p>
          ) : (
            selectedDayEvents.map((event) => (
              <div key={event.id} className="bg-white border border-slate-200 rounded-xl px-3 py-2.5 shadow-sm flex items-start justify-between gap-2">
                <div className="flex flex-col gap-1 min-w-0">
                  <p className="text-slate-700 text-xs font-medium truncate">{event.title}</p>
                  <span className={`text-xs border px-1.5 py-0.5 rounded-full self-start ${TYPE_PILL[event.type] || TYPE_PILL.general}`}>
                    {event.type}
                  </span>
                </div>
                <div className="flex gap-1.5 shrink-0">
                  <button onClick={() => { setEditingEvent(event); setEditTitle(event.title); setEditDate(event.date); }}
                    className="text-slate-400 hover:text-violet-600 transition-colors text-xs">✏️</button>
                  <button onClick={() => handleDelete(event.id)}
                    className="text-slate-400 hover:text-rose-500 transition-colors text-sm leading-none">×</button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Upcoming events */}
      {upcomingEvents.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-slate-500 text-xs font-medium uppercase tracking-wider">Upcoming</p>
          {upcomingEvents.map((event) => (
            <div key={event.id} className="flex items-center gap-2.5">
              <div className={`w-2 h-2 rounded-full shrink-0 ${TYPE_DOT[event.type] || "bg-slate-400"}`} />
              <div className="min-w-0 flex-1">
                <p className="text-slate-700 text-xs truncate">{event.title}</p>
                <p className="text-slate-400 text-xs">{format(parseISO(event.date), "MMM d")}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Edit modal */}
      {editingEvent && (
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 w-80 shadow-2xl flex flex-col gap-4">
            <h4 className="text-slate-800 text-sm font-semibold">Edit Event</h4>
            <input
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-slate-700 text-sm outline-none focus:border-violet-400 focus:ring-2 focus:ring-violet-100"
              placeholder="Event title"
            />
            <input
              type="date"
              value={editDate}
              onChange={(e) => setEditDate(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-slate-700 text-sm outline-none focus:border-violet-400 focus:ring-2 focus:ring-violet-100"
            />
            <div className="flex gap-2 justify-end">
              <button onClick={() => setEditingEvent(null)}
                className="text-slate-500 hover:text-slate-800 text-sm px-4 py-2 rounded-xl hover:bg-slate-100 transition-colors">
                Cancel
              </button>
              <button onClick={handleEdit}
                className="bg-gradient-to-r from-violet-500 to-indigo-600 text-white text-sm px-4 py-2 rounded-xl shadow-md shadow-violet-200 hover:shadow-lg transition-all">
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}