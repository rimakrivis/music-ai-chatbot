"use client";
import { useRef, useState } from "react";
import { analyzeVideo, analyzeAudioFile, AnalyzeResponse } from "@/lib/api";

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
  onSkip: () => void; // NEW — lets the user plan without a song
  sessionId: string;
}

export default function UploadPanel({ onVideoLoaded, onSkip, sessionId }: UploadPanelProps) {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [videoTitle, setVideoTitle] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [songTitle, setSongTitle] = useState("");
  const [artistName, setArtistName] = useState("");
  const [skipped, setSkipped] = useState(false); // NEW — local view state
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleAnalyze = async () => {
    setStatus("loading");
    setErrorMsg("");

    try {
      if (selectedFile) {
        console.log("[UploadPanel] Uploading file:", selectedFile.name);
      const data = await analyzeAudioFile(
          selectedFile,
          sessionId,
          songTitle.trim() || selectedFile.name.replace(/\.[^/.]+$/, ""),
          artistName.trim() || "Unknown Artist"
        );  
        setVideoTitle(data.title);
        setStatus("success");
        onVideoLoaded(data);
      } else {
        if (!url.trim()) {
          setErrorMsg("Please paste a YouTube URL or choose an audio file");
          setStatus("error");
          return;
        }
        const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/;
        if (!youtubeRegex.test(url.trim())) {
          setErrorMsg("Please paste a valid YouTube URL");
          setStatus("error");
          return;
        }
        const data = await analyzeVideo(url.trim());
        setVideoTitle(data.title);
        setStatus("success");
        onVideoLoaded(data);
      }
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
    setSelectedFile(null);
    setStatus("idle");
    setErrorMsg("");
    setVideoTitle("");
    setSongTitle("");
    setArtistName("");
    setSkipped(false);
  };

  const handleSkipClick = () => {
    setSkipped(true);
    onSkip();
  };

  const handleUndoSkip = () => {
    setSkipped(false);
  };

  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100">
      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 bg-slate-800 rounded-xl flex items-center justify-center">
          <img src="/LOGO.png" alt="DropOperator" className="w-full h-full object-contain" />
        </div>

      </div>

      {/* Skipped state — planning without a song */}
      {skipped ? (
        <div className="flex flex-col gap-3">
          <div className="flex items-start gap-2 bg-slate-50 border border-slate-200 rounded-xl px-3 py-3">
            <div className="text-slate-500 mt-0.5 shrink-0"><CheckIcon /></div>
            <div>
              <p className="text-slate-700 text-sm font-medium">Planning without a song</p>
              <p className="text-slate-500 text-xs mt-0.5">Tell the assistant about your concert or campaign in the chat.</p>
            </div>
          </div>
          <button
            onClick={handleUndoSkip}
            className="text-slate-400 hover:text-slate-600 text-xs text-center transition-colors"
          >
            Add a song after all →
          </button>
        </div>
      ) : status === "success" ? (
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
                onChange={(e) => { 
                  setUrl(e.target.value); 
                  if (selectedFile) setSelectedFile(null); // Clear file if user types URL
                  if (status === "error") setStatus("idle"); 
                }}
                onKeyDown={handleKeyDown}
                placeholder="Paste YouTube URL here"
                disabled={status === "loading"}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 pr-10 text-sm text-slate-700 placeholder-slate-400 outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-100 transition-all disabled:opacity-50"
              />
              <button
                onClick={handleAnalyze}
                disabled={(!url.trim() && !selectedFile) || status === "loading"}
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
                <span className="ml-1">
                  {selectedFile ? "Uploading and transcribing audio..." : "Fetching transcript, this may take 30s..."}
                </span>
              </p>
            )}

            {/* Error message */}
            {status === "error" && (
              <p className="text-red-400 text-xs mt-2">{errorMsg}</p>
            )}
          </div>

          {/* Audio File Upload */}
          <div className="mb-4">
            <p className="text-slate-600 text-sm font-medium mb-2">Or Upload Audio File</p>
            <input
              type="file"
              ref={fileInputRef}
              accept=".mp3,.wav"
              disabled={status === "loading"}
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setSelectedFile(e.target.files[0]);
                  setUrl(""); // Clear URL field if user selects file
                  if (status === "error") setStatus("idle");
                }
              }}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={status === "loading"}
              className="w-full bg-slate-50 border border-dashed border-slate-300 rounded-xl px-4 py-2.5 text-xs text-slate-600 hover:bg-slate-100/50 transition-colors truncate"
            >
              {selectedFile ? `🎵 Selected: ${selectedFile.name}` : "Choose MP3 or WAV file..."}
            </button>
            {selectedFile && (
              <button
                type="button"
                onClick={() => setSelectedFile(null)}
                className="text-rose-400 hover:text-rose-600 text-[10px] mt-1 block text-right w-full"
              >
                Clear file
              </button>
            )}
          </div>

          {/* Optional metadata */}
          <div className="mb-4 flex flex-col gap-2">
            <input
              type="text"
              value={songTitle}
              onChange={(e) => setSongTitle(e.target.value)}
              placeholder="Song name (optional)"
              disabled={status === "loading"}
              className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-700 placeholder-slate-400 outline-none focus:border-slate-400 transition-all disabled:opacity-50"
            />
            <input
              type="text"
              value={artistName}
              onChange={(e) => setArtistName(e.target.value)}
              placeholder="Artist (optional)"
              disabled={status === "loading"}
              className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-700 placeholder-slate-400 outline-none focus:border-slate-400 transition-all disabled:opacity-50"
            />
          </div>

          {/* Analyze button */}
          <button
            onClick={handleAnalyze}
            disabled={(!url.trim() && !selectedFile) || status === "loading"}
            className="w-full bg-slate-800 hover:bg-slate-700 disabled:bg-slate-300 text-white text-sm font-medium py-2.5 rounded-xl transition-colors"
          >
            {status === "loading" ? "Analyzing..." : "Analyze Song"}
          </button>

          {/* Skip — plan without a song */}
          {status !== "loading" && (
            <button
              type="button"
              onClick={handleSkipClick}
              className="w-full text-slate-400 hover:text-slate-600 text-xs text-center mt-3 transition-colors"
            >
              Skip — plan a concert or campaign without a song →
            </button>
          )}
        </>
      )}
    </div>
  );
}
