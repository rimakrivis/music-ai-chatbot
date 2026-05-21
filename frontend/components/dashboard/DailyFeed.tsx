"use client";

import { CalendarEvent, EVENT_COLORS } from "@/lib/types";

interface DailyFeedProps {
  events: CalendarEvent[];
  onEventClick: (event: CalendarEvent) => void;
}

// Inline SVG Icons
const MusicIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
    <path d="M9 18V5l12-2v13"/>
    <circle cx="6" cy="18" r="3"/>
    <circle cx="18" cy="16" r="3"/>
  </svg>
);

const ChevronRightIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
    <path d="m9 18 6-6-6-6"/>
  </svg>
);

const CheckCircleIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
    <circle cx="12" cy="12" r="10"/>
    <polyline points="9 12 11 14 15 10"/>
  </svg>
);

function groupEventsByDate(events: CalendarEvent[]) {
  const groups: Record<string, CalendarEvent[]> = {};
  events.forEach((event) => {
    if (!groups[event.date]) groups[event.date] = [];
    groups[event.date].push(event);
  });
  return groups;
}

// FIX: parse as local date
function formatDayInfo(dateStr: string) {
  const date = new Date(dateStr + "T00:00:00");
  const day = date.getDate();
  const weekday = date.toLocaleDateString("en-US", { weekday: "short" }).toUpperCase();
  return { day, weekday };
}

function getEventIcon(type: string) {
  switch (type) {
    case "release": return <MusicIcon />;
    case "spotify":
      return (
        <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
          <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
        </svg>
      );
    case "social_media":
      return (
        <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
          <rect width="20" height="20" x="2" y="2" rx="5" fill="currentColor" opacity="0.2"/>
          <circle cx="12" cy="12" r="4" fill="currentColor"/>
          <circle cx="18" cy="6" r="1.5" fill="currentColor"/>
        </svg>
      );
    case "promo":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <line x1="12" x2="12" y1="19" y2="23"/>
          <line x1="8" x2="16" y1="23" y2="23"/>
        </svg>
      );
    case "deadline":
      return (
        <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
          <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.2"/>
          <path d="M12 6v6l4 2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" fill="none"/>
        </svg>
      );
    case "youtube":
      return (
        <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
          <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
        </svg>
      );
    default:
      return <div className="w-4 h-4 rounded-full bg-current opacity-60" />;
  }
}

export default function DailyFeed({ events, onEventClick }: DailyFeedProps) {
  const groupedEvents = groupEventsByDate(events);
  const sortedDates = Object.keys(groupedEvents).sort();

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
              <div className="w-24 shrink-0 text-center">
                <div className="text-7xl font-light text-slate-800 leading-none">{day}</div>
                <div className="text-sm font-medium text-slate-400 mt-1">{weekday}</div>
              </div>

              {/* Events column */}
              <div className="flex-1 flex flex-col gap-3">
                {dayEvents.map((event) => {
                  const colors = EVENT_COLORS[event.type] || EVENT_COLORS.general;
                  const isCompleted = event.completed;

                  return (
                    <button
                      key={event.id}
                      onClick={() => onEventClick(event)}
                      className={`group w-full text-left rounded-2xl p-4 pr-3 flex items-start justify-between gap-3 transition-all duration-200 hover:shadow-md hover:scale-[1.01] active:scale-[0.99]
                        ${isCompleted ? colors.completedBg : colors.bg}`}
                    >
                      <div className="flex items-start gap-3 min-w-0">
                        <span className={`mt-0.5 transition-opacity ${isCompleted ? "opacity-30" : colors.icon}`}>
                          {isCompleted ? <CheckCircleIcon /> : getEventIcon(event.type)}
                        </span>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className={`font-semibold text-sm transition-colors ${isCompleted ? "text-slate-400" : "text-slate-800"}`}>
                              {colors.label}
                            </span>
                          </div>
                          <p className={`text-sm mt-0.5 font-medium transition-colors ${isCompleted ? "text-slate-400 line-through" : "text-slate-700"}`}>
                            {event.title}
                          </p>
                          {event.description && !isCompleted && (
                            <p className="text-slate-500 text-xs mt-1 whitespace-pre-line">
                              {event.description}
                            </p>
                          )}
                          {isCompleted && (
                            <p className="text-xs text-slate-400 mt-1 italic">Completed</p>
                          )}
                        </div>
                      </div>
                      <span className={`transition-colors mt-1 shrink-0 ${isCompleted ? "text-slate-300" : "text-slate-400 group-hover:text-slate-600"}`}>
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
