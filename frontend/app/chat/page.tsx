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
  const [sessionId, setSessionId] = useState<string>("");

  useEffect(() => {
    let stored = localStorage.getItem("music_ai_session_id");
    if (!stored) {
      stored = crypto.randomUUID();
      localStorage.setItem("music_ai_session_id", stored);
    }
    setSessionId(stored);
  }, []);
  const [videoInfo, setVideoInfo] = useState<AnalyzeResponse | null>(() => {
    if (typeof window === "undefined") return null;
    const stored = localStorage.getItem("music_ai_last_video");
    return stored ? JSON.parse(stored) : null;
  });

  const [audioFeatures, setAudioFeatures] = useState<Record<string, number> | null>(null);

  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [todos, setTodos] = useState<TodoItem[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Paste a YouTube URL above to load a song, then ask me anything about it — lyrics, marketing plan, release strategy, Spotify stats, and more.",
    },
  ]);
  const [isChatLoading, setIsChatLoading] = useState(false);

  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // ── Load from Supabase ───────────────────────────────────────────────────

  const loadFromSupabase = useCallback(async () => {
    try {
      const [eventsRes, todosRes] = await Promise.all([
        fetch(`${API}/calendar/events/${sessionId}`),
        fetch(`${API}/todos/${sessionId}`),
      ]);
      const eventsData = await eventsRes.json();
      const todosData = await todosRes.json();

      setEvents(
        eventsData.events?.length > 0
          ? eventsData.events.map((e: any) => ({
              id: e.id,
              title: e.title,
              date: e.date,
              type: e.type,
              completed: e.status === "done",
              savedContent: e.saved_content ?? "",
              linkedTodoId: e.linked_todo_id ?? undefined,
            }))
          : []
      );
      setTodos(
        todosData.items?.length > 0
          ? todosData.items.map((t: any) => ({
              id: t.id,
              title: t.title,
              completed: t.status === "done",
              linkedEventId: t.linked_event_id ?? undefined,
            }))
          : []
      );
    } catch (e) {
      console.error("[page] Failed to load from Supabase", e);
    }
  }, [sessionId, API]);

  useEffect(() => {
    if (sessionId) loadFromSupabase();
  }, [sessionId, loadFromSupabase]);

  // ── Load audio features from localStorage when video changes ────────────

  useEffect(() => {
    if (!videoInfo?.video_id) return;
    const stored = localStorage.getItem(`audio_features_${videoInfo.video_id}`);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        setAudioFeatures(parsed);
        console.log("🎵 Loaded audio features:", parsed);
      } catch (e) {
        console.error("[page] Failed to parse audio features", e);
        setAudioFeatures(null);
      }
    } else {
      setAudioFeatures(null);
    }
  }, [videoInfo?.video_id]);

  // ── Video loaded ─────────────────────────────────────────────────────────

  const handleVideoLoaded = useCallback((video: AnalyzeResponse) => {
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

  // ── Todo toggle — also syncs linked event ────────────────────────────────

  const handleToggleTodo = useCallback(
    async (id: number) => {
      const todo = todos.find((t) => t.id === id);
      if (!todo) return;
      const newCompleted = !todo.completed;

      // Optimistic update
      setTodos((prev) =>
        prev.map((t) => (t.id === id ? { ...t, completed: newCompleted } : t))
      );

      // If the todo has a linked event, mirror completion there too
      if (todo.linkedEventId) {
        setEvents((prev) =>
          prev.map((e) =>
            e.id === todo.linkedEventId ? { ...e, completed: newCompleted } : e
          )
        );
      }

      // Persist to Supabase
      try {
        await fetch(`${API}/todos/${id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: newCompleted ? "done" : "pending" }),
        });
      } catch (err) {
        console.error("[page] Failed to update todo status", err);
      }
    },
    [todos, API]
  );

  // ── Todo title click — open drawer for linked event or synthetic event ───

  const handleTodoTitleClick = useCallback(
    (todo: TodoItem) => {
      if (todo.linkedEventId) {
        const linked = events.find((e) => e.id === todo.linkedEventId);
        if (linked) {
          setSelectedEvent(linked);
          return;
        }
      }
      // No linked event — open drawer with a synthetic event so the user can
      // still chat about this task
      setSelectedEvent({
        id: -(todo.id), // negative ID signals synthetic
        title: todo.title,
        date: "",
        type: "general",
        savedContent: "",
      });
    },
    [events]
  );

  // ── Progress ─────────────────────────────────────────────────────────────

  const completedCount = todos.filter((t) => t.completed).length;
  const progressPercent = todos.length > 0 ? (completedCount / todos.length) * 100 : 0;

  // ── Event drawer ─────────────────────────────────────────────────────────

  const handleEventClick = useCallback((event: CalendarEvent) => {
    setSelectedEvent(event);
  }, []);

  const handleCloseDrawer = useCallback(() => {
    setSelectedEvent(null);
  }, []);

  // When AI content is saved to the doc panel, persist it in events state
  const handleSaveContent = useCallback((eventId: number, content: string) => {
    if (eventId < 0) return; // synthetic event, nothing to persist
    setEvents((prev) =>
      prev.map((e) => (e.id === eventId ? { ...e, savedContent: content } : e))
    );
    // Keep selectedEvent in sync so the drawer doesn't lose it on re-render
    setSelectedEvent((prev) =>
      prev && prev.id === eventId ? { ...prev, savedContent: content } : prev
    );
    // Persist to Supabase
    fetch(`${API}/calendar/events/${eventId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ saved_content: content }),
    }).catch((err) => console.error("[page] Failed to save doc content", err));
  }, [API]);

  // ── Task confirmation ────────────────────────────────────────────────────

  function handleTaskConfirm(msgIndex: number) {
    setChatMessages((prev) =>
      prev.map((m, i) => (i === msgIndex ? { ...m, tasksConfirmed: true } : m))
    );
    loadFromSupabase();
  }

  function handleTaskDismiss(msgIndex: number) {
    setChatMessages((prev) =>
      prev.map((m, i) => (i === msgIndex ? { ...m, tasksConfirmed: true } : m))
    );
  }

  // ── Main chat ────────────────────────────────────────────────────────────

  const handleSendMessage = async (message: string) => {
    if (!videoInfo) {
      setChatMessages((prev) => [
        ...prev,
        { role: "user", content: message },
        {
          role: "assistant",
          content: "Please load a YouTube song first using the panel above.",
        },
      ]);
      return;
    }

    setChatMessages((prev) => [...prev, { role: "user", content: message }]);
    setIsChatLoading(true);

    try {
      const data = await sendMessage(
        videoInfo.video_id,
        message,
        sessionId,
        videoInfo.title,
        videoInfo.channel,
        audioFeatures ?? undefined,  // ← librosa data passed to agent
      );

      const hasTasks =
        (data.calendar_events && data.calendar_events.length > 0) ||
        (data.todo_items && data.todo_items.length > 0);

      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.response,
          tasks: hasTasks
            ? {
                calendar_events: data.calendar_events || [],
                todo_items: data.todo_items || [],
              }
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

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-[#f7f5f2] p-6">
      <div className="max-w-[1600px] mx-auto grid grid-cols-1 lg:grid-cols-[320px_1fr_340px] gap-6 h-[calc(100vh-48px)]">

        {/* Left Sidebar */}
        <aside className="flex flex-col gap-5 lg:sticky lg:top-6 lg:h-fit">
          <MiniCalendar
            events={events}
            onEventClick={handleEventClick}
          />
          <TodoListPanel
            todos={todos}
            onToggle={handleToggleTodo}
            onTitleClick={handleTodoTitleClick}
          />
          <ProgressBar progress={progressPercent} />
        </aside>

        {/* Center Feed */}
        <main className="overflow-y-auto pr-2 -mr-2">
          {events.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-slate-400 gap-3">
              <span className="text-5xl">🎵</span>
              <p className="text-sm">
                Load a song and ask for a marketing plan to see your schedule here.
              </p>
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
        sessionId={sessionId}
        videoId={videoInfo?.video_id}
        videoTitle={videoInfo?.title}
        videoChannel={videoInfo?.channel}
        onSaveContent={handleSaveContent}
      />

      {/* Reset session button */}
      <button
        onClick={async () => {
          await fetch(`${API}/session/${sessionId}`, { method: "DELETE" });
          setEvents([]);
          setTodos([]);
          setChatMessages([
            {
              role: "assistant",
              content: "Session cleared. Paste a YouTube URL to start fresh.",
            },
          ]);
        }}
        className="fixed bottom-4 left-4 text-xs text-slate-300 hover:text-rose-400 transition-colors"
        title="Clear session"
      >
        ↺ reset
      </button>
    </div>
  );
}
