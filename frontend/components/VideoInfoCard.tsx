"use client";

import { useRouter } from "next/navigation";
import { AnalyzeResponse } from "@/lib/api";

interface VideoInfoCardProps {
  data: AnalyzeResponse;
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

const SOURCE_LABELS: Record<string, string> = {
  youtube_api: "YouTube Captions",
  whisper: "Whisper Transcription",
};

export default function VideoInfoCard({ data }: VideoInfoCardProps) {
  const router = useRouter();

function handleStartChat() {
    const params = new URLSearchParams({
      video_id: data.video_id,
      title: data.title,
      channel: data.channel,
    });
    router.push(`/chat?${params.toString()}`);
  }

  return (
    <div className="w-full max-w-2xl mx-auto bg-zinc-900 border border-zinc-700 rounded-xl p-6 flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="text-zinc-100 font-semibold text-lg leading-tight line-clamp-2">
            {data.title}
          </h2>
          <p className="text-zinc-400 text-sm">{data.channel}</p>
        </div>
        <span className="shrink-0 bg-violet-900/50 border border-violet-700/50 text-violet-300 text-xs font-mono px-2 py-1 rounded-md">
          ✓ Indexed
        </span>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Stat label="Duration" value={formatDuration(data.duration)} />
        <Stat label="Words" value={data.word_count.toLocaleString()} />
        <Stat label="Chunks" value={data.chunks_created.toString()} />
        <Stat label="Source" value={SOURCE_LABELS[data.source] || data.source} />
      </div>

      {/* CTA */}
      <button
        onClick={handleStartChat}
        className="w-full bg-violet-600 hover:bg-violet-500 text-white font-semibold
                   py-3 rounded-lg transition-colors text-sm"
      >
        Start chatting →
      </button>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-zinc-800 rounded-lg px-3 py-2 flex flex-col gap-0.5">
      <span className="text-zinc-500 text-xs">{label}</span>
      <span className="text-zinc-100 text-sm font-mono truncate">{value}</span>
    </div>
  );
}
