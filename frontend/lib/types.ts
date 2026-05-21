export interface CalendarEvent {
  id: number;
  title: string;
  description?: string;
  date: string;
  type: "release" | "spotify" | "youtube" | "social_media" | "promo" | "deadline" | "general";
  completed?: boolean;
  savedContent?: string;
  linkedTodoId?: number;
}

export interface TodoItem {
  id: number;
  title: string;
  completed: boolean;
  linkedEventId?: number;
}

export interface ExtractedTasks {
  calendar_events: { title: string; date: string; type: string }[];
  todo_items: { title: string; due_date: string | null }[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  tasks?: ExtractedTasks;
  tasksConfirmed?: boolean;
}

export interface DotDate {
  date: number;
  color: string;
}

export const EVENT_COLORS: Record<string, { bg: string; icon: string; label: string; completedBg: string }> = {
  release: {
    bg: "bg-purple-100/80",
    icon: "text-purple-600",
    label: "Release",
    completedBg: "bg-purple-50/50",
  },
  spotify: {
    bg: "bg-green-100/80",
    icon: "text-green-600",
    label: "Spotify",
    completedBg: "bg-green-50/50",
  },
  youtube: {
    bg: "bg-red-100/80",
    icon: "text-red-600",
    label: "YouTube",
    completedBg: "bg-red-50/50",
  },
  social_media: {
    bg: "bg-blue-100/80",
    icon: "text-blue-600",
    label: "Social Media",
    completedBg: "bg-blue-50/50",
  },
  promo: {
    bg: "bg-orange-100/80",
    icon: "text-orange-600",
    label: "Promo",
    completedBg: "bg-orange-50/50",
  },
  deadline: {
    bg: "bg-rose-100/80",
    icon: "text-rose-600",
    label: "Deadline",
    completedBg: "bg-rose-50/50",
  },
  general: {
    bg: "bg-slate-100/80",
    icon: "text-slate-600",
    label: "General",
    completedBg: "bg-slate-50/50",
  },
};