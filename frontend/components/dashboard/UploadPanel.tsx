"use client";

// Inline SVG icons
const LinkIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
  </svg>
);

const VideoIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="6" width="20" height="12" rx="2" ry="2"/>
    <path d="m10 9 5 3-5 3z"/>
  </svg>
);

export default function UploadPanel() {
  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100">
      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 bg-slate-800 rounded-xl flex items-center justify-center">
          <span className="text-white text-lg">X</span>
        </div>
        <h3 className="text-slate-800 font-semibold text-lg">AI Music</h3>
      </div>

      {/* Upload YouTube URL */}
      <div className="mb-4">
        <p className="text-slate-600 text-sm font-medium mb-2">Upload YouTube URL</p>
        <div className="relative">
          <input
            type="text"
            placeholder="Paste URL"
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 pr-10 text-sm text-slate-700 placeholder-slate-400 outline-none focus:border-slate-300 focus:ring-2 focus:ring-slate-100 transition-all"
          />
          <button className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors">
            <LinkIcon />
          </button>
        </div>
      </div>

      {/* Upload Video */}
      <div>
        <p className="text-slate-600 text-sm font-medium mb-2">Upload Video</p>
        <div className="border-2 border-dashed border-slate-200 rounded-xl p-8 flex flex-col items-center justify-center gap-2 hover:border-slate-300 transition-colors cursor-pointer">
          <div className="w-12 h-12 bg-slate-100 rounded-xl flex items-center justify-center text-slate-400">
            <VideoIcon />
          </div>
          <p className="text-slate-400 text-sm">Drag and drop to here</p>
        </div>
      </div>
    </div>
  );
}
