"use client";

export interface Message {
  role: "user" | "assistant";
  content: string;
  tools_used?: string[];
}

// One color per tool — shown as badge pills under AI messages
const TOOL_COLORS: Record<string, string> = {
  search_transcript:           "bg-blue-900/60 border-blue-700/50 text-blue-300",
  extract_lyrics:              "bg-violet-900/60 border-violet-700/50 text-violet-300",
  analyze_marketing_potential: "bg-emerald-900/60 border-emerald-700/50 text-emerald-300",
  get_artist_info:             "bg-orange-900/60 border-orange-700/50 text-orange-300",
  find_release_timing:         "bg-pink-900/60 border-pink-700/50 text-pink-300",
  search_marketing_knowledge:  "bg-teal-900/60 border-teal-700/50 text-teal-300",
};

const TOOL_LABELS: Record<string, string> = {
  search_transcript:           "🔍 search_transcript",
  extract_lyrics:              "🎵 extract_lyrics",
  analyze_marketing_potential: "📊 analyze_marketing",
  get_artist_info:             "🎤 get_artist_info",
  find_release_timing:         "📅 find_release_timing",
  search_marketing_knowledge:  "📚 search_marketing_knowledge",
};

interface ChatMessageProps {
  message: Message;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex flex-col gap-1.5 ${isUser ? "items-end" : "items-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? "bg-violet-600 text-white rounded-br-sm"
            : "bg-zinc-800 border border-zinc-700 text-zinc-100 rounded-bl-sm"
        }`}
      >
        {message.content}
      </div>

      {/* Tool badges — only on AI messages that used tools */}
      {!isUser && message.tools_used && message.tools_used.length > 0 && (
        <div className="flex flex-wrap gap-1.5 px-1">
          {message.tools_used.map((tool) => {
            const colorClass = TOOL_COLORS[tool] || "bg-zinc-800 border-zinc-700 text-zinc-400";
            const label = TOOL_LABELS[tool] || tool;
            return (
              <span
                key={tool}
                className={`border text-xs font-mono px-2 py-0.5 rounded-full ${colorClass}`}
              >
                {label}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}
