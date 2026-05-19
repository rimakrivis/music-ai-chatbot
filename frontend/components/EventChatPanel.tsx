"use client";

import { useState, useEffect, useRef } from "react";
import { sendMessage } from "@/lib/api";

interface CalendarEvent {
  id: number;
  title: string;
  date: string;
  type: string;
}

interface EventMessage {
  role: "user" | "assistant";
  content: string;
}

interface EventChatPanelProps {
  event: CalendarEvent;
  sessionId: string;
  videoId: string;
  videoTitle: string;
  videoChannel: string;
  onClose: () => void;
  onSaveToCalendar: (event: { title: string; date: string; type: string }) => void;
}

const TYPE_CONFIG: Record<string, { bg: string; border: string; text: string; dot: string; label: string }> = {
  release:      { bg: "bg-violet-50",  border: "border-violet-200", text: "text-violet-700", dot: "bg-violet-400",  label: "Release" },
  spotify:      { bg: "bg-green-50",   border: "border-green-200",  text: "text-green-700",  dot: "bg-green-400",   label: "Spotify" },
  youtube:      { bg: "bg-red-50",     border: "border-red-200",    text: "text-red-700",    dot: "bg-red-400",     label: "YouTube" },
  social_media: { bg: "bg-blue-50",    border: "border-blue-200",   text: "text-blue-700",   dot: "bg-blue-400",    label: "Social" },
  promo:        { bg: "bg-orange-50",  border: "border-orange-200", text: "text-orange-700", dot: "bg-orange-400",  label: "Promo" },
  deadline:     { bg: "bg-rose-50",    border: "border-rose-200",   text: "text-rose-700",   dot: "bg-rose-400",    label: "Deadline" },
  general:      { bg: "bg-slate-50",   border: "border-slate-200",  text: "text-slate-600",  dot: "bg-slate-400",   label: "General" },
};

export default function EventChatPanel({
  event, sessionId, videoId, videoTitle, videoChannel, onClose, onSaveToCalendar
}: EventChatPanelProps) {
  const [messages, setMessages] = useState<EventMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [editableContent, setEditableContent] = useState<string | null>(null);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const config = TYPE_CONFIG[event.type] || TYPE_CONFIG.general;

  // Auto-send first message scoped to this event
  useEffect(() => {
    autoPrompt();
  }, [event.id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function autoPrompt() {
    setLoading(true);
    const prompt = `For the song "${videoTitle}" by "${videoChannel}", help me plan this specific task: "${event.title}" scheduled for ${event.date}. Generate a concise actionable draft or plan for this. Keep it focused and practical.`;

    try {
      const data = await sendMessage(videoId, prompt, `${sessionId}_event_${event.id}`, videoTitle, videoChannel);
      setMessages([{ role: "assistant", content: data.response }]);
    } catch (e) {
      setMessages([{ role: "assistant", content: "Couldn't load a draft. Ask me anything about this task!" }]);
    } finally {
      setLoading(false);
    }
  }

  async function handleSend() {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setLoading(true);

    try {
      const data = await sendMessage(videoId, userMsg, `${sessionId}_event_${event.id}`, videoTitle, videoChannel);
      setMessages((prev) => [...prev, { role: "assistant", content: data.response }]);
    } catch (e) {
      setMessages((prev) => [...prev, { role: "assistant", content: "Something went wrong. Try again." }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full bg-white border-l border-slate-200 shadow-xl">
      {/* Header */}
      <div className={`px-5 py-4 border-b ${config.border} ${config.bg} flex items-start justify-between gap-3`}>
        <div className="flex items-start gap-3 min-w-0">
          <div className={`w-3 h-3 rounded-full shrink-0 mt-1 ${config.dot}`} />
          <div className="min-w-0">
            <p className={`font-semibold text-sm ${config.text} truncate`}>{event.title}</p>
            <p className="text-slate-400 text-xs mt-0.5">{event.date}</p>
            <span className={`text-xs border px-2 py-0.5 rounded-full mt-1 inline-block ${config.bg} ${config.border} ${config.text}`}>
              {config.label}
            </span>
          </div>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-700 transition-colors text-lg leading-none shrink-0">×</button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3">
        {loading && messages.length === 0 && (
          <div className="flex items-center gap-2 text-slate-400 text-xs">
            <span className="w-3 h-3 border-2 border-slate-300 border-t-violet-500 rounded-full animate-spin" />
            Generating draft…
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex flex-col gap-1.5 ${msg.role === "user" ? "items-end" : "items-start"}`}>
            {msg.role === "assistant" ? (
              <div className="w-full">
                {editingIndex === i ? (
                  <textarea
                    value={editableContent ?? msg.content}
                    onChange={(e) => setEditableContent(e.target.value)}
                    className="w-full text-xs text-slate-700 bg-slate-50 border border-violet-300 rounded-xl px-3 py-2.5 outline-none focus:ring-2 focus:ring-violet-100 resize-none leading-relaxed"
                    rows={8}
                  />
                ) : (
                  <div className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-xs text-slate-700 leading-relaxed whitespace-pre-wrap">
                    {editableContent && editingIndex === null ? editableContent : msg.content}
                  </div>
                )}

                {/* Action buttons under AI messages */}
                <div className="flex gap-2 mt-1.5">
                  {editingIndex === i ? (
                    <button
                      onClick={() => setEditingIndex(null)}
                      className="text-xs text-violet-600 hover:text-violet-800 transition-colors"
                    >
                      ✓ Done editing
                    </button>
                  ) : (
                    <button
                      onClick={() => { setEditingIndex(i); setEditableContent(msg.content); }}
                      className="text-xs text-slate-400 hover:text-slate-700 transition-colors"
                    >
                      ✏️ Edit
                    </button>
                  )}
                  <button
                    onClick={() => navigator.clipboard.writeText(editableContent ?? msg.content)}
                    className="text-xs text-slate-400 hover:text-slate-700 transition-colors"
                  >
                    📋 Copy
                  </button>
                  <button
                    onClick={() => onSaveToCalendar({ title: event.title, date: event.date, type: event.type })}
                    className={`text-xs px-2.5 py-1 rounded-lg border transition-all ${config.bg} ${config.border} ${config.text} hover:shadow-sm`}
                  >
                    + Plan this
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-gradient-to-br from-violet-500 to-indigo-600 text-white rounded-2xl rounded-br-sm px-3 py-2 text-xs max-w-[85%]">
                {msg.content}
              </div>
            )}
          </div>
        ))}

        {loading && messages.length > 0 && (
          <div className="flex items-center gap-2 text-slate-400 text-xs">
            <span className="w-3 h-3 border-2 border-slate-300 border-t-violet-500 rounded-full animate-spin" />
            Thinking…
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-slate-200 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
          placeholder="Ask about this task…"
          className="flex-1 text-xs bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 outline-none focus:border-violet-400 focus:ring-2 focus:ring-violet-100 text-slate-700 placeholder-slate-400"
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="bg-gradient-to-r from-violet-500 to-indigo-600 text-white text-xs px-4 py-2 rounded-xl shadow-md shadow-violet-200 hover:shadow-lg transition-all disabled:opacity-40"
        >
          Send
        </button>
      </div>
    </div>
  );
}