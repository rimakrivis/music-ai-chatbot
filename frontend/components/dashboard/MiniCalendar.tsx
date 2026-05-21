"use client";

import { useEffect, useState } from "react";
import { CalendarEvent, DotDate } from "@/lib/types";

interface MiniCalendarProps {
  dotDates?: DotDate[];
  events?: CalendarEvent[];
  onEventClick?: (event: CalendarEvent) => void;
}

const DAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

function getDaysInMonth(year: number, month: number) {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfMonth(year: number, month: number) {
  return new Date(year, month, 1).getDay();
}

const ChevronLeftIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M15 18l-6-6 6-6"/>
  </svg>
);

const ChevronRightIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9 18l6-6-6-6"/>
  </svg>
);

const XIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
  </svg>
);

export default function MiniCalendar({ dotDates = [], events = [], onEventClick }: MiniCalendarProps) {
  const [currentDate, setCurrentDate] = useState(() => {
    if (events && events.length > 0) {
      return new Date(events[0].date + "T00:00:00");
    }
    return new Date();
  });
  useEffect(() => {
    if (events && events.length > 0) {
      setCurrentDate(new Date(events[0].date + "T00:00:00"));
    }
  }, [events.length]);
  const [selectedDay, setSelectedDay] = useState(new Date().getDate());
  // When a day has multiple events, show a picker popover
  const [pickerDay, setPickerDay] = useState<number | null>(null);
  const [pickerEvents, setPickerEvents] = useState<CalendarEvent[]>([]);

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const daysInMonth = getDaysInMonth(year, month);
  const firstDay = getFirstDayOfMonth(year, month);
  const monthName = currentDate.toLocaleString("default", { month: "long", year: "numeric" });

  const prevMonthDays = getDaysInMonth(year, month - 1);
  const prevDays = Array.from({ length: firstDay }, (_, i) => prevMonthDays - firstDay + i + 1);
  const currentDays = Array.from({ length: daysInMonth }, (_, i) => i + 1);
  const totalCells = Math.ceil((firstDay + daysInMonth) / 7) * 7;
  const nextDays = Array.from({ length: totalCells - firstDay - daysInMonth }, (_, i) => i + 1);

  // FIX: parse date as local, not UTC — append T00:00:00 to force local timezone
  const getEventsForDay = (day: number): CalendarEvent[] => {
    return events.filter((e) => {
      const d = new Date(e.date + "T00:00:00");
      return d.getFullYear() === year && d.getMonth() === month && d.getDate() === day;
    });
  };

  const getDotColor = (day: number) => {
    // First check live events (source of truth)
    const dayEvents = getEventsForDay(day);
    if (dayEvents.length > 0) {
      const colorMap: Record<string, string> = {
        release: "bg-purple-400",
        spotify: "bg-green-400",
        youtube: "bg-red-400",
        social_media: "bg-blue-400",
        promo: "bg-orange-400",
        deadline: "bg-rose-400",
        general: "bg-slate-400",
      };
      return colorMap[dayEvents[0].type] ?? "bg-slate-400";
    }
    // Fallback to passed-in dotDates
    const dotDate = dotDates.find((d) => d.date === day);
    if (!dotDate) return null;
    const colors: Record<string, string> = {
      blue: "bg-blue-400",
      green: "bg-green-400",
      yellow: "bg-yellow-400",
      purple: "bg-purple-400",
      red: "bg-red-400",
      orange: "bg-orange-400",
    };
    return colors[dotDate.color] || "bg-slate-400";
  };

  const handleDayClick = (day: number) => {
    setSelectedDay(day);
    setPickerDay(null);

    if (!onEventClick) return;

    const dayEvents = getEventsForDay(day);
    if (dayEvents.length === 0) return;
    if (dayEvents.length === 1) {
      onEventClick(dayEvents[0]);
    } else {
      // Multiple events — show picker
      setPickerEvents(dayEvents);
      setPickerDay(day);
    }
  };

  const prevMonth = () => {
    setCurrentDate(new Date(year, month - 1, 1));
    setSelectedDay(0);
    setPickerDay(null);
  };

  const nextMonth = () => {
    setCurrentDate(new Date(year, month + 1, 1));
    setSelectedDay(0);
    setPickerDay(null);
  };

  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100 relative">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-slate-800 font-semibold text-lg">{monthName}</h2>
        <div className="flex items-center gap-1">
          <button
            onClick={prevMonth}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors"
          >
            <ChevronLeftIcon />
          </button>
          <button
            onClick={nextMonth}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors"
          >
            <ChevronRightIcon />
          </button>
        </div>
      </div>

      {/* Day labels */}
      <div className="grid grid-cols-7 mb-2">
        {DAYS.map((day) => (
          <div key={day} className="text-center text-slate-400 text-xs font-medium py-1">
            {day}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7 gap-1">
        {prevDays.map((day) => (
          <div key={`prev-${day}`} className="flex flex-col items-center justify-center h-9 text-slate-300 text-sm">
            {day}
          </div>
        ))}

        {currentDays.map((day) => {
          const isSelected = day === selectedDay;
          const dotColor = getDotColor(day);
          const hasEvents = getEventsForDay(day).length > 0;

          return (
            <button
              key={day}
              onClick={() => handleDayClick(day)}
              className={`relative flex flex-col items-center justify-center h-9 text-sm rounded-full transition-all
                ${isSelected
                  ? "bg-red-500 text-white font-medium"
                  : hasEvents
                    ? "text-slate-800 font-medium hover:bg-slate-100"
                    : "text-slate-700 hover:bg-slate-100"
                }`}
            >
              {day}
              {dotColor && !isSelected && (
                <span className={`absolute bottom-0.5 w-1.5 h-1.5 rounded-full ${dotColor}`} />
              )}
            </button>
          );
        })}

        {nextDays.map((day) => (
          <div key={`next-${day}`} className="flex flex-col items-center justify-center h-9 text-slate-300 text-sm">
            {day}
          </div>
        ))}
      </div>

      {/* Multi-event picker popover */}
      {pickerDay !== null && (
        <div className="absolute left-4 right-4 bottom-full mb-2 bg-white rounded-xl shadow-xl border border-slate-200 z-50 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-100">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
              {currentDate.toLocaleString("default", { month: "short" })} {pickerDay}
            </span>
            <button
              onClick={() => setPickerDay(null)}
              className="text-slate-400 hover:text-slate-600 transition-colors"
            >
              <XIcon />
            </button>
          </div>
          <div className="flex flex-col divide-y divide-slate-50">
            {pickerEvents.map((ev) => (
              <button
                key={ev.id}
                onClick={() => {
                  setPickerDay(null);
                  onEventClick?.(ev);
                }}
                className="w-full text-left px-4 py-3 hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full shrink-0 ${
                    ev.type === "release" ? "bg-purple-400" :
                    ev.type === "spotify" ? "bg-green-400" :
                    ev.type === "youtube" ? "bg-red-400" :
                    ev.type === "social_media" ? "bg-blue-400" :
                    ev.type === "promo" ? "bg-orange-400" :
                    ev.type === "deadline" ? "bg-rose-400" : "bg-slate-400"
                  }`} />
                  <span className="text-sm text-slate-700 font-medium truncate">{ev.title}</span>
                </div>
                <span className="text-xs text-slate-400 ml-4 capitalize">{ev.type.replace("_", " ")}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
