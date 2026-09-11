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

function IconSingle({ active }: { active: boolean }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={active ? "#ffffff" : "#475569"} strokeWidth="1.5">
      <circle cx="6" cy="18" r="2.5" />
      <path d="M8.5 18V5.5L20 3.5V16" />
      <circle cx="17.5" cy="16" r="2.5" />
    </svg>
  );
}

function IconAlbum({ active }: { active: boolean }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={active ? "#ffffff" : "#475569"} strokeWidth="1.5">
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="12" r="2.5" />
    </svg>
  );
}

function IconConcert({ active }: { active: boolean }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={active ? "#ffffff" : "#475569"} strokeWidth="1.5">
      <rect x="9" y="2.5" width="6" height="10" rx="3" />
      <path d="M6 11a6 6 0 0 0 12 0" />
      <path d="M12 17v4.5" />
      <path d="M9 21.5h6" />
    </svg>
  );
}

function IconSocial({ active }: { active: boolean }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={active ? "#ffffff" : "#475569"} strokeWidth="1.5">
      <circle cx="5" cy="12" r="2.5" />
      <circle cx="18" cy="6" r="2.5" />
      <circle cx="18" cy="18" r="2.5" />
      <path d="M7.3 10.8 15.7 7M7.3 13.2l8.4 3.8" />
    </svg>
  );
}

function IconOther({ active }: { active: boolean }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={active ? "#ffffff" : "#475569"} strokeWidth="1.5">
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M17.5 17.5 15 15M6 18l2.5-2.5M17.5 6.5 15 9" />
    </svg>
  );
}

const PROJECT_TYPES: { id: ProjectType; label: string; Icon: typeof IconSingle }[] = [
  { id: "single_release", label: "Single Release", Icon: IconSingle },
  { id: "album_release", label: "Album Release", Icon: IconAlbum },
  { id: "concert", label: "Concert", Icon: IconConcert },
  { id: "social_campaign", label: "Social Campaign", Icon: IconSocial },
  { id: "other", label: "Other", Icon: IconOther },
];

export default function ProjectTypeSelector({ activeType, onSelect }: ProjectTypeSelectorProps) {
  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100">
      <p className="text-slate-600 text-sm font-medium mb-3">What are you planning?</p>
      <div className="grid grid-cols-2 gap-2">
        {PROJECT_TYPES.map((pt) => {
          const active = activeType === pt.id;
          return (
            <button
              key={pt.id}
              type="button"
              onClick={() => onSelect(pt.id)}
              className={`flex flex-col items-center justify-center gap-1.5 rounded-xl px-3 py-3 text-xs font-medium transition-colors border ${
                active
                  ? "bg-slate-800 text-white border-slate-800"
                  : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
              }`}
            >
              <pt.Icon active={active} />
              {pt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
