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
    <div className="flex flex-col gap-4">
      {/* Divider */}
      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-slate-100" />
        <span className="text-slate-300 text-xs">Ready to chat</span>
        <div className="h-px flex-1 bg-slate-100" />
      </div>

      {/* Video info */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-col gap-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex flex-col gap-0.5 min-w-0">
            <p className="text-slate-800 font-semibold text-sm leading-tight truncate">{data.title}</p>
            <p className="text-slate-400 text-xs">{data.channel}</p>
          </div>
          <span className="shrink-0 bg-green-50 border border-green-200 text-green-600 text-xs px-2 py-1 rounded-lg">
            ✓ Indexed
          </span>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-2">
          <Stat label="Duration" value={formatDuration(data.duration)} />
          <Stat label="Words" value={data.word_count.toLocaleString()} />
          <Stat label="Chunks" value={data.chunks_created.toString()} />
          <Stat label="Source" value={SOURCE_LABELS[data.source] || data.source} />
        </div>
      </div>

      {/* CTA */}
      <button
        onClick={handleStartChat}
        className="w-full bg-gradient-to-r from-violet-500 to-indigo-600 text-white font-semibold
                   py-3 rounded-xl shadow-md shadow-violet-200 hover:shadow-lg transition-all text-sm"
      >
        Start chatting →
      </button>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg px-2.5 py-2 flex flex-col gap-0.5">
      <span className="text-slate-400 text-xs">{label}</span>
      <span className="text-slate-700 text-xs font-mono truncate">{value}</span>
    </div>
  );
}