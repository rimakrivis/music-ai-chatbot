"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import ChatMessage, { Message } from "@/components/ChatMessage";
import ChatInput from "@/components/ChatInput";
import TranscriptPanel from "@/components/TranscriptPanel";
import { sendMessage } from "@/lib/api";

const STARTER_PROMPTS = [
  "What is this song about?",
  "Extract the lyrics and format them cleanly.",
  "What is the marketing potential for this song?",
  "Tell me about the artist's Spotify stats.",
  "When should this song be released and on which platforms?",
];

function ChatPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const video_id = searchParams.get("video_id") || "";
  const video_title = searchParams.get("title") || "Unknown Video";
  const video_channel = searchParams.get("channel") || "";

  const [sessionId] = useState(() => crypto.randomUUID());
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (video_id === null) {
      router.push("/");
    }
  }, [video_id, router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend(text: string) {
    if (!video_id) return;

    const userMessage: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);
    setError(null);

    try {
      const data = await sendMessage(video_id, text, sessionId, video_title, video_channel);
      const aiMessage: Message = {
        role: "assistant",
        content: data.response,
        tools_used: data.tools_used,
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

  if (!video_id) return null;

  return (
    <div className="flex flex-col h-screen bg-zinc-950">
      <header className="flex items-center justify-between px-4 py-3 border-b border-zinc-800 bg-zinc-950 z-10">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={() => router.push("/")}
            className="text-zinc-500 hover:text-zinc-200 transition-colors shrink-0 text-sm"
          >
            ← Back
          </button>
          <div className="h-4 w-px bg-zinc-800 shrink-0" />
          <div className="min-w-0">
            <p className="text-zinc-100 text-sm font-medium truncate">{video_title}</p>
            <p className="text-zinc-400 text-xs truncate">{video_channel}</p>
            <p className="text-zinc-600 text-xs font-mono truncate">id: {video_id}</p>
          </div>
        </div>
        <button
          onClick={() => router.push("/")}
          className="shrink-0 text-xs text-zinc-500 hover:text-violet-400 transition-colors border border-zinc-800 hover:border-violet-800 px-3 py-1.5 rounded-lg"
        >
          + New video
        </button>
      </header>

      <TranscriptPanel video_id={video_id} />

      <div className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 ? (
          <EmptyState onPromptSelect={handleSend} />
        ) : (
          <div className="max-w-2xl mx-auto flex flex-col gap-5">
            {messages.map((msg, i) => (
              <ChatMessage key={i} message={msg} />
            ))}
            {loading && (
              <div className="flex items-start gap-2">
                <div className="bg-zinc-800 border border-zinc-700 rounded-2xl rounded-bl-sm px-4 py-3 text-sm text-zinc-500 flex items-center gap-2">
                  <span className="inline-block w-3 h-3 border-2 border-zinc-600 border-t-violet-400 rounded-full animate-spin" />
                  Thinking…
                </div>
              </div>
            )}
            {error && (
              <p className="text-red-400 text-xs text-center">⚠ {error} — try again.</p>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <ChatInput onSend={handleSend} disabled={loading} />
    </div>
  );
}

function EmptyState({ onPromptSelect }: { onPromptSelect: (p: string) => void }) {
  return (
    <div className="max-w-2xl mx-auto flex flex-col items-center gap-8 pt-8">
      <div className="text-center flex flex-col gap-2">
        <span className="text-4xl">🎤</span>
        <h2 className="text-zinc-300 font-semibold">Ask anything about this song</h2>
        <p className="text-zinc-600 text-sm">The AI will pick the right tools and show you which ones it used.</p>
      </div>
      <div className="w-full flex flex-col gap-2">
        <p className="text-zinc-600 text-xs text-center mb-1">Try one of these</p>
        {STARTER_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            onClick={() => onPromptSelect(prompt)}
            className="w-full text-left text-sm text-zinc-400 hover:text-zinc-100 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-zinc-700 rounded-xl px-4 py-3 transition-colors"
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
      <div className="min-h-screen flex items-center justify-center text-zinc-500 text-sm">
        Loading…
      </div>
    }>
      <ChatPageInner />
    </Suspense>
  );
}