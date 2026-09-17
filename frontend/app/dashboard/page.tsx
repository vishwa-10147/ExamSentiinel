"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import Sidebar from "@/components/Sidebar";
import {
  ShieldCheck,
  Users,
  CheckCircle2,
  AlertTriangle,
  Activity,
  ArrowUpRight,
  RefreshCw,
  Plus,
  Eye,
  TrendingUp,
  Clock,
  Loader2,
  FileText,
  BarChart3,
  Zap,
  BookOpen,
} from "lucide-react";

interface DashboardStats {
  active_exams: number;
  total_active_sessions: number;
  in_progress_sessions: number;
  submitted_sessions: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  average_risk_score: number;
}

interface Exam {
  id: string;
  title: string;
  status: string;
  duration_minutes: number;
  start_window: string;
  end_window: string;
  total_marks: number;
}

interface ActiveSession {
  session_id: string;
  candidate_name: string;
  candidate_email: string;
  exam_title: string;
  exam_id: string;
  status: string;
  current_risk_score: number;
  risk_level: string;
  started_at: string;
}

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  accent,
  loading,
}: {
  label: string;
  value: string | number;
  sub: string;
  icon: React.ElementType;
  accent: string;
  loading: boolean;
}) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</span>
        <div className={`flex h-9 w-9 items-center justify-center rounded-xl ${accent}`}>
          <Icon className="h-4 w-4 text-white" />
        </div>
      </div>
      {loading ? (
        <div className="mt-3 h-8 w-16 animate-pulse rounded-lg bg-slate-100" />
      ) : (
        <p className="mt-3 text-3xl font-bold text-slate-900">{value}</p>
      )}
      <p className="mt-1 text-xs text-slate-400">{sub}</p>
    </div>
  );
}

