"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import ChatMessage, { Message } from "@/components/ChatMessage";
import ChatInput from "@/components/ChatInput";
import TranscriptPanel from "@/components/TranscriptPanel";
import CalendarPanel from "@/components/CalendarPanel";
import TodoList from "@/components/TodoList";
import TaskConfirmationCard from "@/components/TaskConfirmationCard";
import WeeklyAgenda from "@/components/WeeklyAgenda";
import { sendMessage } from "@/lib/api";

const STARTER_PROMPTS = [
  "What is this song about?",
  "Extract the lyrics and format them cleanly.",
  "What is the marketing potential for this song?",
  "Tell me about the artist's Spotify stats.",
  "When should this song be released and on which platforms?",
];

interface ExtractedTasks {
  calendar_events: { title: string; date: string; type: string }[];
  todo_items: { title: string; due_date: string | null }[];
}

interface MessageWithTasks extends Message {
  tasks?: ExtractedTasks;
  tasksConfirmed?: boolean;
}

interface CalendarEvent {
  id: number;
  title: string;
  date: string;
  type: string;
}

function ChatPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const video_id = searchParams.get("video_id") || "";
  const video_title = searchParams.get("title") || "Unknown Video";
  const video_channel = searchParams.get("channel") || "";

  const [sessionId, setSessionId] = useState<string>("");

  useEffect(() => {
    let stored = localStorage.getItem("music_ai_session_id");
    if (!stored) {
      stored = crypto.randomUUID();
      localStorage.setItem("music_ai_session_id", stored);
    }
    setSessionId(stored);
  }, []);

  const [messages, setMessages] = useState<MessageWithTasks[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sidebarRefresh, setSidebarRefresh] = useState(0);
  const [chatCollapsed, setChatCollapsed] = useState(false);
  const [agendaEvents, setAgendaEvents] = useState<CalendarEvent[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    if (!video_id) router.push("/");
  }, [video_id, router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Fetch events for weekly agenda
  useEffect(() => {
    async function fetchAgendaEvents() {
      try {
        const res = await fetch(`${API}/calendar/events/${sessionId}`);
        const data = await res.json();
        setAgendaEvents(data.events || []);
      } catch (e) {
        console.error("Failed to fetch agenda events", e);
      }
    }
    fetchAgendaEvents();
  }, [sessionId, sidebarRefresh]);

  async function handleSend(text: string) {
    if (!video_id) return;
    const userMessage: MessageWithTasks = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);
    setError(null);

    try {
      const data = await sendMessage(video_id, text, sessionId, video_title, video_channel);
      const hasTasks =
        (data.calendar_events && data.calendar_events.length > 0) ||
        (data.todo_items && data.todo_items.length > 0);

      const aiMessage: MessageWithTasks = {
        role: "assistant",
        content: data.response,
        tools_used: data.tools_used,
        tasks: hasTasks
          ? { calendar_events: data.calendar_events || [], todo_items: data.todo_items || [] }
          : undefined,
        tasksConfirmed: false,
      };
      setMessages((prev) => [...prev, aiMessage]);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Something went wrong.";
      setError(msg);
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  }

  function handleTaskConfirm(msgIndex: number) {
    setMessages((prev) =>
      prev.map((m, i) => i === msgIndex ? { ...m, tasksConfirmed: true } : m)
    );
    setSidebarRefresh((n) => n + 1);
  }

  function handleTaskDismiss(msgIndex: number) {
    setMessages((prev) =>
      prev.map((m, i) => i === msgIndex ? { ...m, tasksConfirmed: true } : m)
    );
  }

  if (!sessionId) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-400 text-sm">
        Loading session…
      </div>
    );
  }

  if (!video_id) return null;

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-slate-50 via-white to-violet-50/30 font-sans">

      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-white/80 backdrop-blur-md border-b border-slate-200/60 z-10 shadow-sm shrink-0">
        <div className="flex items-center gap-4 min-w-0">
          <button
            onClick={() => router.push("/")}
            className="text-slate-400 hover:text-slate-700 transition-colors text-sm flex items-center gap-1.5 shrink-0"
          >
            ← Back
          </button>
          <div className="h-5 w-px bg-slate-200 shrink-0" />
          <div className="flex items-center gap-2 shrink-0">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-md shadow-violet-200">
              <span className="text-white text-xs">🎵</span>
            </div>
            <span className="text-slate-800 font-semibold text-sm hidden sm:block">Music AI</span>
          </div>
          <div className="h-5 w-px bg-slate-200 shrink-0" />
          <div className="min-w-0">
            <p className="text-slate-800 text-sm font-medium truncate">{video_title}</p>
            <p className="text-slate-400 text-xs truncate">{video_channel}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setChatCollapsed((v) => !v)}
            className="text-xs text-slate-500 hover:text-slate-800 border border-slate-200 hover:border-slate-300 px-3 py-1.5 rounded-lg transition-colors bg-white shadow-sm"
          >
            {chatCollapsed ? "💬 Show Chat" : "📅 Full Calendar"}
          </button>
          <button
            onClick={() => router.push("/")}
            className="text-xs text-slate-500 hover:text-violet-600 border border-slate-200 hover:border-violet-300 px-3 py-1.5 rounded-lg transition-colors bg-white shadow-sm"
          >
            + New video
          </button>
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">

        {/* Sidebar — always visible */}
        {!chatCollapsed && (
          <aside className="w-72 shrink-0 bg-white/70 backdrop-blur-sm border-r border-slate-200/60 flex flex-col overflow-y-auto shadow-sm">
            <div className="p-5 border-b border-slate-100">
              <CalendarPanel sessionId={sessionId} refreshTrigger={sidebarRefresh} />
            </div>
            <div className="p-5">
              <TodoList sessionId={sessionId} refreshTrigger={sidebarRefresh} />
            </div>
          </aside>
        )}

        {/* Chat — visible when not collapsed */}
        {!chatCollapsed && (
          <main className="flex-1 flex flex-col overflow-hidden">
            <TranscriptPanel video_id={video_id} />
            <div className="flex-1 overflow-y-auto px-6 py-6">
              {messages.length === 0 ? (
                <EmptyState onPromptSelect={handleSend} />
              ) : (
                <div className="max-w-2xl mx-auto flex flex-col gap-5">
                  {messages.map((msg, i) => (
                    <div key={i}>
                      <ChatMessage message={msg} />
                      {msg.role === "assistant" && msg.tasks && !msg.tasksConfirmed && (
                        <TaskConfirmationCard
                          sessionId={sessionId}
                          videoId={video_id}
                          calendarEvents={msg.tasks.calendar_events}
                          todoItems={msg.tasks.todo_items}
                          onConfirm={() => handleTaskConfirm(i)}
                          onDismiss={() => handleTaskDismiss(i)}
                        />
                      )}
                    </div>
                  ))}
                  {loading && (
                    <div className="flex items-start gap-2">
                      <div className="bg-white border border-slate-200 shadow-sm rounded-2xl rounded-bl-sm px-4 py-3 text-sm text-slate-400 flex items-center gap-2">
                        <span className="inline-block w-3 h-3 border-2 border-slate-300 border-t-violet-500 rounded-full animate-spin" />
                        Thinking…
                      </div>
                    </div>
                  )}
                  {error && (
                    <p className="text-rose-400 text-xs text-center">⚠ {error} — try again.</p>
                  )}
                  <div ref={bottomRef} />
                </div>
              )}
            </div>
            <ChatInput onSend={handleSend} disabled={loading} />
          </main>
        )}

        {/* Weekly agenda — full screen when chat collapsed */}
        {chatCollapsed && (
          <div className="flex-1 overflow-hidden">
            <WeeklyAgenda
              events={agendaEvents}
              sessionId={sessionId}
              videoId={video_id}
              videoTitle={video_title}
              videoChannel={video_channel}
              onEventSaved={() => setSidebarRefresh((n) => n + 1)}
            />
          </div>
        )}
      </div>
    </div>
  );
}

function EmptyState({ onPromptSelect }: { onPromptSelect: (p: string) => void }) {
  return (
    <div className="max-w-2xl mx-auto flex flex-col items-center gap-8 pt-8">
      <div className="text-center flex flex-col gap-2">
        <span className="text-4xl">🎤</span>
        <h2 className="text-slate-800 font-semibold">Ask anything about this song</h2>
        <p className="text-slate-400 text-sm">The AI will pick the right tools and show you which ones it used.</p>
      </div>
      <div className="w-full flex flex-col gap-2">
        <p className="text-slate-400 text-xs text-center mb-1">Try one of these</p>
        {STARTER_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            onClick={() => onPromptSelect(prompt)}
            className="w-full text-left text-sm text-slate-600 hover:text-slate-900 bg-white hover:bg-violet-50 border border-slate-200 hover:border-violet-200 rounded-xl px-4 py-3 transition-all shadow-sm hover:shadow-md"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center text-slate-400 text-sm">
        Loading…
      </div>
    }>
      <ChatPageInner />
    </Suspense>
  );
}