export interface CalendarEvent {
  id: number;
  title: string;
  description?: string;
  date: string;
  type: "release" | "spotify" | "youtube" | "social_media" | "promo" | "deadline" | "general";
}

export interface TodoItem {
  id: number;
  title: string;
  completed: boolean;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface DotDate {
  date: number;
  color: string;
}

export const EVENT_COLORS: Record<string, { bg: string; icon: string; label: string }> = {
  release: {
    bg: "bg-purple-100/80",
    icon: "text-purple-600",
    label: "Soft Purple",
  },
  spotify: {
    bg: "bg-green-100/80",
    icon: "text-green-600",
    label: "Soft Green",
  },
  youtube: {
    bg: "bg-red-100/80",
    icon: "text-red-600",
    label: "Soft Red",
  },
  social_media: {
    bg: "bg-blue-100/80",
    icon: "text-blue-600",
    label: "Soft Blue",
  },
  promo: {
    bg: "bg-orange-100/80",
    icon: "text-orange-600",
    label: "Soft Orange",
  },
  deadline: {
    bg: "bg-rose-100/80",
    icon: "text-rose-600",
    label: "Soft Rose",
  },
  general: {
    bg: "bg-slate-100/80",
    icon: "text-slate-600",
    label: "Soft Slate",
  },
};
