"use client";

import { useState, useCallback } from "react";
import { v4 as uuidv4 } from "uuid";
import MiniCalendar from "@/components/dashboard/MiniCalendar";
import TodoListPanel from "@/components/dashboard/TodoListPanel";
import ProgressBar from "@/components/dashboard/ProgressBar";
import DailyFeed from "@/components/dashboard/DailyFeed";
import UploadPanel from "@/components/dashboard/UploadPanel";
import AIChatbot from "@/components/dashboard/AIChatbot";
import EventDrawer from "@/components/dashboard/EventDrawer";
import { CalendarEvent, TodoItem, ChatMessage } from "@/lib/types";
import { sendMessage, AnalyzeResponse } from "@/lib/api";

// Stable session ID for this browser session
const SESSION_ID = typeof window !== "undefined"
  ? (localStorage.getItem("session_id") ?? (() => {
      const id = uuidv4();
      localStorage.setItem("session_id", id);
      return id;
    })())
  : uuidv4();

export default function DashboardPage() {
  const [videoInfo, setVideoInfo] = useState<AnalyzeResponse | null>(null);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [todos, setTodos] = useState<TodoItem[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: "Paste a YouTube URL above to load a song, then ask me anything about it — lyrics, marketing plan, release strategy, Spotify stats, and more.",
    },
  ]);
  const [isChatLoading, setIsChatLoading] = useState(false);

  // Called when UploadPanel successfully analyzes a video
  const handleVideoLoaded = useCallback((video: AnalyzeResponse) => {
    console.log("[page] Video loaded:", video.title);
    setVideoInfo(video);
    // Reset chat with a welcome message for this song
    setChatMessages([
      {
        role: "assistant",
        content: `✅ Loaded **"${video.title}"** by ${video.channel}. I've indexed the transcript (${video.word_count} words). Ask me anything — lyrics, marketing plan, release timing, or Spotify stats!`,
      },
    ]);
    // Clear previous events/todos from last song
    setEvents([]);
    setTodos([]);
  }, []);

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

  const handleSendMessage = async (message: string) => {
    if (!videoInfo) {
      setChatMessages((prev) => [
        ...prev,
        { role: "user", content: message },
        { role: "assistant", content: "Please load a YouTube song first using the panel above." },
      ]);
      return;
    }

    // Add user message immediately
    setChatMessages((prev) => [...prev, { role: "user", content: message }]);
    setIsChatLoading(true);
    console.log("[page] Sending message to agent:", message);

    try {
      const data = await sendMessage(
        videoInfo.video_id,
        message,
        SESSION_ID,
        videoInfo.title,
        videoInfo.channel
      );

      console.log("[page] Agent response received:", {
        response_length: data.response.length,
        tools_used: data.tools_used,
        calendar_events: data.calendar_events?.length ?? 0,
        todo_items: data.todo_items?.length ?? 0,
      });

      // Add assistant response
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.response },
      ]);

      // Append any new calendar events returned by the agent
      if (data.calendar_events && data.calendar_events.length > 0) {
        const newEvents: CalendarEvent[] = data.calendar_events.map((e, i) => ({
          id: Date.now() + i,
          title: e.title,
          date: e.date,
          type: (e.type as CalendarEvent["type"]) || "general",
        }));
        console.log("[page] Adding", newEvents.length, "calendar events");
        setEvents((prev) => [...prev, ...newEvents]);
      }

      // Append any new todos returned by the agent
      if (data.todo_items && data.todo_items.length > 0) {
        const newTodos: TodoItem[] = data.todo_items.map((t, i) => ({
          id: Date.now() + i + 1000,
          title: t.title,
          completed: false,
        }));
        console.log("[page] Adding", newTodos.length, "todos");
        setTodos((prev) => [...prev, ...newTodos]);
      }

    } catch (err) {
      console.error("[page] Chat error:", err);
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, something went wrong connecting to the AI. Please try again.",
        },
      ]);
    } finally {
      setIsChatLoading(false);
    }
  };

  // Build dot dates for MiniCalendar from real events
  const calendarDotDates = events.map((e) => {
    const day = parseInt(e.date.split("-")[2], 10);
    const colorMap: Record<string, string> = {
      release: "purple",
      spotify: "green",
      youtube: "red",
      social_media: "blue",
      promo: "orange",
      deadline: "rose",
      general: "slate",
    };
    return { date: day, color: colorMap[e.type] ?? "slate" };
  });

  return (
    <div className="min-h-screen bg-[#f7f5f2] p-6">
      <div className="max-w-[1600px] mx-auto grid grid-cols-1 lg:grid-cols-[320px_1fr_340px] gap-6 h-[calc(100vh-48px)]">

        {/* Left Sidebar */}
        <aside className="flex flex-col gap-5 lg:sticky lg:top-6 lg:h-fit">
          <MiniCalendar dotDates={calendarDotDates} />
          <TodoListPanel todos={todos} onToggle={handleToggleTodo} />
          <ProgressBar progress={progressPercent} />
        </aside>

        {/* Center Feed */}
        <main className="overflow-y-auto pr-2 -mr-2">
          {events.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-slate-400 gap-3">
              <span className="text-5xl">🎵</span>
              <p className="text-sm">Load a song and ask for a marketing plan to see your schedule here.</p>
            </div>
          ) : (
            <DailyFeed events={events} onEventClick={handleEventClick} />
          )}
        </main>

        {/* Right Sidebar */}
        <aside className="flex flex-col gap-5 lg:sticky lg:top-6 lg:h-fit">
          <UploadPanel onVideoLoaded={handleVideoLoaded} />
          <AIChatbot
            messages={chatMessages}
            onSendMessage={handleSendMessage}
            isLoading={isChatLoading}
          />
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
