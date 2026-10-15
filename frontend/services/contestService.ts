import { apiClient } from "./apiClient";
import type { Difficulty, ProblemStatus, Verdict } from "./practiceService";

export type ContestPhase = "upcoming" | "running" | "ended";

export interface ContestSummary {
  id: string;
  slug: string;
  title: string;
  starts_at: string;
  ends_at: string;
  duration_minutes: number;
  phase: ContestPhase;
  problem_count: number;
  participants: number;
  registered: boolean;
  is_published: boolean;
}

export interface ContestProblem {
  label: string;
  slug: string;
  title: string;
  difficulty: Difficulty;
  points: number;
  status: ProblemStatus;
  solved_by: number;
}

export interface ContestDetail extends ContestSummary {
  description: string;
  penalty_minutes: number;
  server_time: string;
  problems: ContestProblem[];
}

export interface LeaderboardCell {
  label: string;
  solved: boolean;
  rejected: number;
  solved_at_minutes: number | null;
}

export interface LeaderboardRow {
  rank: number;
  user_id: string;
  name: string;
  score: number;
  solved: number;
  penalty_minutes: number;
  problems: LeaderboardCell[];
  is_me: boolean;
}

export interface ContestLeaderboard {
  contest_slug: string;
  phase: ContestPhase;
  labels: string[];
  rows: LeaderboardRow[];
}

export interface ContestSubmission {
  id: string;
  label: string;
  problem_slug: string;
  language: string;
  verdict: Verdict;
  passed_count: number;
  total_count: number;
  runtime_ms: number | null;
  created_at: string;
}

export interface ContestUpsert {
  slug: string;
  title: string;
  description: string;
  starts_at: string; // ISO 8601 with offset
  duration_minutes: number;
  penalty_minutes: number;
  is_published: boolean;
  problems: { problem_id: string; points: number }[];
}

export interface ContestAdmin extends Omit<ContestUpsert, "problems"> {
  id: string;
  ends_at: string;
  phase: ContestPhase;
  participants: number;
  problems: { problem_id: string; points: number; label: string; slug: string; title: string; difficulty: Difficulty; is_published: boolean }[];
}

const path = (slug: string) => `/api/contests/${encodeURIComponent(slug)}`;

class ContestService {
  list() {
    return apiClient.get<{ items: ContestSummary[]; server_time: string }>("/api/contests");
  }
  get(slug: string) {
    return apiClient.get<ContestDetail>(path(slug));
  }
  register(slug: string) {
    return apiClient.post<ContestSummary>(`${path(slug)}/register`, {});
  }
  leaderboard(slug: string) {
    return apiClient.get<ContestLeaderboard>(`${path(slug)}/leaderboard`);
  }
  submissions(slug: string) {
    return apiClient.get<ContestSubmission[]>(`${path(slug)}/submissions`);
  }

  // ---- Admin ----
  adminList() {
    return apiClient.get<ContestAdmin[]>("/api/admin/contests");
  }
  create(payload: ContestUpsert) {
    return apiClient.post<ContestAdmin>("/api/admin/contests", payload);
  }
  update(id: string, payload: ContestUpsert) {
    return apiClient.put<ContestAdmin>(`/api/admin/contests/${id}`, payload);
  }
  remove(id: string) {
    return apiClient.delete<void>(`/api/admin/contests/${id}`);
  }
}

export const contestService = new ContestService();

/** Milliseconds between the server clock and this browser's clock (server - local). */
export function clockSkew(serverTime: string): number {
  return new Date(serverTime).getTime() - Date.now();
}

/** "2d 03:04:05" / "03:04:05" for a positive number of milliseconds. */
export function formatCountdown(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const d = Math.floor(total / 86400);
  const h = Math.floor((total % 86400) / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const hms = [h, m, s].map((n) => String(n).padStart(2, "0")).join(":");
  return d > 0 ? `${d}d ${hms}` : hms;
}

export function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h && m ? `${h} h ${m} min` : h ? `${h} h` : `${m} min`;
}