function RiskBadge({ level }: { level: string }) {
  const styles: Record<string, string> = {
    CRITICAL: "bg-red-100 text-red-700 border-red-200",
    HIGH: "bg-orange-100 text-orange-700 border-orange-200",
    MEDIUM: "bg-amber-100 text-amber-700 border-amber-200",
    LOW: "bg-emerald-100 text-emerald-700 border-emerald-200",
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${styles[level] || styles["LOW"]}`}>
      {level}
    </span>
  );
}

function ExamStatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    PUBLISHED: "bg-blue-100 text-blue-700",
    DRAFT: "bg-slate-100 text-slate-600",
    ARCHIVED: "bg-stone-100 text-stone-600",
    LIVE: "bg-emerald-100 text-emerald-700",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${styles[status] || "bg-slate-100 text-slate-600"}`}>
      {status}
    </span>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [exams, setExams] = useState<Exam[]>([]);
  const [activeSessions, setActiveSessions] = useState<ActiveSession[]>([]);
  const [statsLoading, setStatsLoading] = useState(true);
  const [examsLoading, setExamsLoading] = useState(true);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.push("/auth/login");
  }, [isLoading, isAuthenticated, router]);

  const fetchStats = useCallback(async () => {
    if (!user || !["admin", "proctor"].includes(user.role)) {
      setStatsLoading(false);
      return;
    }
    try {
      const data = await apiClient.get<DashboardStats>("/api/dashboard/stats");
      setStats(data);
    } catch {
      // Keep previous data on error
    } finally {
      setStatsLoading(false);
    }
  }, [user]);

  const fetchExams = useCallback(async () => {
    if (!user) return;
    try {
      const data = await apiClient.get<{ exams: Exam[]; total: number }>("/api/exams?limit=5&offset=0");
      setExams(data.exams ?? []);
    } catch {
      setExams([]);
    } finally {
      setExamsLoading(false);
    }
  }, [user]);

  const fetchActiveSessions = useCallback(async () => {
    if (!user || !["admin", "proctor"].includes(user.role)) {
      setSessionsLoading(false);
      return;
    }
    try {
      const data = await apiClient.get<ActiveSession[]>("/api/dashboard/active-sessions?limit=8&sort_by=risk_score");
      setActiveSessions(Array.isArray(data) ? data : []);
    } catch {
      setActiveSessions([]);
    } finally {
      setSessionsLoading(false);
    }
  }, [user]);

  const refreshAll = useCallback(() => {
    setStatsLoading(true);
    setLastRefreshed(new Date());
    void fetchStats();
    void fetchExams();
    void fetchActiveSessions();
  }, [fetchStats, fetchExams, fetchActiveSessions]);

  useEffect(() => {
    if (!isLoading && user) {
      void fetchStats();
      void fetchExams();
      void fetchActiveSessions();
    }
  }, [isLoading, user, fetchStats, fetchExams, fetchActiveSessions]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(refreshAll, 30000);
    return () => clearInterval(interval);
  }, [refreshAll]);

  if (isLoading || !isAuthenticated || !user) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  const isAdmin = user.role === "admin";
  const isProctor = user.role === "proctor";
  const isReviewer = user.role === "reviewer";
  const isCandidate = user.role === "candidate";

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <div className="flex-1 overflow-auto">
        {/* Header */}
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white/80 backdrop-blur px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-slate-900">
                {isAdmin && "Admin Dashboard"}
                {isProctor && "Proctoring Center"}
                {isReviewer && "Review Center"}
                {isCandidate && "My Exam Portal"}
              </h1>
              <p className="text-sm text-slate-500 mt-0.5">
                Welcome back, <span className="font-medium text-slate-700">{user.full_name}</span>
                <span className="ml-2 inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700 capitalize">{user.role}</span>
              </p>
            </div>
            <div className="flex items-center gap-3">
              {(isAdmin || isProctor) && (
                <div className="text-right">
                  <p className="text-xs text-slate-400">Last refreshed</p>
                  <p className="text-xs font-medium text-slate-600">
                    {lastRefreshed.toLocaleTimeString()}
                  </p>
                </div>
              )}
              <button
                onClick={refreshAll}
                className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 transition-colors"
              >
                <RefreshCw className="h-4 w-4" />
                Refresh
              </button>
              {isAdmin && (
                <Link
                  href="/admin/exam/builder"
                  className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 transition-colors shadow-sm"
                >
                  <Plus className="h-4 w-4" />
                  New Exam
                </Link>
              )}
            </div>
          </div>
        </div>

        <div className="px-8 py-6 space-y-8">

          {/* ── ADMIN & PROCTOR VIEW ── */}
          {(isAdmin || isProctor) && (
            <>
              {/* Stats Grid */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <StatCard
                  label="Active Exams"
                  value={stats?.active_exams ?? 0}
                  sub="Running right now"
                  icon={Zap}
                  accent="bg-blue-600"
                  loading={statsLoading}
                />
                <StatCard
                  label="Live Students"
                  value={stats?.total_active_sessions ?? 0}
                  sub={`${stats?.in_progress_sessions ?? 0} in progress`}
                  icon={Users}
                  accent="bg-violet-600"
                  loading={statsLoading}
                />
                <StatCard
                  label="Flagged Sessions"
                  value={stats ? stats.high_risk_count + stats.medium_risk_count : 0}
                  sub={`${stats?.high_risk_count ?? 0} critical · ${stats?.medium_risk_count ?? 0} medium`}
                  icon={AlertTriangle}
                  accent="bg-amber-500"
                  loading={statsLoading}
                />
                <StatCard
                  label="Completed Today"
                  value={stats?.submitted_sessions ?? 0}
                  sub={`Avg risk: ${((stats?.average_risk_score ?? 0) * 100).toFixed(1)}%`}
                  icon={CheckCircle2}
                  accent="bg-emerald-600"
                  loading={statsLoading}
                />
              </div>

              {/* Risk Distribution Bar */}
              {stats && (stats.total_active_sessions > 0) && (
                <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                      <BarChart3 className="h-4 w-4 text-blue-600" />
                      Risk Distribution — Live Sessions
                    </h2>
                    <span className="text-xs text-slate-500">{stats.total_active_sessions} total</span>
                  </div>
                  <div className="flex h-4 w-full overflow-hidden rounded-full gap-0.5">
                    {stats.high_risk_count > 0 && (
                      <div
                        style={{ width: `${(stats.high_risk_count / stats.total_active_sessions) * 100}%` }}
                        className="bg-red-500 rounded-l-full"
                        title={`High: ${stats.high_risk_count}`}
                      />
                    )}
                    {stats.medium_risk_count > 0 && (
                      <div
                        style={{ width: `${(stats.medium_risk_count / stats.total_active_sessions) * 100}%` }}
                        className="bg-amber-400"
                        title={`Medium: ${stats.medium_risk_count}`}
                      />
                    )}
                    {stats.low_risk_count > 0 && (
                      <div
                        style={{ width: `${(stats.low_risk_count / stats.total_active_sessions) * 100}%` }}
                        className="bg-emerald-400 rounded-r-full"
                        title={`Low: ${stats.low_risk_count}`}
                      />
                    )}
                  </div>
                  <div className="mt-2 flex gap-4 text-xs text-slate-500">
                    <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-red-500" />High ({stats.high_risk_count})</span>
                    <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-amber-400" />Medium ({stats.medium_risk_count})</span>
                    <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-400" />Low ({stats.low_risk_count})</span>
                  </div>
                </div>
              )}

              {/* Active Sessions Table */}
              <div className="rounded-2xl border border-slate-100 bg-white shadow-sm">
                <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
                  <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <Activity className="h-4 w-4 text-blue-600 animate-pulse" />
                    Live Active Sessions
                  </h2>
                  <Link href="/dashboard/live" className="flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-500 transition-colors">
                    View All <ArrowUpRight className="h-3.5 w-3.5" />
                  </Link>
                </div>

                {sessionsLoading ? (
                  <div className="space-y-3 p-6">
                    {[...Array(4)].map((_, i) => (
                      <div key={i} className="h-12 w-full animate-pulse rounded-lg bg-slate-100" />
                    ))}
                  </div>
                ) : activeSessions.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-14 text-slate-400">
                    <ShieldCheck className="h-10 w-10 mb-3 text-slate-300" />
                    <p className="text-sm font-medium">No active sessions right now</p>
                    <p className="text-xs mt-1">Sessions will appear here once candidates start an exam</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-slate-100 bg-slate-50/60 text-xs font-semibold uppercase tracking-wider text-slate-500">
                          <th className="px-6 py-3 text-left">Candidate</th>
                          <th className="px-6 py-3 text-left">Exam</th>
                          <th className="px-6 py-3 text-left">Risk Score</th>
                          <th className="px-6 py-3 text-left">Risk Level</th>
                          <th className="px-6 py-3 text-left">Started</th>
                          <th className="px-6 py-3 text-left">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {activeSessions.map((session) => (
                          <tr key={session.session_id} className="hover:bg-slate-50/60 transition-colors">
                            <td className="px-6 py-3.5">
                              <div>
                                <p className="font-medium text-slate-900">{session.candidate_name || "—"}</p>
                                <p className="text-xs text-slate-400">{session.candidate_email || ""}</p>
                              </div>
                            </td>
                            <td className="px-6 py-3.5">
                              <p className="text-slate-700 font-medium truncate max-w-[180px]">{session.exam_title}</p>
                            </td>
                            <td className="px-6 py-3.5">
                              <div className="flex items-center gap-2">
                                <div className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-100">
                                  <div
                                    className={`h-full rounded-full transition-all ${
                                      session.current_risk_score >= 60 ? "bg-red-500" :
                                      session.current_risk_score >= 30 ? "bg-amber-400" : "bg-emerald-400"
                                    }`}
                                    style={{ width: `${Math.min(session.current_risk_score, 100)}%` }}
                                  />
                                </div>
                                <span className="text-xs font-mono text-slate-500">
                                  {session.current_risk_score.toFixed(1)}
                                </span>
                              </div>
                            </td>
                            <td className="px-6 py-3.5">
                              <RiskBadge level={session.risk_level || "LOW"} />
                            </td>
                            <td className="px-6 py-3.5 text-xs text-slate-400">
                              {session.started_at
                                ? new Date(session.started_at).toLocaleTimeString()
                                : "—"}
                            </td>
                            <td className="px-6 py-3.5">
                              <Link
                                href={`/admin/exam/${session.exam_id}/manage`}
                                className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 hover:border-blue-400 hover:text-blue-600 transition-colors"
                              >
                                <Eye className="h-3 w-3" /> Monitor
                              </Link>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Recent Exams + Quick Actions Row */}
              <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                {/* Recent Exams */}
                <div className="xl:col-span-2 rounded-2xl border border-slate-100 bg-white shadow-sm">
                  <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
                    <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                      <BookOpen className="h-4 w-4 text-blue-600" />
                      Recent Exams
                    </h2>
                    <Link href="/admin/exam" className="flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-500 transition-colors">
                      View All <ArrowUpRight className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                  {examsLoading ? (
                    <div className="space-y-3 p-6">
                      {[...Array(4)].map((_, i) => (
                        <div key={i} className="h-14 w-full animate-pulse rounded-lg bg-slate-100" />
                      ))}
                    </div>
                  ) : exams.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 text-slate-400">
                      <FileText className="h-8 w-8 mb-2 text-slate-300" />
                      <p className="text-sm font-medium">No exams yet</p>
                      {isAdmin && (
                        <Link href="/admin/exam/builder" className="mt-3 text-xs font-semibold text-blue-600 hover:underline">
                          Create your first exam →
                        </Link>
                      )}
                    </div>
                  ) : (
                    <div className="divide-y divide-slate-100">
                      {exams.map((exam) => (
                        <div key={exam.id} className="flex items-center justify-between px-6 py-4 hover:bg-slate-50/60 transition-colors">
                          <div className="flex-1 min-w-0">
                            <p className="font-semibold text-slate-900 text-sm truncate">{exam.title}</p>
                            <p className="text-xs text-slate-400 mt-0.5">
                              {exam.duration_minutes}min · {exam.total_marks} marks ·{" "}
                              {exam.start_window
                                ? new Date(exam.start_window).toLocaleDateString()
                                : "No date set"}
                            </p>
                          </div>
                          <div className="flex items-center gap-3 ml-4">
                            <ExamStatusBadge status={exam.status} />
                            <Link
                              href={`/admin/exam/${exam.id}/manage`}
                              className="rounded-lg border border-slate-200 p-1.5 hover:border-blue-400 hover:text-blue-600 transition-colors"
                            >
                              <ArrowUpRight className="h-3.5 w-3.5" />
                            </Link>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Quick Actions */}
                <div className="rounded-2xl border border-slate-100 bg-white shadow-sm">
                  <div className="border-b border-slate-100 px-6 py-4">
                    <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-blue-600" />
                      Quick Actions
                    </h2>
                  </div>
                  <div className="p-4 space-y-2">
                    {isAdmin && (
                      <>
                        <Link href="/admin/exam/builder" className="flex items-center justify-between rounded-xl border border-slate-100 p-4 hover:border-blue-400 hover:bg-blue-50/40 transition group">
                          <div>
                            <p className="font-semibold text-slate-800 text-sm">Create Exam</p>
                            <p className="text-xs text-slate-400 mt-0.5">Questions, schedule & proctoring</p>
                          </div>
                          <ArrowUpRight className="h-4 w-4 text-slate-300 group-hover:text-blue-500 transition-colors" />
                        </Link>
                        <Link href="/admin/users" className="flex items-center justify-between rounded-xl border border-slate-100 p-4 hover:border-blue-400 hover:bg-blue-50/40 transition group">
                          <div>
                            <p className="font-semibold text-slate-800 text-sm">Manage Users</p>
                            <p className="text-xs text-slate-400 mt-0.5">Roles, access & registration</p>
                          </div>
                          <ArrowUpRight className="h-4 w-4 text-slate-300 group-hover:text-blue-500 transition-colors" />
                        </Link>
                        <Link href="/admin/settings" className="flex items-center justify-between rounded-xl border border-slate-100 p-4 hover:border-blue-400 hover:bg-blue-50/40 transition group">
                          <div>
                            <p className="font-semibold text-slate-800 text-sm">Risk Weights</p>
                            <p className="text-xs text-slate-400 mt-0.5">Calibrate AI risk engine</p>
                          </div>
                          <ArrowUpRight className="h-4 w-4 text-slate-300 group-hover:text-blue-500 transition-colors" />
                        </Link>
                      </>
                    )}
                    <Link href="/admin/review" className="flex items-center justify-between rounded-xl border border-slate-100 p-4 hover:border-amber-400 hover:bg-amber-50/40 transition group">
                      <div>
                        <p className="font-semibold text-slate-800 text-sm">Review Queue</p>
                        <p className="text-xs text-slate-400 mt-0.5">Adjudicate flagged signals</p>
                      </div>
                      <ArrowUpRight className="h-4 w-4 text-slate-300 group-hover:text-amber-500 transition-colors" />
                    </Link>
                    <Link href="/admin/appeals" className="flex items-center justify-between rounded-xl border border-slate-100 p-4 hover:border-blue-400 hover:bg-blue-50/40 transition group">
                      <div>
                        <p className="font-semibold text-slate-800 text-sm">Appeals Center</p>
                        <p className="text-xs text-slate-400 mt-0.5">Manage candidate appeals</p>
                      </div>
                      <ArrowUpRight className="h-4 w-4 text-slate-300 group-hover:text-blue-500 transition-colors" />
                    </Link>
                    <Link href="/admin/audit" className="flex items-center justify-between rounded-xl border border-slate-100 p-4 hover:border-blue-400 hover:bg-blue-50/40 transition group">
                      <div>
                        <p className="font-semibold text-slate-800 text-sm">Audit Log</p>
                        <p className="text-xs text-slate-400 mt-0.5">System and reviewer activity</p>
                      </div>
                      <ArrowUpRight className="h-4 w-4 text-slate-300 group-hover:text-blue-500 transition-colors" />
                    </Link>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* ── REVIEWER VIEW ── */}
          {isReviewer && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Link href="/admin/review" className="group rounded-2xl border border-slate-100 bg-white p-6 shadow-sm hover:border-amber-400 hover:shadow-md transition">
                  <AlertTriangle className="h-7 w-7 text-amber-500 mb-3" />
                  <p className="font-bold text-slate-900">Review Queue</p>
                  <p className="text-xs text-slate-500 mt-1">Evaluate AI-flagged sessions with video snapshots</p>
                  <p className="mt-3 text-xs font-semibold text-amber-600 group-hover:underline flex items-center gap-1">Open Queue <ArrowUpRight className="h-3 w-3" /></p>
                </Link>
                <Link href="/admin/appeals" className="group rounded-2xl border border-slate-100 bg-white p-6 shadow-sm hover:border-blue-400 hover:shadow-md transition">
                  <FileText className="h-7 w-7 text-blue-500 mb-3" />
                  <p className="font-bold text-slate-900">Appeals Center</p>
                  <p className="text-xs text-slate-500 mt-1">Manage formal candidate objections</p>
                  <p className="mt-3 text-xs font-semibold text-blue-600 group-hover:underline flex items-center gap-1">Open Appeals <ArrowUpRight className="h-3 w-3" /></p>
                </Link>
                <Link href="/admin/audit" className="group rounded-2xl border border-slate-100 bg-white p-6 shadow-sm hover:border-slate-400 hover:shadow-md transition">
                  <Clock className="h-7 w-7 text-slate-500 mb-3" />
                  <p className="font-bold text-slate-900">Audit Trail</p>
                  <p className="text-xs text-slate-500 mt-1">Track all reviewer decisions</p>
                  <p className="mt-3 text-xs font-semibold text-slate-600 group-hover:underline flex items-center gap-1">View Audit <ArrowUpRight className="h-3 w-3" /></p>
                </Link>
              </div>
              <div className="rounded-2xl border border-amber-100 bg-amber-50/50 p-5 text-sm text-amber-800">
                <strong>Reviewer Reminder:</strong> Proctoring signals are AI-generated suggestions, not verdicts. You have full authority to dismiss, escalate, or record findings after reviewing the evidence.
              </div>
            </div>
          )}

          {/* ── CANDIDATE VIEW ── */}
          {isCandidate && (
            <div className="space-y-6">
              {/* Available Exams */}
              <div className="rounded-2xl border border-slate-100 bg-white shadow-sm">
                <div className="border-b border-slate-100 px-6 py-4">
                  <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <BookOpen className="h-4 w-4 text-blue-600" />
                    Available Exams
                  </h2>
                </div>
                {examsLoading ? (
                  <div className="space-y-3 p-6">
                    {[...Array(3)].map((_, i) => <div key={i} className="h-16 w-full animate-pulse rounded-lg bg-slate-100" />)}
                  </div>
                ) : exams.filter((e) => e.status === "PUBLISHED").length === 0 ? (
                  <div className="flex flex-col items-center py-12 text-slate-400">
                    <ShieldCheck className="h-10 w-10 mb-3 text-slate-300" />
                    <p className="text-sm font-medium">No exams scheduled for you</p>
                    <p className="text-xs mt-1">Check back later or contact your administrator</p>
                  </div>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {exams.filter((e) => e.status === "PUBLISHED").map((exam) => (
                      <div key={exam.id} className="flex items-center justify-between px-6 py-4 hover:bg-slate-50/60 transition-colors">
                        <div>
                          <p className="font-semibold text-slate-900 text-sm">{exam.title}</p>
                          <p className="text-xs text-slate-400 mt-0.5">
                            {exam.duration_minutes} minutes · {exam.total_marks} marks
                          </p>
                        </div>
                        <Link
                          href={`/exam/readiness?exam_id=${exam.id}`}
                          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-500 transition-colors"
                        >
                          Start Exam <ArrowUpRight className="h-3.5 w-3.5" />
                        </Link>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Readiness Check Card */}
              <div className="rounded-2xl border border-blue-100 bg-blue-50/50 p-6">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="font-bold text-slate-900">Pre-Exam System Readiness</h3>
                    <p className="text-sm text-slate-600 mt-1">Check webcam, microphone, and browser compatibility before you start</p>
                  </div>
                  <Link
                    href="/exam/readiness"
                    className="shrink-0 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 transition-colors shadow-sm"
                  >
                    Run System Check
                  </Link>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
