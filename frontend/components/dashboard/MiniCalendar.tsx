"use client";

import { useState } from "react";
import { DotDate } from "@/lib/types";

interface MiniCalendarProps {
  dotDates?: DotDate[];
}

const DAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

function getDaysInMonth(year: number, month: number) {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfMonth(year: number, month: number) {
  return new Date(year, month, 1).getDay();
}

// Inline SVG icons
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

export default function MiniCalendar({ dotDates = [] }: MiniCalendarProps) {
  const [currentDate, setCurrentDate] = useState(new Date(2025, 4, 3)); // May 2025, day 3 selected
  const [selectedDay, setSelectedDay] = useState(3);

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const daysInMonth = getDaysInMonth(year, month);
  const firstDay = getFirstDayOfMonth(year, month);
  const monthName = currentDate.toLocaleString("default", { month: "long", year: "numeric" });

  // Previous month days to show
  const prevMonthDays = getDaysInMonth(year, month - 1);
  const prevDays = Array.from({ length: firstDay }, (_, i) => prevMonthDays - firstDay + i + 1);

  // Current month days
  const currentDays = Array.from({ length: daysInMonth }, (_, i) => i + 1);

  // Next month days to fill the grid
  const totalCells = Math.ceil((firstDay + daysInMonth) / 7) * 7;
  const nextDays = Array.from({ length: totalCells - firstDay - daysInMonth }, (_, i) => i + 1);

  const getDotColor = (day: number) => {
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

  const prevMonth = () => {
    setCurrentDate(new Date(year, month - 1, 1));
    setSelectedDay(0);
  };

  const nextMonth = () => {
    setCurrentDate(new Date(year, month + 1, 1));
    setSelectedDay(0);
  };

  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100">
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
        {/* Previous month days */}
        {prevDays.map((day) => (
          <div
            key={`prev-${day}`}
            className="flex flex-col items-center justify-center h-9 text-slate-300 text-sm"
          >
            {day}
          </div>
        ))}

        {/* Current month days */}
        {currentDays.map((day) => {
          const isSelected = day === selectedDay;
          const dotColor = getDotColor(day);

          return (
            <button
              key={day}
              onClick={() => setSelectedDay(day)}
              className={`relative flex flex-col items-center justify-center h-9 text-sm rounded-full transition-all
                ${isSelected
                  ? "bg-red-500 text-white font-medium"
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

        {/* Next month days */}
        {nextDays.map((day) => (
          <div
            key={`next-${day}`}
            className="flex flex-col items-center justify-center h-9 text-slate-300 text-sm"
          >
            {day}
          </div>
        ))}
      </div>
    </div>
  );
}
