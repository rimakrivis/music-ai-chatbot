const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface AnalyzeResponse {
  video_id: string;
  title: string;
  channel: string;
  duration: number;
  transcript_text: string;
  word_count: number;
  source: string;
  chunks_created: number;
  namespace: string;
  audio_features?: Record<string, unknown>;
  status: string;
}

export interface ChatResponse {
  response: string;
  tools_used: string[];
  session_id: string;
  calendar_events?: { title: string; date: string; type: string }[];
  todo_items?: { title: string; due_date: string | null }[];
}

export interface TranscriptResponse {
  transcript_text: string;
  word_count: number;
}

export interface AnalyzeLyricsResponse {
  status: string;
  [key: string]: unknown;
}

export async function analyzeVideo(youtube_url: string): Promise<AnalyzeResponse> {
  console.log("[api] analyzeVideo →", youtube_url);
  const res = await fetch(`${API_URL}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ youtube_url }),
  });
  if (!res.ok) {
    const err = await res.text();
    console.error("[api] analyzeVideo failed:", err);
    throw new Error(`Analyze failed: ${res.status} — ${err}`);
  }
  const data: AnalyzeResponse = await res.json();

  if (data.audio_features && Object.keys(data.audio_features).length > 0) {
    localStorage.setItem(
      `audio_features_${data.video_id}`,
      JSON.stringify(data.audio_features)
    );
    console.log("[api] analyzeVideo — audio_features saved:", data.audio_features);
  } else {
    console.log("[api] analyzeVideo — no audio_features (yt-dlp blocked or librosa failed)");
  }

  console.log("[api] analyzeVideo ✓", data);
  return data;
}

export async function sendMessage(
  video_id: string,
  message: string,
  session_id: string,
  video_title: string,
  video_channel: string = "",
  audio_features?: Record<string, unknown>,
  projectType?: string | null,
  band_id?: string | null,
  project_id?: number | null
): Promise<ChatResponse> {
  console.log("[api] sendMessage →", { video_id, message, session_id, projectType, band_id, project_id });
  if (audio_features) {
    console.log("[api] sendMessage — audio_features included:", audio_features);
  }
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      video_id,
      message,
      session_id,
      video_title,
      video_channel,
      audio_features: audio_features ?? null,  // ← was missing before
      project_type: projectType ?? null,
      band_id: band_id ?? null,
      project_id: project_id ?? null,  // ← NEW: specific project instance for memory isolation
    }),
  });
  if (!res.ok) {
    const err = await res.text();
    console.error("[api] sendMessage failed:", err);
    throw new Error(`Chat failed: ${res.status} — ${err}`);
  }
  const data = await res.json();
  console.log("[api] sendMessage ✓", data);
  return data;
}

export interface Project {
  id: number;
  band_id: string;
  project_type: string;
  details: Record<string, unknown>;
  created_at: string;
}

export async function createProject(band_id: string, project_type: string): Promise<Project> {
  console.log("[api] createProject →", { band_id, project_type });
  const res = await fetch(`${API_URL}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ band_id, project_type }),
  });
  if (!res.ok) {
    const err = await res.text();
    console.error("[api] createProject failed:", err);
    throw new Error(`Create project failed: ${res.status} — ${err}`);
  }
  const data = await res.json();
  console.log("[api] createProject ✓", data.project);
  return data.project;
}

export async function updateProjectDetails(
  project_id: number,
  details: Record<string, unknown>
): Promise<void> {
  console.log("[api] updateProjectDetails →", { project_id, details });
  const res = await fetch(`${API_URL}/projects/${project_id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ details }),
  });
  if (!res.ok) {
    const err = await res.text();
    console.error("[api] updateProjectDetails failed:", err);
    throw new Error(`Update project details failed: ${res.status} — ${err}`);
  }
  console.log("[api] updateProjectDetails ✓");
}

export async function getTranscript(video_id: string): Promise<TranscriptResponse> {
  console.log("[api] getTranscript →", video_id);
  const res = await fetch(`${API_URL}/transcript/${video_id}`);
  if (!res.ok) {
    const err = await res.text();
    console.error("[api] getTranscript failed:", err);
    throw new Error(`Transcript fetch failed: ${res.status} — ${err}`);
  }
  const data = await res.json();
  console.log("[api] getTranscript ✓", { word_count: data.word_count });
  return data;
}

export async function analyzeLyrics(
  video_id: string,
  lyrics_text: string,
  title: string,
  artist: string
): Promise<AnalyzeLyricsResponse> {
  console.log("[api] analyzeLyrics →", { video_id, title, artist });
  const res = await fetch(`${API_URL}/analyze-lyrics`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ video_id, lyrics_text, title, artist }),
  });
  if (!res.ok) {
    const err = await res.text();
    console.error("[api] analyzeLyrics failed:", err);
    throw new Error(`Lyrics analyze failed: ${res.status} — ${err}`);
  }
  const data = await res.json();
  console.log("[api] analyzeLyrics ✓", data);
  return data;
}

export async function analyzeAudioFile(
  file: File,
  sessionId: string,
  title: string,
  artist: string
): Promise<AnalyzeResponse> {
  console.log("[api] analyzeAudioFile →", { filename: file.name, title, artist });
  const formData = new FormData();
  formData.append("file", file);
  formData.append("session_id", sessionId);
  formData.append("title", title);
  formData.append("artist", artist);

  const response = await fetch(`${API_URL}/analyze-audio`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData.detail || "Audio analysis failed");
  }

  const data: AnalyzeResponse = await response.json();

  // Save audio_features to localStorage so the chat page can pass them to the agent
  if (data.audio_features && Object.keys(data.audio_features).length > 0) {
    localStorage.setItem(
      `audio_features_${data.video_id}`,
      JSON.stringify(data.audio_features)
    );
    console.log("[api] analyzeAudioFile — audio_features saved to localStorage:", data.audio_features);
  } else {
    console.log("[api] analyzeAudioFile — no audio_features in response (librosa may have failed)");
  }

  console.log("[api] analyzeAudioFile ✓", { video_id: data.video_id, chunks: data.chunks_created });
  return data;
}
export async function deleteCalendarEvent(eventId: number): Promise<void> {
  const res = await fetch(`${API_URL}/calendar/events/${eventId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
}

export async function rescheduleCalendarEvent(eventId: number, newDate: string): Promise<void> {
  const res = await fetch(`${API_URL}/calendar/events/${eventId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ date: newDate }),
  });
  if (!res.ok) throw new Error(`Reschedule failed: ${res.status}`);
}
