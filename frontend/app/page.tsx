"use client";

import { useState } from "react";
import UrlInput from "@/components/UrlInput";
import VideoInfoCard from "@/components/VideoInfoCard";
import { AnalyzeResponse } from "@/lib/api";

export default function HomePage() {
  const [videoData, setVideoData] = useState<AnalyzeResponse | null>(null);
  const [tab, setTab] = useState<"url" | "upload">("url");

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-violet-50/40 flex flex-col items-center justify-center px-4 py-16 gap-10">

      {/* Hero */}
      <div className="text-center flex flex-col items-center gap-4 max-w-lg">
        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-xl shadow-violet-200 mb-2">
          <span className="text-2xl">🎵</span>
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-800">Music AI</h1>
        <p className="text-slate-400 text-sm leading-relaxed max-w-sm">
          Paste a YouTube URL and let AI analyze lyrics, marketing potential, artist stats, and build your release strategy.
        </p>
      </div>

      {/* Card */}
      <div className="w-full max-w-xl bg-white rounded-2xl border border-slate-200 shadow-xl shadow-slate-100 p-6 flex flex-col gap-5">

        {/* Tabs */}
        <div className="flex bg-slate-100 rounded-xl p-1 gap-1">
          <button
            onClick={() => setTab("url")}
            className={`flex-1 text-sm py-2 rounded-lg font-medium transition-all ${
              tab === "url"
                ? "bg-white text-slate-800 shadow-sm"
                : "text-slate-400 hover:text-slate-600"
            }`}
          >
            🔗 YouTube URL
          </button>
          <button
            onClick={() => setTab("upload")}
            className={`flex-1 text-sm py-2 rounded-lg font-medium transition-all ${
              tab === "upload"
                ? "bg-white text-slate-800 shadow-sm"
                : "text-slate-400 hover:text-slate-600"
            }`}
          >
            📁 Upload Video
          </button>
        </div>

        {/* URL tab */}
        {tab === "url" && (
          <UrlInput onSuccess={setVideoData} />
        )}

        {/* Upload tab — coming soon */}
        {tab === "upload" && (
          <div className="flex flex-col items-center justify-center gap-3 py-10 border-2 border-dashed border-slate-200 rounded-xl">
            <span className="text-3xl">📁</span>
            <p className="text-slate-500 text-sm font-medium">Video upload coming soon</p>
            <p className="text-slate-300 text-xs text-center max-w-xs">
              You'll be able to upload MP4 or audio files directly. For now, use a YouTube URL.
            </p>
            <button
              onClick={() => setTab("url")}
              className="mt-2 text-xs text-violet-600 hover:text-violet-800 border border-violet-200 hover:border-violet-300 px-4 py-2 rounded-lg transition-colors bg-violet-50"
            >
              Use YouTube URL instead
            </button>
          </div>
        )}

        {/* Video card after success */}
        {videoData && (
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
            <VideoInfoCard data={videoData} />
          </div>
        )}
      </div>

      {/* Footer */}
      {!videoData && (
        <p className="text-slate-300 text-xs text-center max-w-sm">
          Works with any YouTube video that has captions. Try a popular artist first.
        </p>
      )}
    </main>
  );
}