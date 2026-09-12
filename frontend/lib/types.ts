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

// --- Band Profile (Artist Questionnaire) -----------------------------------
// Mirrors the JSONB shape documented in backend/migration_band_profile.sql.
// The whole object is always read/written together — no partial updates —
// since it's small, bounded, and injected in full into the agent prompt.

export interface BandProfileBasicInfo {
  artist_name: string;
  primary_genre: string;
  sub_genres: string[];
  home_country: string;
  main_markets: string[];
  languages: string[];
  bio: string;
  brand_voice: string[];
  social_handles: { instagram: string; tiktok: string; spotify: string; youtube: string };
  content_restrictions: string;
}

export interface BandProfileAudiencePlatform {
  spotify_monthly_listeners: number | null;
  spotify_followers: number | null;
  instagram_followers: number | null;
  tiktok_followers: number | null;
  youtube_subscribers: number | null;
  email_list_size: number | null;
  unknown_metrics: string[];
  age_range: [number, number];
  top_cities: string[];
}

export interface BandProfileLiveShow {
  city: string;
  attendance: number | null;
  venue_size: string;
}

export interface BandProfileCareerStage {
  stage: "emerging" | "mid_level" | "established" | "";
  previous_releases_count: number | null;
  best_release_performance: string;
  live_shows: BandProfileLiveShow[];
  has_manager: boolean;
  has_booking_agent: boolean;
  has_label: boolean;
  label_name: string;
  has_pr: boolean;
  release_cadence: string;
  comparable_artists: string[];
}

export interface BandProfileStrengthsWeaknesses {
  what_works: string[];
  what_works_other: string;
  what_weak: string[];
  what_weak_other: string;
  promotion_styles: string[];
  promotion_styles_other: string;
}

export interface BandProfilePracticalPreferences {
  venue_size: string;
  ticket_price_min: number | null;
  ticket_price_max: number | null;
  budget_level: "low" | "medium" | "high" | "";
  promo_lead_time: string;
  has_content_assets: boolean | null;
  content_assets_notes: string;
  sells_merch: boolean | null;
  merch_type: string;
  timezone: string;
}

export interface BandProfileGoals {
  main_goals: string[];
  main_goals_other: string;
  success_definition: string;
  known_upcoming_dates: { label: string; date: string }[];
  no_dates_set: boolean;
}

export interface BandProfile {
  basic_info: BandProfileBasicInfo;
  audience_platform: BandProfileAudiencePlatform;
  career_stage: BandProfileCareerStage;
  strengths_weaknesses: BandProfileStrengthsWeaknesses;
  practical_preferences: BandProfilePracticalPreferences;
  goals: BandProfileGoals;
}

export type BandProfileStatus = "empty" | "draft" | "complete";

export const EMPTY_BAND_PROFILE: BandProfile = {
  basic_info: {
    artist_name: "", primary_genre: "", sub_genres: [], home_country: "",
    main_markets: [], languages: [], bio: "", brand_voice: [],
    social_handles: { instagram: "", tiktok: "", spotify: "", youtube: "" },
    content_restrictions: "",
  },
  audience_platform: {
    spotify_monthly_listeners: null, spotify_followers: null, instagram_followers: null,
    tiktok_followers: null, youtube_subscribers: null, email_list_size: null,
    unknown_metrics: [], age_range: [18, 34], top_cities: [],
  },
  career_stage: {
    stage: "", previous_releases_count: null, best_release_performance: "",
    live_shows: [], has_manager: false, has_booking_agent: false,
    has_label: false, label_name: "", has_pr: false,
    release_cadence: "", comparable_artists: [],
  },
  strengths_weaknesses: {
    what_works: [], what_works_other: "", what_weak: [], what_weak_other: "",
    promotion_styles: [], promotion_styles_other: "",
  },
  practical_preferences: {
    venue_size: "", ticket_price_min: null, ticket_price_max: null,
    budget_level: "", promo_lead_time: "", has_content_assets: null,
    content_assets_notes: "", sells_merch: null, merch_type: "", timezone: "",
  },
  goals: {
    main_goals: [], main_goals_other: "", success_definition: "",
    known_upcoming_dates: [], no_dates_set: false,
  },
};

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