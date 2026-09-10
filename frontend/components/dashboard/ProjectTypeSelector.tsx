"use client";

export type ProjectType =
  | "single_release"
  | "album_release"
  | "concert"
  | "social_campaign"
  | "other";

interface ProjectTypeSelectorProps {
  activeType: ProjectType | null;
  onSelect: (type: ProjectType) => void;
}

const PROJECT_TYPES: { id: ProjectType; label: string; emoji: string }[] = [
  { id: "single_release", label: "Single Release", emoji: "🎵" },
  { id: "album_release", label: "Album Release", emoji: "💿" },
  { id: "concert", label: "Concert", emoji: "🎤" },
  { id: "social_campaign", label: "Social Campaign", emoji: "📱" },
  { id: "other", label: "Other", emoji: "✨" },
];

export default function ProjectTypeSelector({ activeType, onSelect }: ProjectTypeSelectorProps) {
  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100">
      <p className="text-slate-600 text-sm font-medium mb-3">What are you planning?</p>
      <div className="grid grid-cols-2 gap-2">
        {PROJECT_TYPES.map((pt) => (
          <button
            key={pt.id}
            type="button"
            onClick={() => onSelect(pt.id)}
            className={`flex flex-col items-center justify-center gap-1 rounded-xl px-3 py-3 text-xs font-medium transition-colors border ${
              activeType === pt.id
                ? "bg-slate-800 text-white border-slate-800"
                : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
            }`}
          >
            <span className="text-lg">{pt.emoji}</span>
            {pt.label}
          </button>
        ))}
      </div>
    </div>
  );
}
