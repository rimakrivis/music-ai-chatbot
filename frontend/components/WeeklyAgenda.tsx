"use client";

import { useState } from "react";
import {
  format, startOfWeek, addDays, isSameDay, parseISO,
  addWeeks, subWeeks, isToday, isSameWeek
} from "date-fns";
import EventChatPanel from "./EventChatPanel";

interface CalendarEvent {
  id: number;
  title: string;
  date: string;
  type: string;
}

interface WeeklyAgendaProps {
  events: CalendarEvent[];
  sessionId: string;
  videoId: string;
  videoTitle: string;
  videoChannel: string;
  onEventSaved: () => void;
}

const TYPE_CONFIG: Record<string, { bg: string; border: string; text: string; dot: string; label: string }> = {
  release:      { bg: "bg-violet-100",  border: "border-violet-200", text: "text-violet-700", dot: "bg-violet-400",  label: "Release" },
  spotify:      { bg: "bg-green-100",   border: "border-green-200",  text: "text-green-700",  dot: "bg-green-400",   label: "Spotify" },
  youtube:      { bg: "bg-red-100",     border: "border-red-200",    text: "text-red-700",    dot: "bg-red-400",     label: "YouTube" },
  social_media: { bg: "bg-blue-100",    border: "border-blue-200",   text: "text-blue-700",   dot: "bg-blue-400",    label: "Social" },
  promo:        { bg: "bg-orange-100",  border: "border-orange-200", text: "text-orange-700", dot: "bg-orange-400",  label: "Promo" },
  deadline:     { bg: "bg-rose-100",    border: "border-rose-200",   text: "text-rose-700",   dot: "bg-rose-400",    label: "Deadline" },
  general:      { bg: "bg-slate-100",   border: "border-slate-200",  text: "text-slate-600",  dot: "bg-slate-400",   label: "General" },
};

const HOURS = Array.from({ length: 24 }, (_, i) => i);

export default function WeeklyAgenda({
  events, sessionId, videoId, videoTitle, videoChannel, onEventSaved
}: WeeklyAgendaProps) {
  const [currentWeek, setCurrentWeek] = useState(new Date());
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);

  const weekStart = startOfWeek(currentWeek, { weekStartsOn: 1 }); // Monday
  const weekDays = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  const eventsOnDay = (day: Date) =>
    events.filter((e) => isSameDay(parseISO(e.date), day));

  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  async function handleSaveToCalendar(eventData: { title: string; date: string; type: string }) {
    try {
      await fetch(`${API}/calendar/events`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          video_id: videoId,
          events: [eventData],
        }),
      });
      onEventSaved();
    } catch (e) {
      console.error("Failed to save event", e);
    }
  }

  const isCurrentWeek = isSameWeek(new Date(), currentWeek, { weekStartsOn: 1 });

  return (
    <div className="flex h-full overflow-hidden">
      {/* Agenda */}
      <div className={`flex flex-col overflow-hidden transition-all duration-300 ${selectedEvent ? "flex-1" : "w-full"}`}>

        {/* Week header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-white shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setCurrentWeek(new Date())}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-all ${
                isCurrentWeek
                  ? "bg-violet-600 text-white border-violet-600 shadow-md shadow-violet-200"
                  : "bg-white text-slate-600 border-slate-200 hover:border-violet-300"
              }`}
            >
              Today
            </button>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setCurrentWeek((w) => subWeeks(w, 1))}
                className="w-7 h-7 flex items-center justify-center rounded-full hover:bg-slate-100 text-slate-500 transition-colors"
              >‹</button>
              <button
                onClick={() => setCurrentWeek((w) => addWeeks(w, 1))}
                className="w-7 h-7 flex items-center justify-center rounded-full hover:bg-slate-100 text-slate-500 transition-colors"
              >›</button>
            </div>
            <h2 className="text-slate-800 font-semibold text-sm">
              {format(weekStart, "MMM d")} — {format(addDays(weekStart, 6), "MMM d, yyyy")}
            </h2>
          </div>
          <div className="flex items-center gap-3">
            {/* Legend */}
            <div className="hidden md:flex items-center gap-3">
              {Object.entries(TYPE_CONFIG).slice(0, 5).map(([type, cfg]) => (
                <div key={type} className="flex items-center gap-1.5">
                  <div className={`w-2 h-2 rounded-full ${cfg.dot}`} />
                  <span className="text-slate-400 text-xs">{cfg.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Day columns header */}
        <div className="grid grid-cols-8 border-b border-slate-100 bg-white shrink-0">
          <div className="py-3 px-2 text-slate-300 text-xs text-right pr-4">GMT</div>
          {weekDays.map((day) => {
            const todayDay = isToday(day);
            return (
              <div key={day.toISOString()} className={`py-3 text-center border-l border-slate-100 ${todayDay ? "bg-violet-50" : ""}`}>
                <p className="text-slate-400 text-xs font-medium">{format(day, "EEE")}</p>
                <p className={`text-sm font-bold mt-0.5 w-7 h-7 flex items-center justify-center rounded-full mx-auto
                  ${todayDay ? "bg-gradient-to-br from-violet-500 to-indigo-600 text-white shadow-md shadow-violet-200" : "text-slate-700"}`}>
                  {format(day, "d")}
                </p>
              </div>
            );
          })}
        </div>

        {/* Scrollable time grid */}
        <div className="flex-1 overflow-y-auto">
          <div className="grid grid-cols-8 relative">
            {/* Hour rows */}
            {HOURS.map((hour) => (
              <div key={hour} className="contents">
                {/* Time label */}
                <div className="py-3 px-2 text-slate-300 text-xs text-right pr-4 border-t border-slate-100 h-16 flex items-start pt-2">
                  {hour === 0 ? "" : `${hour}:00`}
                </div>
                {/* Day cells */}
                {weekDays.map((day) => {
                  const dayEvents = eventsOnDay(day);
                  const todayDay = isToday(day);
                  return (
                    <div
                      key={`${day.toISOString()}-${hour}`}
                      className={`border-t border-l border-slate-100 h-16 relative px-1 py-1
                        ${todayDay ? "bg-violet-50/30" : ""}`}
                    >
                      {/* Show events at 9am slot if no time specified */}
                      {hour === 9 && dayEvents.map((event) => {
                        const cfg = TYPE_CONFIG[event.type] || TYPE_CONFIG.general;
                        return (
                          <button
                            key={event.id}
                            onClick={() => setSelectedEvent(selectedEvent?.id === event.id ? null : event)}
                            className={`w-full text-left px-2 py-1.5 rounded-lg border text-xs font-medium transition-all hover:shadow-md hover:scale-[1.02] active:scale-100 mb-1
                              ${cfg.bg} ${cfg.border} ${cfg.text}
                              ${selectedEvent?.id === event.id ? "ring-2 ring-violet-400 ring-offset-1" : ""}`}
                          >
                            <div className="flex items-center gap-1.5">
                              <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${cfg.dot}`} />
                              <span className="truncate">{event.title}</span>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Event chat panel — slides in from right */}
      {selectedEvent && (
        <div className="w-96 shrink-0 border-l border-slate-200 flex flex-col overflow-hidden">
          <EventChatPanel
            event={selectedEvent}
            sessionId={sessionId}
            videoId={videoId}
            videoTitle={videoTitle}
            videoChannel={videoChannel}
            onClose={() => setSelectedEvent(null)}
            onSaveToCalendar={handleSaveToCalendar}
          />
        </div>
      )}
    </div>
  );
}