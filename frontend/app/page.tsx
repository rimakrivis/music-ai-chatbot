"use client";

import { useState, useCallback, useEffect } from "react";
import MiniCalendar from "@/components/dashboard/MiniCalendar";
import TodoListPanel from "@/components/dashboard/TodoListPanel";
import ProgressBar from "@/components/dashboard/ProgressBar";
import DailyFeed from "@/components/dashboard/DailyFeed";
import UploadPanel from "@/components/dashboard/UploadPanel";
import AIChatbot from "@/components/dashboard/AIChatbot";
import EventDrawer from "@/components/dashboard/EventDrawer";
import TaskConfirmationCard from "@/components/TaskConfirmationCard";
import { CalendarEvent, TodoItem, ChatMessage } from "@/lib/types";
import { sendMessage, AnalyzeResponse } from "@/lib/api";

export default function DashboardPage() {
  const [sessionId] = useState<string>(() => {
    if (typeof window === "undefined") return "";
    let stored = localStorage.getItem("music_ai_session_id");
    if (!stored) {
      stored = crypto.randomUUID();
      localStorage.setItem("music_ai_session_id", stored);
    }
    return stored;
  });

  const [videoInfo, setVideoInfo] = useState<AnalyzeResponse | null>(() => {
    if (typeof window === "undefined") return null;
    const stored = localStorage.getItem("music_ai_last_video");
    return stored ? JSON.parse(stored) : null;
  });

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

  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const loadFromSupabase = useCallback(async () => {
    try {
      const [eventsRes, todosRes] = await Promise.all([
        fetch(`${API}/calendar/events/${sessionId}`),
        fetch(`${API}/todos/${sessionId}`),
      ]);
      const eventsData = await eventsRes.json();
      const todosData = await todosRes.json();

      if (eventsData.events?.length > 0) {
        setEvents(eventsData.events.map((e: any) => ({
          id: e.id,
          title: e.title,
          date: e.date,
          type: e.type,
        })));
        console.log("[page] Loaded", eventsData.events.length, "events from Supabase");
      }
      if (todosData.items?.length > 0) {
        setTodos(todosData.items.map((t: any) => ({
          id: t.id,
          title: t.title,
          completed: t.status === "done",
        })));
        console.log("[page] Loaded", todosData.items.length, "todos from Supabase");
      }
    } catch (e) {
      console.error("[page] Failed to load from Supabase", e);
    }
  }, [sessionId, API]);

  useEffect(() => {
    if (sessionId) loadFromSupabase();
  }, [sessionId, loadFromSupabase]);

  const handleVideoLoaded = useCallback((video: AnalyzeResponse) => {
    console.log("[page] Video loaded:", video.title);
    localStorage.setItem("music_ai_last_video", JSON.stringify(video));
    setVideoInfo(video);
    setChatMessages([
      {
        role: "assistant",
        content: `✅ Loaded **"${video.title}"** by ${video.channel}. I've indexed the transcript (${video.word_count} words). Ask me anything — lyrics, marketing plan, release timing, or Spotify stats!`,
      },
    ]);
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

  function handleTaskConfirm(msgIndex: number) {
    setChatMessages((prev) =>
      prev.map((m, i) => i === msgIndex ? { ...m, tasksConfirmed: true } : m)
    );
    loadFromSupabase();
  }

  function handleTaskDismiss(msgIndex: number) {
    setChatMessages((prev) =>
      prev.map((m, i) => i === msgIndex ? { ...m, tasksConfirmed: true } : m)
    );
  }

  const handleSendMessage = async (message: string) => {
    if (!videoInfo) {
      setChatMessages((prev) => [
        ...prev,
        { role: "user", content: message },
        { role: "assistant", content: "Please load a YouTube song first using the panel above." },
      ]);
      return;
    }

    setChatMessages((prev) => [...prev, { role: "user", content: message }]);
    setIsChatLoading(true);
    console.log("[page] Sending message to agent:", message);

    try {
      const data = await sendMessage(
        videoInfo.video_id,
        message,
        sessionId,
        videoInfo.title,
        videoInfo.channel
      );

      console.log("[page] Agent response received:", {
        response_length: data.response.length,
        tools_used: data.tools_used,
        calendar_events: data.calendar_events?.length ?? 0,
        todo_items: data.todo_items?.length ?? 0,
      });

      const hasTasks =
        (data.calendar_events && data.calendar_events.length > 0) ||
        (data.todo_items && data.todo_items.length > 0);

      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.response,
          tasks: hasTasks
            ? { calendar_events: data.calendar_events || [], todo_items: data.todo_items || [] }
            : undefined,
          tasksConfirmed: false,
        },
      ]);

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

  const now = new Date();
  const calendarDotDates = events
    .filter((e) => {
      const d = new Date(e.date + "T00:00:00");
      return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth();
    })
    .map((e) => {
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
          <UploadPanel onVideoLoaded={handleVideoLoaded} sessionId={sessionId} />
          <AIChatbot
            messages={chatMessages}
            onSendMessage={handleSendMessage}
            isLoading={isChatLoading}
            renderTaskCard={(msg, i) => {
              if (!msg.tasks || msg.tasksConfirmed) return null;
              return (
                <TaskConfirmationCard
                  sessionId={sessionId}
                  videoId={videoInfo?.video_id ?? ""}
                  calendarEvents={msg.tasks.calendar_events}
                  todoItems={msg.tasks.todo_items}
                  onConfirm={() => handleTaskConfirm(i)}
                  onDismiss={() => handleTaskDismiss(i)}
                />
              );
            }}
          />
        </aside>
      </div>

      {/* Event Drawer */}
      <EventDrawer
        event={selectedEvent}
        onClose={handleCloseDrawer}
      />
  {/* Reset session button — subtle, bottom left */}
      <button
        onClick={async () => {
          await fetch(`${API}/session/${sessionId}`, { method: "DELETE" });
          setEvents([]);
          setTodos([]);
          setChatMessages([{
            role: "assistant",
            content: "Session cleared. Paste a YouTube URL to start fresh.",
          }]);
        }}
        className="fixed bottom-4 left-4 text-xs text-slate-300 hover:text-rose-400 transition-colors"
        title="Clear session"
      >
        ↺ reset
      </button>
    </div>
  );
}  