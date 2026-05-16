"use client";

import { useState, useEffect } from "react";
import { getTranscript } from "@/lib/api";

interface TranscriptPanelProps {
  video_id: string;
}

export default function TranscriptPanel({ video_id }: TranscriptPanelProps) {
  const [open, setOpen] = useState(false);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [wordCount, setWordCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch transcript the first time the panel is opened
  useEffect(() => {
    if (!open || transcript !== null) return;

    async function fetchTranscript() {
      setLoading(true);
      setError(null);
      try {
        const data = await getTranscript(video_id);
        setTranscript(data.transcript_text);
        setWordCount(data.word_count);
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "Failed to load transcript.";
        setError(msg);
      } finally {
        setLoading(false);
      }
    }

    fetchTranscript();
  }, [open, video_id, transcript]);

  return (
    <div className="border-b border-zinc-800 bg-zinc-950">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-zinc-400
                   hover:text-zinc-200 text-sm transition-colors"
      >
        <span className="flex items-center gap-2">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <polyline points="10 9 9 9 8 9"/>
          </svg>
          Transcript
          {wordCount !== null && (
            <span className="text-zinc-600 font-mono text-xs">{wordCount.toLocaleString()} words</span>
          )}
        </span>
        <svg
          width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          className={`transition-transform duration-200 ${open ? "rotate-180" : ""}`}
        >
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </button>

      {open && (
        <div className="px-4 pb-4 max-h-60 overflow-y-auto">
          {loading && (
            <p className="text-zinc-500 text-xs animate-pulse">Loading transcript…</p>
          )}
          {error && (
            <p className="text-red-400 text-xs">⚠ {error}</p>
          )}
          {transcript && (
            <p className="text-zinc-400 text-xs leading-relaxed font-mono whitespace-pre-wrap">
              {transcript}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
