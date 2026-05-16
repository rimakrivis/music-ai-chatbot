"use client";

import { useState } from "react";
import UrlInput from "@/components/UrlInput";
import VideoInfoCard from "@/components/VideoInfoCard";
import { AnalyzeResponse } from "@/lib/api";

export default function HomePage() {
  const [videoData, setVideoData] = useState<AnalyzeResponse | null>(null);

  function handleAnalyzeSuccess(data: AnalyzeResponse) {
    setVideoData(data);
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4 py-16 gap-10">
      {/* Header */}
      <div className="text-center flex flex-col gap-3 max-w-lg">
        <div className="flex items-center justify-center gap-2 mb-2">
          <span className="text-3xl">🎵</span>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100">Music AI</h1>
        </div>
        <p className="text-zinc-400 text-sm leading-relaxed">
          Paste a YouTube music video URL. The AI will fetch the transcript, 
          index it, and let you chat — analyzing lyrics, marketing potential, 
          artist stats, and release strategy.
        </p>
      </div>

      {/* URL Input */}
      <UrlInput onSuccess={handleAnalyzeSuccess} />

      {/* Video card — shown after successful analyze */}
      {videoData && (
        <div className="w-full max-w-2xl animate-in fade-in slide-in-from-bottom-4 duration-300">
          <VideoInfoCard data={videoData} />
        </div>
      )}

      {/* Footer hint */}
      {!videoData && (
        <p className="text-zinc-600 text-xs text-center max-w-sm">
          Works with any YouTube video that has captions. 
          Try a popular artist first — Taylor Swift, Drake, etc.
        </p>
      )}
    </main>
  );
}
