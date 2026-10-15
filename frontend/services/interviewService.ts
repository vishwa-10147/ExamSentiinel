import { apiClient } from "./apiClient";

export interface TranscriptSegment {
  speaker: string;
  at: string;
  start: number;
  end: number;
  text: string;
}

export interface InterviewScore {
  id: string;
  criterion_scores: Record<string, number>;
  notes: string | null;
  created_at: string;
}

export interface InterviewDetail {
  id: string;
  status: "SCHEDULED" | "READY" | "LIVE" | "COMPLETED";
  mode: string;
  recording_consent: boolean;
  role: "candidate" | "interviewer";
  candidate_name: string | null;
  exam_title: string | null;
  segments: TranscriptSegment[];
  transcription_available: boolean;
  topics?: string[];
  coverage?: Record<string, boolean>;
  scores?: InterviewScore[];
}

export interface InterviewListItem {
  id: string;
  status: string;
  mode: string;
  recording_consent: boolean;
  candidate_name: string;
  candidate_email: string;
  exam_title: string;
  segments: number;
  created_at: string;
}

export const CONSENT_NOTICE_VERSION = "2026-10";

class InterviewService {
  create(examSessionId: string) {
    return apiClient.post<{ id: string; status: string }>("/api/interviews/sessions", {
      exam_session_id: examSessionId,
      mode: "LIVE",
    });
  }
  get(id: string) {
    return apiClient.get<InterviewDetail>(`/api/interviews/${id}`);
  }
  list() {
    return apiClient.get<InterviewListItem[]>("/api/interviews");
  }
  consent(id: string) {
    return apiClient.post(`/api/interviews/${id}/consent`, { consent: true, notice_version: CONSENT_NOTICE_VERSION });
  }
  setStatus(id: string, status: InterviewDetail["status"]) {
    return apiClient.post(`/api/interviews/${id}/status`, { status });
  }
  setTopics(id: string, topics: string[]) {
    return apiClient.put<{ topics: string[]; coverage: Record<string, boolean> }>(`/api/interviews/${id}/topics`, { topics });
  }
  uploadAudio(id: string, clip: Blob) {
    const form = new FormData();
    form.append("clip", clip, "clip.webm");
    return apiClient.upload<{ segments: TranscriptSegment[] }>(`/api/interviews/${id}/audio`, form);
  }
  score(id: string, criterion_scores: Record<string, number>, notes: string) {
    return apiClient.post(`/api/interviews/${id}/scores`, { criterion_scores, notes });
  }
}

export const interviewService = new InterviewService();

/** ws(s)://<api host>/api/ws/interview/<id> — authenticated by the httpOnly session cookie. */
export function signallingUrl(interviewId: string): string {
  const api = process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");
  const base = api ? new URL(api) : new URL(window.location.origin);
  const protocol = base.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${base.host}/api/ws/interview/${interviewId}`;
}

/** STUN by default; production should add a TURN server via NEXT_PUBLIC_ICE_SERVERS (JSON). */
export function iceServers(): RTCIceServer[] {
  try {
    const configured = process.env.NEXT_PUBLIC_ICE_SERVERS;
    if (configured) return JSON.parse(configured);
  } catch {
    /* fall through to the default */
  }
  return [{ urls: "stun:stun.l.google.com:19302" }];
}
