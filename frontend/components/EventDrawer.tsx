"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { CalendarEvent, EVENT_COLORS, ChatMessage } from "@/lib/types";

const XIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
    <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
  </svg>
);

const SendIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
    <path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>
  </svg>
);

const FileTextIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
    <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
    <polyline points="14 2 14 8 20 8"/>
    <line x1="16" x2="8" y1="13" y2="13"/>
    <line x1="16" x2="8" y1="17" y2="17"/>
    <line x1="10" x2="8" y1="9" y2="9"/>
  </svg>
);

const CheckIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);

const PlusIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
    <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
  </svg>
);

interface PendingSave {
  content: string;
  messageIndex: number;
}

interface EventDrawerProps {
  event: CalendarEvent | null;
  onClose: () => void;
  sessionId: string;
  videoId?: string;
  videoTitle?: string;
  videoChannel?: string;
  onSaveContent?: (eventId: number, content: string) => void;
}

export default function EventDrawer({
  event,
  onClose,
  sessionId,
  videoId,
  videoTitle,
  videoChannel,
  onSaveContent,
}: EventDrawerProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [docContent, setDocContent] = useState<string>("");
  const [pendingSave, setPendingSave] = useState<PendingSave | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    if (event) {
      setIsVisible(true);
      setDocContent(event.savedContent ?? "");
      setPendingSave(null);
      setMessages([
        {
          role: "assistant",
          content: `I'm ready to help with **"${event.title}"** (${event.date}). Ask me to write a Spotify pitch, Instagram caption, press release, or anything specific to this task.`,
        },
      ]);
    } else {
      setIsVisible(false);
      setMessages([]);
      setDocContent("");
      setPendingSave(null);
    }
    setInput("");
  }, [event?.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || loading || !event) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);

    try {
      const res = await fetch(`${API}/event-chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMessage,
          event_title: event.title,
          event_type: event.type,
          event_date: event.date,
          video_title: videoTitle ?? "",
          video_channel: videoChannel ?? "",
          video_id: videoId ?? "",
          doc_content: docContent,
        }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const assistantContent: string = data.response ?? "Sorry, no response received.";

      setMessages((prev) => [...prev, { role: "assistant", content: assistantContent }]);
      setPendingSave({ content: assistantContent, messageIndex: messages.length + 1 });
    } catch (err) {
      console.error("[EventDrawer] chat error:", err);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, event, messages.length, videoId, videoTitle, videoChannel, sessionId, docContent, API]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSaveToDoc = async (mode: "replace" | "add") => {
    if (!pendingSave || !event) return;
    const newContent =
      mode === "replace"
        ? pendingSave.content
        : docContent
          ? `${docContent}\n\n---\n\n${pendingSave.content}`
          : pendingSave.content;

    setDocContent(newContent);
    onSaveContent?.(event.id, newContent);
    setPendingSave(null);

    // Persist to Supabase
    try {
      await fetch(`${API}/calendar/events/${event.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ saved_content: newContent }),
      });
      console.log("[EventDrawer] Saved content to Supabase");
    } catch (e) {
      console.error("[EventDrawer] Failed to save content to Supabase", e);
    }
  };

  if (!event) return null;

  const colors = EVENT_COLORS[event.type] || EVENT_COLORS.general;

  return (
    <>
      <div
        onClick={onClose}
        className={`fixed inset-0 bg-black/20 backdrop-blur-sm z-40 transition-opacity duration-300 ${
          isVisible ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
      />

      <div
        className={`fixed top-0 right-0 h-full z-50 flex transition-transform duration-300 ease-out
          ${isVisible ? "translate-x-0" : "translate-x-full"}
          w-full max-w-2xl`}
      >
        {/* Left panel: Notes */}
        <div className="w-[45%] flex flex-col bg-slate-50 border-r border-slate-200 overflow-hidden">
          <div className={`${colors.bg} px-4 py-4 border-b border-slate-200 shrink-0`}>
            <div className="flex items-center gap-2 mb-1">
              <span className={`${colors.icon} text-xs font-semibold uppercase tracking-wide`}>
                {event.type.replace("_", " ")}
              </span>
            </div>
            <h2 className="text-slate-800 font-semibold text-base leading-tight">{event.title}</h2>
            <p className="text-slate-500 text-xs mt-1">{event.date}</p>
          </div>

          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-slate-100 bg-white shrink-0">
            <FileTextIcon />
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Notes</span>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            {docContent ? (
              <div className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
                {docContent}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
                <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center text-slate-400">
                  <FileTextIcon />
                </div>
                <p className="text-xs text-slate-400 max-w-[160px]">
                  Chat with the AI and save outputs here.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Right panel: Chat */}
        <div className="flex-1 flex flex-col bg-white overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 shrink-0">
            <span className="text-sm font-semibold text-slate-700">Creative Assistant</span>
            <button
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors"
            >
              <XIcon />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[90%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed
                    ${msg.role === "user"
                      ? "bg-slate-800 text-white rounded-br-sm"
                      : "bg-slate-100 text-slate-700 rounded-bl-sm"
                    }`}
                >
                  <p className="whitespace-pre-line">{msg.content}</p>
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="bg-slate-100 rounded-2xl rounded-bl-sm px-4 py-3">
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {pendingSave && (
            <div className="mx-4 mb-3 rounded-xl border border-slate-200 bg-slate-50 overflow-hidden shrink-0">
              <div className="px-3 py-2 border-b border-slate-100">
                <p className="text-xs font-semibold text-slate-600">Save to notes?</p>
                <p className="text-xs text-slate-400 mt-0.5">
                  {docContent ? "You already have notes. Replace or add below?" : "This will appear in the notes panel."}
                </p>
              </div>
              <div className="flex">
                {docContent && (
                  <button
                    onClick={() => handleSaveToDoc("replace")}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-medium text-rose-600 hover:bg-rose-50 transition-colors border-r border-slate-100"
                  >
                    <CheckIcon />
                    Replace
                  </button>
                )}
                <button
                  onClick={() => handleSaveToDoc("add")}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-medium text-slate-700 hover:bg-slate-100 transition-colors border-r border-slate-100"
                >
                  <PlusIcon />
                  {docContent ? "Add below" : "Save"}
                </button>
                <button
                  onClick={() => setPendingSave(null)}
                  className="px-3 py-2 text-xs text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
                >
                  Skip
                </button>
              </div>
            </div>
          )}

          <div className="px-4 pb-4 pt-2 shrink-0">
            <div className="relative flex items-center">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Write a caption, Spotify pitch, press release..."
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 pr-12 text-sm text-slate-700 placeholder-slate-400 outline-none focus:border-slate-300 focus:ring-2 focus:ring-slate-100 transition-all"
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || loading}
                className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 bg-slate-800 hover:bg-slate-700 disabled:bg-slate-300 rounded-lg flex items-center justify-center text-white transition-colors"
              >
                <SendIcon />
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}