"use client";
import { useState } from "react";
import { analyzeVideo, AnalyzeResponse } from "@/lib/api";

const LinkIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
  </svg>
);

const CheckIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);

const SpinnerIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="animate-spin">
    <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
  </svg>
);

interface UploadPanelProps {
  onVideoLoaded: (video: AnalyzeResponse) => void;
}

export default function UploadPanel({ onVideoLoaded }: UploadPanelProps) {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [videoTitle, setVideoTitle] = useState("");

  const handleAnalyze = async () => {
    if (!url.trim()) return;

    const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/;
    if (!youtubeRegex.test(url.trim())) {
      setErrorMsg("Please paste a valid YouTube URL");
      setStatus("error");
      return;
    }

    setStatus("loading");
    setErrorMsg("");
    console.log("[UploadPanel] Analyzing URL:", url);

    try {
      const data = await analyzeVideo(url.trim());
      console.log("[UploadPanel] Analysis complete:", data);
      setVideoTitle(data.title);
      setStatus("success");
      onVideoLoaded(data);
    } catch (err) {
      console.error("[UploadPanel] Error:", err);
      setErrorMsg(err instanceof Error ? err.message : "Something went wrong. Try again.");
      setStatus("error");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleAnalyze();
  };

  const handleReset = () => {
    setUrl("");
    setStatus("idle");
    setErrorMsg("");
    setVideoTitle("");
  };

  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100">
      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 bg-slate-800 rounded-xl flex items-center justify-center">
          <span className="text-white text-lg">♪</span>
        </div>
        <h3 className="text-slate-800 font-semibold text-lg">AI Music</h3>
      </div>

      {/* Success state */}
      {status === "success" ? (
        <div className="flex flex-col gap-3">
          <div className="flex items-start gap-2 bg-green-50 border border-green-200 rounded-xl px-3 py-3">
            <div className="text-green-500 mt-0.5 shrink-0"><CheckIcon /></div>
            <div>
              <p className="text-green-700 text-sm font-medium">Song loaded!</p>
              <p className="text-green-600 text-xs mt-0.5 line-clamp-2">{videoTitle}</p>
            </div>
          </div>
          <button
            onClick={handleReset}
            className="text-slate-400 hover:text-slate-600 text-xs text-center transition-colors"
          >
            Load a different song →
          </button>
        </div>
      ) : (
        <>
          {/* URL Input */}
          <div className="mb-4">
            <p className="text-slate-600 text-sm font-medium mb-2">Upload YouTube URL</p>
            <div className="relative">
              <input
                type="text"
                value={url}
                onChange={(e) => { setUrl(e.target.value); if (status === "error") setStatus("idle"); }}
                onKeyDown={handleKeyDown}
                placeholder="Paste YouTube URL here"
                disabled={status === "loading"}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 pr-10 text-sm text-slate-700 placeholder-slate-400 outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-100 transition-all disabled:opacity-50"
              />
              <button
                onClick={handleAnalyze}
                disabled={!url.trim() || status === "loading"}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 disabled:opacity-40 transition-colors"
              >
                {status === "loading" ? <SpinnerIcon /> : <LinkIcon />}
              </button>
            </div>

            {/* Loading message */}
            {status === "loading" && (
              <p className="text-slate-400 text-xs mt-2 flex items-center gap-1">
                <span className="inline-block w-1 h-1 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="inline-block w-1 h-1 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="inline-block w-1 h-1 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                <span className="ml-1">Fetching transcript, this may take 30s...</span>
              </p>
            )}

            {/* Error message */}
            {status === "error" && (
              <p className="text-red-400 text-xs mt-2">{errorMsg}</p>
            )}
          </div>

          {/* Analyze button */}
          <button
            onClick={handleAnalyze}
            disabled={!url.trim() || status === "loading"}
            className="w-full bg-slate-800 hover:bg-slate-700 disabled:bg-slate-300 text-white text-sm font-medium py-2.5 rounded-xl transition-colors"
          >
            {status === "loading" ? "Analyzing..." : "Analyze Song"}
          </button>
        </>
      )}
    </div>
  );
}
