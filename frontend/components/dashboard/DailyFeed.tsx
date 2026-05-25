"use client";

import { CalendarEvent, EVENT_COLORS } from "@/lib/types";

interface DailyFeedProps {
  events: CalendarEvent[];
  onEventClick: (event: CalendarEvent) => void;
}

// ── Icons ──────────────────────────────────────────────────────────────────

const ChevronRightIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
    strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
    <path d="m9 18 6-6-6-6"/>
  </svg>
);

const CheckCircleIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
    strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
    <circle cx="12" cy="12" r="10"/><polyline points="9 12 11 14 15 10"/>
  </svg>
);

function getIconType(type: string, title: string): string {
  const t = title.toLowerCase();
  if (t.includes("spotify")) return "spotify";
  if (t.includes("youtube")) return "youtube";
  if (t.includes("instagram") || t.includes("tiktok") || t.includes("social")) return "social_media";
  if (t.includes("release") || t.includes("album") || t.includes("song")) return "release";
  if (t.includes("promo") || t.includes("press") || t.includes("interview") || t.includes("pitch")) return "promo";
  return type;
}

function EventIcon({ type, title = "" }: { type: string; title?: string }) {
  switch (getIconType(type, title)) {
    case "release":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
          <path d="M9 18V5l12-2v13"/>
          <circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>
        </svg>
      );
    case "spotify":
      return (
        <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
          <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
        </svg>
      );
    case "youtube":
      return (
        <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
          <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
        </svg>
      );
    case "social_media":
      return (
        <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
          <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 1 0 0 12.324 6.162 6.162 0 0 0 0-12.324zM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.406-11.845a1.44 1.44 0 1 0 0 2.881 1.44 1.44 0 0 0 0-2.881z"/>
        </svg>
      );
    case "promo":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <line x1="12" x2="12" y1="19" y2="23"/>
          <line x1="8" x2="16" y1="23" y2="23"/>
        </svg>
      );
    case "deadline":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
          <circle cx="12" cy="12" r="10"/>
          <polyline points="12 6 12 12 16 14"/>
        </svg>
      );
    default:
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" x2="12" y1="8" y2="12"/>
          <line x1="12" x2="12.01" y1="16" y2="16"/>
        </svg>
      );
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────

function groupEventsByDate(events: CalendarEvent[]) {
  const groups: Record<string, CalendarEvent[]> = {};
  events.forEach((e) => {
    if (!groups[e.date]) groups[e.date] = [];
    groups[e.date].push(e);
  });
  return groups;
}

function formatDayInfo(dateStr: string) {
  const date = new Date(dateStr + "T00:00:00");
  return {
    day: date.getDate(),
    weekday: date.toLocaleDateString("en-US", { weekday: "short" }).toUpperCase(),
  };
}

// Muted top-right label like "Soft Purple" in the design
const TYPE_LABEL: Record<string, string> = {
  release:      "Soft Purple",
  spotify:      "Soft Green",
  youtube:      "Soft Red",
  social_media: "Soft Blue",
  promo:        "Soft Orange",
  deadline:     "Soft Rose",
  general:      "Soft Slate",
};

// ── Component ──────────────────────────────────────────────────────────────

export default function DailyFeed({ events, onEventClick }: DailyFeedProps) {
  const groupedEvents = groupEventsByDate(events);
  const sortedDates = Object.keys(groupedEvents).sort();

  if (sortedDates.length === 0) {
    return (
      <div className="flex flex-col">
        <h1 className="text-3xl font-bold text-slate-800 mb-8">Daily Dashboard</h1>
        <p className="text-slate-400 text-sm">No events yet. Upload a song to generate your release plan.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      <h1 className="text-3xl font-bold text-slate-800 mb-8">Daily Dashboard</h1>

      <div className="flex flex-col gap-6">
        {sortedDates.map((dateStr) => {
          const { day, weekday } = formatDayInfo(dateStr);
          const dayEvents = groupedEvents[dateStr];

          return (
            <div key={dateStr} className="flex gap-6">

              {/* Date column */}
              <div className="w-16 shrink-0 text-center">
                <div className="text-6xl font-light text-slate-800 leading-none">{day}</div>
                <div className="text-xs font-medium text-slate-400 mt-1">{weekday}</div>
              </div>

              {/* Events column */}
              <div className="flex-1 flex flex-col gap-3">
                {dayEvents.map((event) => {
                  const resolvedType = getIconType(event.type, event.title ?? "");
                  const colors = EVENT_COLORS[resolvedType] || EVENT_COLORS[event.type] || EVENT_COLORS.general;
                  const isCompleted = event.completed;
                  const softLabel = TYPE_LABEL[resolvedType] || TYPE_LABEL[event.type] || "Soft Slate";

                  return (
                    <button
                      key={event.id}
                      onClick={() => onEventClick(event)}
                      className={`group w-full text-left rounded-2xl px-4 py-3 pr-3
                        flex items-start justify-between gap-3
                        transition-all duration-200
                        hover:shadow-md hover:shadow-slate-200/80
                        hover:scale-[1.01] active:scale-[0.99]
                        ${isCompleted ? colors.completedBg : colors.bg}`}
                    >
                      <div className="flex items-start gap-3 min-w-0 flex-1">

                        {/* Icon */}
                        <span className={`mt-0.5 shrink-0 ${isCompleted ? "opacity-30 text-slate-400" : colors.icon}`}>
                          {isCompleted ? <CheckCircleIcon /> : <EventIcon type={event.type} title={event.title} />}
                        </span>

                        {/* Text block */}
                        <div className="min-w-0 flex-1">

                          {/* Row 1: task title — always the real name */}
                          <div className="flex items-center justify-between gap-2">
                            <p className={`text-sm font-semibold
                              ${isCompleted ? "text-slate-400 line-through" : "text-slate-800"}`}>
                              {event.title}
                            </p>
                            <span className="text-xs text-slate-400 shrink-0">{softLabel}</span>
                          </div>

                          {/* Row 2: type label as small metadata below title */}
                          <span className={`text-xs font-medium mt-0.5 block
                            ${isCompleted ? "text-slate-300" : colors.icon}`}>
                            {colors.label}
                          </span>

                          {/* Row 3: description / subtitle */}
                          {event.description && !isCompleted && (
                            <p className="text-slate-500 text-xs mt-1 leading-relaxed">
                              {event.description}
                            </p>
                          )}

                          {isCompleted && (
                            <p className="text-xs text-slate-400 mt-1 italic">Completed</p>
                          )}
                        </div>
                      </div>

                      {/* Chevron */}
                      <span className={`shrink-0 mt-1 transition-colors
                        ${isCompleted
                          ? "text-slate-300"
                          : "text-slate-400 group-hover:text-slate-600"}`}>
                        <ChevronRightIcon />
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
