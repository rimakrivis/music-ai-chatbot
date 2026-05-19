"use client";

import { useState } from "react";
import { analyzeVideo, AnalyzeResponse } from "@/lib/api";

interface UrlInputProps {
  onSuccess: (data: AnalyzeResponse) => void;
}

export default function UrlInput({ onSuccess }: UrlInputProps) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAnalyze() {
    if (!url.trim()) {
      setError("Paste a YouTube URL first.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const data = await analyzeVideo(url.trim());
      onSuccess(data);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Something went wrong.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-2">
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
          placeholder="https://www.youtube.com/watch?v=..."
          disabled={loading}
          className="flex-1 bg-slate-50 border border-slate-200 text-slate-800 placeholder-slate-300
                     rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-violet-400
                     focus:ring-2 focus:ring-violet-100 transition-all disabled:opacity-50 font-mono"
        />
        <button
          onClick={handleAnalyze}
          disabled={loading}
          className="bg-gradient-to-r from-violet-500 to-indigo-600 hover:shadow-lg
                     disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-violet-200
                     text-white font-semibold px-5 py-3 rounded-xl transition-all text-sm whitespace-nowrap"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Fetching…
            </span>
          ) : (
            "Analyze →"
          )}
        </button>
      </div>

      {error && <p className="text-rose-400 text-sm px-1">⚠ {error}</p>}

      {loading && (
        <p className="text-slate-400 text-xs px-1 animate-pulse">
          Fetching transcript and building vector index…
        </p>
      )}
    </div>
  );
}