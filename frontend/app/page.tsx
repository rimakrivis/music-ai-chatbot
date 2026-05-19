"use client";

import { useState } from "react";
import MiniCalendar from "@/components/dashboard/MiniCalendar";
import TodoListPanel from "@/components/dashboard/TodoListPanel";
import ProgressBar from "@/components/dashboard/ProgressBar";
import DailyFeed from "@/components/dashboard/DailyFeed";
import UploadPanel from "@/components/dashboard/UploadPanel";
import AIChatbot from "@/components/dashboard/AIChatbot";
import EventDrawer from "@/components/dashboard/EventDrawer";
import { CalendarEvent, TodoItem, ChatMessage } from "@/lib/types";

// Sample data
const SAMPLE_EVENTS: CalendarEvent[] = [
  {
    id: 1,
    title: "ALBUM RELEASE: 'Dreamscape' [23 May]",
    description: "Release details: January 23, 2025\nRelease Time: 10:00 - 5:00pm",
    date: "2025-05-22",
    type: "release",
  },
  {
    id: 2,
    title: "Playlisting Pitch: 'Dreamscape' [23 May 10:00]",
    date: "2025-05-22",
    type: "spotify",
  },
  {
    id: 3,
    title: "Teaser Posts: Instagram & TikTok [22 May]",
    date: "2025-05-23",
    type: "social_media",
  },
  {
    id: 4,
    title: "Press Interview: 'New Artist Spotlight' [23 May 14:00]",
    date: "2025-05-23",
    type: "promo",
  },
  {
    id: 5,
    title: "Artwork Finalization [22 May 18:00]",
    date: "2025-05-24",
    type: "deadline",
  },
  {
    id: 6,
    title: "Team Sync Meeting [22 May 11:00]",
    date: "2025-05-24",
    type: "general",
  },
];

const SAMPLE_TODOS: TodoItem[] = [
  { id: 1, title: "Upload YouTube video", completed: false },
  { id: 2, title: "Check Spotify stats", completed: false },
  { id: 3, title: "Schedule Instagram posts", completed: false },
  { id: 4, title: "Finalize artwork", completed: false },
];

const CALENDAR_DOT_DATES = [
  { date: 12, color: "blue" },
  { date: 16, color: "yellow" },
  { date: 19, color: "green" },
  { date: 22, color: "purple" },
];

export default function DashboardPage() {
  const [events] = useState<CalendarEvent[]>(SAMPLE_EVENTS);
  const [todos, setTodos] = useState<TodoItem[]>(SAMPLE_TODOS);
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: "Hi, that's one context...since micrommency music release, the release with avsphnment to discuss and form a mesting some that iwrantive and AI's product.",
    },
  ]);

  const handleToggleTodo = (id: number) => {
    setTodos((prev) =>
      prev.map((t) => (t.id === id ? { ...t, completed: !t.completed } : t))
    );
  };

  const completedCount = todos.filter((t) => t.completed).length;
  const progressPercent = todos.length > 0 ? (completedCount / todos.length) * 100 : 0;

  const handleEventClick = (event: CalendarEvent) => {
    setSelectedEvent(event);
  };

  const handleCloseDrawer = () => {
    setSelectedEvent(null);
  };

  const handleSendMessage = (message: string) => {
    setChatMessages((prev) => [...prev, { role: "user", content: message }]);
    // Simulate AI response
    setTimeout(() => {
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "I can help you with your music release planning. What specific aspect would you like to discuss?",
        },
      ]);
    }, 1000);
  };

  return (
    <div className="min-h-screen bg-[#f7f5f2] p-6">
      <div className="max-w-[1600px] mx-auto grid grid-cols-1 lg:grid-cols-[320px_1fr_340px] gap-6 h-[calc(100vh-48px)]">
        {/* Left Sidebar */}
        <aside className="flex flex-col gap-5 lg:sticky lg:top-6 lg:h-fit">
          <MiniCalendar dotDates={CALENDAR_DOT_DATES} />
          <TodoListPanel todos={todos} onToggle={handleToggleTodo} />
          <ProgressBar progress={progressPercent} />
        </aside>

        {/* Center Feed */}
        <main className="overflow-y-auto pr-2 -mr-2">
          <DailyFeed events={events} onEventClick={handleEventClick} />
        </main>

        {/* Right Sidebar */}
        <aside className="flex flex-col gap-5 lg:sticky lg:top-6 lg:h-fit">
          <UploadPanel />
          <AIChatbot messages={chatMessages} onSendMessage={handleSendMessage} />
        </aside>
      </div>

      {/* Event Drawer */}
      <EventDrawer
        event={selectedEvent}
        onClose={handleCloseDrawer}
      />
    </div>
  );
}
