"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import DailyFeed from "@/components/dashboard/DailyFeed";
import UploadPanel from "@/components/dashboard/UploadPanel";
import { ProjectType } from "@/components/dashboard/ProjectTypeSelector";
import ConcertDetailsCapture from "@/components/dashboard/ConcertDetailsCapture";
import AIChatbot from "@/components/dashboard/AIChatbot";
import EventDrawer from "@/components/dashboard/EventDrawer";
import TaskConfirmationCard from "@/components/TaskConfirmationCard";
import Sidebar from "@/components/dashboard/Sidebar";
import TodoDrawer from "@/components/dashboard/TodoDrawer";
import AddToCalendarModal from "@/components/dashboard/AddToCalendarModal";
import BandProfileForm from "@/components/dashboard/BandProfileForm";
import { CalendarEvent, TodoItem, ChatMessage } from "@/lib/types";
import { sendMessage, createProject, getLatestProject, AnalyzeResponse, deleteCalendarEvent, rescheduleCalendarEvent } from "@/lib/api";

export default function DashboardPage() {
  const [sessionId, setSessionId] = useState<string>("");
  const [bandId, setBandId] = useState<string>("");

  useEffect(() => {
    let stored = localStorage.getItem("music_ai_session_id");
    if (!stored) {
      stored = crypto.randomUUID();
      localStorage.setItem("music_ai_session_id", stored);
    }
    setSessionId(stored);
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(`${API}/band`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ owner_id: sessionId }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`Band fetch failed: ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setBandId(data.band_id);
        console.log("[page] band_id ready:", data.band_id);
      })
      .catch((err) => console.error("[page] Failed to get/create band", err));
  }, [sessionId]);

  const [videoInfo, setVideoInfo] = useState<AnalyzeResponse | null>(() => {
    if (typeof window === "undefined") return null;
    const stored = localStorage.getItem("music_ai_last_video");
    return stored ? JSON.parse(stored) : null;
  });

  const [audioFeatures, setAudioFeatures] = useState<Record<string, unknown> | null>(null);
  const [projectType, setProjectType] = useState<ProjectType | null>(null);
  const [currentProjectId, setCurrentProjectId] = useState<number | null>(null);

  // Set right before an auto-detected project (see handleSendMessage) updates
  // projectType/currentProjectId in the background, so the project-switch
  // effect below skips its "reset chat + fetch project" side effects — those
  // are only meant for the user manually clicking a project type button.
  const skipNextProjectEffectRef = useRef(false);

  // Set true when the band profile is saved; the next chat message sends
  // it so the backend rebuilds the system prompt with the fresh profile
  // instead of the one from earlier in the conversation. Cleared after
  // that one message — a normal one-shot flag, not a standing setting.
  const profileJustUpdatedRef = useRef(false);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [todos, setTodos] = useState<TodoItem[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: "Paste a YouTube URL above to load a song, then ask me anything about it — lyrics, marketing plan, release strategy, Spotify stats, and more. Or skip the upload to plan a concert or campaign instead.",
    },
  ]);
  const [isChatLoading, setIsChatLoading] = useState(false);

  // New sidebar-driven overlays — each independent, none touch the
  // calendar-event-click -> EventDrawer flow, which keeps using selectedEvent.
  const [todoDrawerOpen, setTodoDrawerOpen] = useState(false);
  const [bandProfileOpen, setBandProfileOpen] = useState(false);
  const [addEventModalOpen, setAddEventModalOpen] = useState(false);

  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const loadFromSupabase = useCallback(async () => {
    if (!bandId) return;
    try {
      const [eventsRes, todosRes] = await Promise.all([
        fetch(`${API}/calendar/events/${bandId}`),
        fetch(`${API}/todos/${bandId}`),
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
              projectId: e.project_id ?? null,
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
              projectId: t.project_id ?? null,
            }))
          : []
      );
    } catch (e) {
      console.error("[page] Failed to load from Supabase", e);
    }
  }, [bandId, API]);

  useEffect(() => {
    if (bandId) loadFromSupabase();
  }, [bandId, loadFromSupabase]);

  useEffect(() => {
    if (!videoInfo?.video_id) return;
    if (videoInfo.audio_features && Object.keys(videoInfo.audio_features).length > 0) {
      setAudioFeatures(videoInfo.audio_features as Record<string, unknown>);
      return;
    }
    const stored = localStorage.getItem(`audio_features_${videoInfo.video_id}`);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        setAudioFeatures(parsed);
      } catch (e) {
        setAudioFeatures(null);
      }
    } else {
      setAudioFeatures(null);
    }
  }, [videoInfo?.video_id]);

  const handleVideoLoaded = useCallback((video: AnalyzeResponse) => {
    localStorage.setItem("music_ai_last_video", JSON.stringify(video));
    setVideoInfo(video);
    if (video.audio_features && Object.keys(video.audio_features).length > 0) {
      setAudioFeatures(video.audio_features as Record<string, unknown>);
      localStorage.setItem(`audio_features_${video.video_id}`, JSON.stringify(video.audio_features));
    }
    setChatMessages([
      {
        role: "assistant",
        content: `✅ Loaded **"${video.title}"** by ${video.channel}. I've indexed the transcript (${video.word_count} words). Ask me anything — lyrics, marketing plan, release timing, or Spotify stats!`,
      },
    ]);
    setEvents([]);
    setTodos([]);
  }, []);

  const handleSkipUpload = useCallback(() => {
    setChatMessages([
      {
        role: "assistant",
        content: "No problem — tell me about your concert or campaign (date, location, expected audience, what you need help with) and I'll help build a plan.",
      },
    ]);
    setEvents([]);
    setTodos([]);
  }, []);

  // NEW — reacts to ProjectTypeSelector button clicks.
  // Release types (single/album) behave like the old default flow (UploadPanel visible).
  // Non-release types (concert/social_campaign/other) behave like the existing "skip" flow —
  // chat-only, no song upload — just with a message tailored to the chosen type.
  useEffect(() => {
    if (!projectType) return;

    if (skipNextProjectEffectRef.current) {
      skipNextProjectEffectRef.current = false;
      return;
    }

    const isReleaseType = projectType === "single_release" || projectType === "album_release";

    if (isReleaseType) {
        setChatMessages([
        {
          role: "assistant",
          content:
            "Paste a YouTube URL above to load a song, then ask me anything about it — lyrics, marketing plan, release strategy, Spotify stats, and more.",
        },
      ]);
    } else {
        const label = projectType.replace("_", " ");
      setChatMessages([
        {
          role: "assistant",
          content: `Tell me about your ${label} — dates, goals, budget, anything relevant — and I'll help build a plan.`,
        },
      ]);
    }
    // Re-fetch from Supabase instead of clearing to [] — the calendar/todo
    // list shows all of the band's tasks regardless of which project type
    // is selected, so switching types shouldn't make existing tasks vanish.
    loadFromSupabase();

    // Every project type gets its own project row now — reuse the most
    // recent one for this band+type if it exists, otherwise create one.
    // This is what lets tasks be tagged with a project_id and the agenda
    // filter down to "just this project" instead of always showing everything.
    setCurrentProjectId(null);
    if (projectType && bandId) {
      getLatestProject(bandId, projectType)
        .then((existing) => {
          if (existing) {
            setCurrentProjectId(existing.id);
            return;
          }
          return createProject(bandId, projectType).then((project) => setCurrentProjectId(project.id));
        })
        .catch((err) => console.error("[page] Failed to load/create project", err));
    }
  }, [projectType, bandId, loadFromSupabase]);

  const handleToggleTodo = useCallback(
    async (id: number) => {
      const todo = todos.find((t) => t.id === id);
      if (!todo) return;
      const newCompleted = !todo.completed;
      setTodos((prev) => prev.map((t) => (t.id === id ? { ...t, completed: newCompleted } : t)));
      if (todo.linkedEventId) {
        setEvents((prev) =>
          prev.map((e) => (e.id === todo.linkedEventId ? { ...e, completed: newCompleted } : e))
        );
      }
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

  const handleTodoTitleClick = useCallback(
    (todo: TodoItem) => {
      if (todo.linkedEventId) {
        const linked = events.find((e) => e.id === todo.linkedEventId);
        if (linked) {
          setSelectedEvent(linked);
          return;
        }
      }
      setSelectedEvent({
        id: -(todo.id),
        title: todo.title,
        date: "",
        type: "general",
        savedContent: "",
      });
    },
    [events]
  );

  // "Agenda" (no project selected) shows every task for the band. Selecting
  // a project type filters down to just that project's own tasks, tagged
  // via projectId when they were saved.
  const visibleEvents = projectType ? events.filter((e) => e.projectId === currentProjectId) : events;
  const visibleTodos = projectType ? todos.filter((t) => t.projectId === currentProjectId) : todos;

  const completedCount = visibleTodos.filter((t) => t.completed).length;
  const progressPercent = visibleTodos.length > 0 ? (completedCount / visibleTodos.length) * 100 : 0;

  const handleEventClick = useCallback((event: CalendarEvent) => {
    setSelectedEvent(event);
  }, []);

  const handleCloseDrawer = useCallback(() => {
    setSelectedEvent(null);
  }, []);

  const handleSaveContent = useCallback(
    (eventId: number, content: string) => {
      if (eventId < 0) return;
      setEvents((prev) => prev.map((e) => (e.id === eventId ? { ...e, savedContent: content } : e)));
      setSelectedEvent((prev) => prev && prev.id === eventId ? { ...prev, savedContent: content } : prev);
      fetch(`${API}/calendar/events/${eventId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ saved_content: content }),
      }).catch((err) => console.error("[page] Failed to save doc content", err));
    },
    [API]
  );

  const handleDeleteEvent = useCallback(async (eventId: number) => {
    setEvents((prev) => prev.filter((e) => e.id !== eventId));
    setTodos((prev) => prev.filter((t) => t.linkedEventId !== eventId));
    try {
      await deleteCalendarEvent(eventId);
    } catch (err) {
      console.error("[page] Failed to delete event", err);
    }
  }, []);

  const handleRescheduleEvent = useCallback(async (eventId: number, newDate: string) => {
    setEvents((prev) => prev.map((e) => (e.id === eventId ? { ...e, date: newDate } : e)));
    try {
      await rescheduleCalendarEvent(eventId, newDate);
    } catch (err) {
      console.error("[page] Failed to reschedule event", err);
    }
  }, []);

  const handleReset = useCallback(async () => {
    await fetch(`${API}/band/${bandId}`, { method: "DELETE" });
    setEvents([]);
    setTodos([]);
    setProjectType(null);
    setChatMessages([
      { role: "assistant", content: "Session cleared. Paste a YouTube URL to start fresh, or skip to plan without one." },
    ]);
  }, [API, bandId]);

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

  const handleSendMessage = async (message: string) => {
    setChatMessages((prev) => [...prev, { role: "user", content: message }]);
    setIsChatLoading(true);

    try {
      // projectType, bandId, and currentProjectId are now threaded through to
      // lib/api.ts's sendMessage(), which forwards them to the backend as
      // `project_type` / `band_id` / `project_id`.
      const profileUpdated = profileJustUpdatedRef.current;
      profileJustUpdatedRef.current = false;

      const data = await sendMessage(
        videoInfo?.video_id ?? "",
        message,
        sessionId,
        videoInfo?.title ?? "",
        videoInfo?.channel ?? "",
        audioFeatures ?? undefined,
        projectType,
        bandId,
        currentProjectId,
        profileUpdated,
      );

      try {
        const jsonMatch = data.response.match(/\{[\s\S]*"action"\s*:\s*"delete"[\s\S]*\}/);
        if (jsonMatch) {
          const parsed = JSON.parse(jsonMatch[0]);
          const taskTitle = parsed.task?.toLowerCase().trim() ?? "";
          const toDelete = events.find((e) => {
            const eventTitle = e.title.toLowerCase().trim();
            return (
              eventTitle.includes(taskTitle) ||
              taskTitle.includes(eventTitle) ||
              taskTitle.split(" ").filter((w: string) => w.length > 3).every((w: string) => eventTitle.includes(w))
            );
          });
          if (toDelete) {
            await handleDeleteEvent(toDelete.id);
          } else {
            console.warn("[page] Delete matched no event for task:", taskTitle);
          }
        }
      } catch (_) {}

      // No project was selected when this was sent, but the agent figured
      // out which one it's about (e.g. "plan my concert" typed straight into
      // Agenda) — sync the sidebar to match, without replaying the reset/
      // fetch side effects meant for a manual click (see skipNextProjectEffectRef).
      if (!projectType && data.project_type) {
        skipNextProjectEffectRef.current = true;
        setProjectType(data.project_type as ProjectType);
        setCurrentProjectId(data.project_id ?? null);
      }

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
          // Use what the backend actually ran this turn under, not the live
          // currentProjectId state — avoids the same save-time race we hit
          // with the sidebar project switch.
          projectId: data.project_id ?? currentProjectId,
        },
      ]);
    } catch (err) {
      console.error("[page] Chat error:", err);
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, something went wrong connecting to the AI. Please try again." },
      ]);
    } finally {
      setIsChatLoading(false);
    }
  };

  return (
    <div className="flex flex-col md:flex-row md:h-screen md:overflow-hidden bg-[#f7f5f2]">

      <Sidebar
        events={visibleEvents}
        onEventClick={handleEventClick}
        progress={progressPercent}
        todos={visibleTodos}
        onOpenTodoDrawer={() => setTodoDrawerOpen(true)}
        onOpenBandProfile={() => setBandProfileOpen(true)}
        activeProjectType={projectType}
        onSelectProjectType={setProjectType}
        onShowAgenda={() => setProjectType(null)}
        onOpenAddEventModal={() => setAddEventModalOpen(true)}
        onReset={handleReset}
      />

      <main className="flex-1 min-w-0 md:h-full md:overflow-y-auto bg-[#f7f5f2] px-4 py-6 md:px-6 md:py-8 lg:px-10">
        {visibleEvents.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-slate-400 gap-3">
            <span className="text-5xl">🎵</span>
            <p className="text-sm">Load a song and ask for a marketing plan to see your schedule here.</p>
          </div>
        ) : (
          <DailyFeed
            events={visibleEvents}
            onEventClick={handleEventClick}
            onDeleteEvent={handleDeleteEvent}
            onRescheduleEvent={handleRescheduleEvent}
          />
        )}
      </main>

      <aside className="flex flex-col w-full md:w-[320px] lg:w-[380px] md:h-full md:overflow-hidden bg-white border-t md:border-t-0 md:border-l border-slate-200 shrink-0">
        {(projectType === "single_release" || projectType === "album_release") && (
          <UploadPanel onVideoLoaded={handleVideoLoaded} onSkip={handleSkipUpload} sessionId={sessionId} />
        )}
        {projectType === "concert" && currentProjectId && (
          <ConcertDetailsCapture projectId={currentProjectId} chatActive={chatMessages.length > 0} />
        )}
        <AIChatbot
          messages={chatMessages}
          onSendMessage={handleSendMessage}
          isLoading={isChatLoading}
          renderTaskCard={(msg, i) => {
            if (!msg.tasks || msg.tasksConfirmed) return null;
            return (
              <TaskConfirmationCard
                bandId={bandId}
                videoId={videoInfo?.video_id ?? ""}
                projectId={msg.projectId}
                calendarEvents={msg.tasks.calendar_events}
                todoItems={msg.tasks.todo_items}
                onConfirm={() => handleTaskConfirm(i)}
                onDismiss={() => handleTaskDismiss(i)}
              />
            );
          }}
        />
      </aside>

      {/* Calendar-event click still opens EventDrawer exactly as before —
          untouched by the sidebar refactor. */}
      <EventDrawer
        event={selectedEvent}
        onClose={handleCloseDrawer}
        sessionId={sessionId}
        videoId={videoInfo?.video_id}
        videoTitle={videoInfo?.title}
        videoChannel={videoInfo?.channel}
        onSaveContent={handleSaveContent}
        releaseDate={events.find(e => e.type === "release")?.date ?? ""}
        audioFeatures={audioFeatures}
        bandId={bandId}
      />

      <TodoDrawer
        open={todoDrawerOpen}
        onClose={() => setTodoDrawerOpen(false)}
        todos={visibleTodos}
        onToggle={handleToggleTodo}
        onTitleClick={(todo) => {
          setTodoDrawerOpen(false);
          handleTodoTitleClick(todo);
        }}
      />

      <BandProfileForm
        open={bandProfileOpen}
        onClose={() => setBandProfileOpen(false)}
        bandId={bandId}
        onSaved={() => { profileJustUpdatedRef.current = true; }}
      />

      <AddToCalendarModal
        open={addEventModalOpen}
        onClose={() => setAddEventModalOpen(false)}
        bandId={bandId}
        videoId={videoInfo?.video_id}
        projectId={currentProjectId}
        onSaved={loadFromSupabase}
      />
    </div>
  );
}
