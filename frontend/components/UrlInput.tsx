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

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") handleAnalyze();
  }

  return (
    <div className="w-full max-w-2xl mx-auto flex flex-col gap-3">
      <div className="flex gap-2">
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="https://www.youtube.com/watch?v=..."
          disabled={loading}
          className="flex-1 bg-zinc-900 border border-zinc-700 text-zinc-100 placeholder-zinc-500
                     rounded-lg px-4 py-3 text-sm font-mono focus:outline-none focus:border-violet-500
                     transition-colors disabled:opacity-50"
        />
        <button
          onClick={handleAnalyze}
          disabled={loading}
          className="bg-violet-600 hover:bg-violet-500 disabled:bg-violet-900 disabled:cursor-not-allowed
                     text-white font-semibold px-6 py-3 rounded-lg transition-colors text-sm whitespace-nowrap"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Fetching…
            </span>
          ) : (
            "Analyze"
          )}
        </button>
      </div>

      {error && (
        <p className="text-red-400 text-sm px-1">
          ⚠ {error}
        </p>
      )}

      {loading && (
        <p className="text-zinc-500 text-xs px-1 animate-pulse">
          Fetching transcript and building vector index…
        </p>
      )}
    </div>
  );
}
