"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
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
  Mail,
  HelpCircle,
  Cpu,
  Sliders,
  Search,
  ChevronRight,
  Radio,
  History
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

interface ActivityItem {
  id: string;
  timestamp: string;
  action: string;
  user: string;
  role: string;
  ip_address: string;
  status: string;
  details?: string | null;
}

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  accent,
  loading,
  onClick,
}: {
  label: string;
  value: string | number;
  sub: string;
  icon: React.ElementType;
  accent: string;
  loading: boolean;
  onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className={`rounded-2xl border border-slate-100 bg-white p-5 shadow-sm hover:shadow-md transition-all ${
        onClick ? "cursor-pointer hover:border-blue-200" : ""
      }`}
    >
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
  const [recentActivities, setRecentActivities] = useState<ActivityItem[]>([]);
  
  const [statsLoading, setStatsLoading] = useState(true);
  const [examsLoading, setExamsLoading] = useState(true);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [activityLoading, setActivityLoading] = useState(true);

  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  // Search & Filter for Live Active Sessions
  const [sessionSearch, setSessionSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState<"ALL" | "CRITICAL" | "MEDIUM" | "LOW">("ALL");

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.replace("/auth/login");
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
      const data = await apiClient.get<Exam[]>("/api/exams?limit=6&offset=0");
      setExams(Array.isArray(data) ? data : []);
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
      const data = await apiClient.get<ActiveSession[]>("/api/dashboard/active-sessions?limit=50&sort_by=risk_score");
      setActiveSessions(Array.isArray(data) ? data : []);
    } catch {
      setActiveSessions([]);
    } finally {
      setSessionsLoading(false);
    }
  }, [user]);

  const fetchRecentActivity = useCallback(async () => {
    if (!user || !["admin", "proctor"].includes(user.role)) {
      setActivityLoading(false);
      return;
    }
    try {
      const data = await apiClient.get<ActivityItem[]>("/api/users/audit-logs?limit=5");
      setRecentActivities(Array.isArray(data) ? data : []);
    } catch {
      setRecentActivities([]);
    } finally {
      setActivityLoading(false);
    }
  }, [user]);

  const refreshAll = useCallback(() => {
    setStatsLoading(true);
    setLastRefreshed(new Date());
    void fetchStats();
    void fetchExams();
    void fetchActiveSessions();
    void fetchRecentActivity();
  }, [fetchStats, fetchExams, fetchActiveSessions, fetchRecentActivity]);

  useEffect(() => {
    if (!isLoading && user) {
      void fetchStats();
      void fetchExams();
      void fetchActiveSessions();
      void fetchRecentActivity();
    }
  }, [isLoading, user, fetchStats, fetchExams, fetchActiveSessions, fetchRecentActivity]);

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

  // Filtered live sessions logic
  const filteredSessions = activeSessions.filter((sess) => {
    const matchesSearch =
      sess.candidate_name?.toLowerCase().includes(sessionSearch.toLowerCase()) ||
      sess.exam_title?.toLowerCase().includes(sessionSearch.toLowerCase()) ||
      sess.candidate_email?.toLowerCase().includes(sessionSearch.toLowerCase());

    if (!matchesSearch) return false;

    if (riskFilter === "CRITICAL") return sess.current_risk_score >= 70 || sess.risk_level === "HIGH" || sess.risk_level === "CRITICAL";
    if (riskFilter === "MEDIUM") return (sess.current_risk_score >= 30 && sess.current_risk_score < 70) || sess.risk_level === "MEDIUM";
    if (riskFilter === "LOW") return sess.current_risk_score < 30 || sess.risk_level === "LOW";

    return true;
  });

  return (
    <div className="flex-1 w-full pb-12">
      <div className="w-full">
        {/* Header */}
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white/80 backdrop-blur px-6 sm:px-8 py-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                {isAdmin && "Admin Command Center"}
                {isProctor && "Proctoring Operations Center"}
                {isReviewer && "Evaluation & Review Center"}
                {isCandidate && "My Candidate Exam Portal"}
              </h1>
              <p className="text-sm text-slate-500 mt-0.5">
                Welcome back, <span className="font-semibold text-slate-800">{user.full_name}</span>
                <span className="ml-2 inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700 capitalize border border-blue-100">
                  {user.role}
                </span>
              </p>
            </div>

            <div className="flex items-center gap-3">
              {(isAdmin || isProctor) && (
                <div className="flex items-center gap-2 text-xs text-slate-500 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg">
                  <Radio className="h-3.5 w-3.5 text-emerald-500 animate-pulse" />
                  <span className="hidden sm:inline">Sync 30s • </span>
                  <span>{lastRefreshed.toLocaleTimeString()}</span>
                </div>
              )}

              <button
                onClick={refreshAll}
                className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 transition-colors"
                title="Refresh dashboard metrics"
              >
                <RefreshCw className={`h-4 w-4 ${statsLoading ? "animate-spin text-blue-600" : ""}`} />
                <span className="hidden sm:inline">Refresh</span>
              </button>

              {isAdmin && (
                <Link
                  href="/admin/exam/builder"
                  className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors shadow-sm"
                >
                  <Plus className="h-4 w-4" />
                  <span>New Exam</span>
                </Link>
              )}
            </div>
          </div>
        </div>

        <div className="px-6 sm:px-8 py-6 space-y-8 max-w-7xl mx-auto">

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
                  sub={`${stats?.in_progress_sessions ?? 0} active in-progress`}
                  icon={Users}
                  accent="bg-violet-600"
                  loading={statsLoading}
                />
                <StatCard
                  label="Flagged Risk Signals"
                  value={stats ? stats.high_risk_count + stats.medium_risk_count : 0}
                  sub={`${stats?.high_risk_count ?? 0} critical · ${stats?.medium_risk_count ?? 0} medium`}
                  icon={AlertTriangle}
                  accent="bg-amber-500"
                  loading={statsLoading}
                />
                <StatCard
                  label="Completed Submissions"
                  value={stats?.submitted_sessions ?? 0}
                  sub={`Avg risk score: ${((stats?.average_risk_score ?? 0) * 100).toFixed(1)}%`}
                  icon={CheckCircle2}
                  accent="bg-emerald-600"
                  loading={statsLoading}
                />
              </div>

              {/* Live Risk Distribution Bar */}
              {stats && (stats.total_active_sessions > 0) && (
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                      <BarChart3 className="h-4 w-4 text-blue-600" />
                      Live Proctoring Risk Spectrum
                    </h2>
                    <span className="text-xs font-semibold text-slate-500">{stats.total_active_sessions} Active Session(s)</span>
                  </div>
                  <div className="flex h-3.5 w-full overflow-hidden rounded-full gap-0.5 bg-slate-100">
                    {stats.high_risk_count > 0 && (
                      <div
                        style={{ width: `${(stats.high_risk_count / stats.total_active_sessions) * 100}%` }}
                        className="bg-red-500 rounded-l-full transition-all"
                        title={`High Risk: ${stats.high_risk_count}`}
                      />
                    )}
                    {stats.medium_risk_count > 0 && (
                      <div
                        style={{ width: `${(stats.medium_risk_count / stats.total_active_sessions) * 100}%` }}
                        className="bg-amber-400 transition-all"
                        title={`Medium Risk: ${stats.medium_risk_count}`}
                      />
                    )}
                    {stats.low_risk_count > 0 && (
                      <div
                        style={{ width: `${(stats.low_risk_count / stats.total_active_sessions) * 100}%` }}
                        className="bg-emerald-400 rounded-r-full transition-all"
                        title={`Low Risk: ${stats.low_risk_count}`}
                      />
                    )}
                  </div>
                  <div className="mt-3 flex items-center gap-6 text-xs text-slate-600">
                    <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-red-500" /><strong>High Risk:</strong> {stats.high_risk_count}</span>
                    <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-amber-400" /><strong>Medium Risk:</strong> {stats.medium_risk_count}</span>
                    <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-emerald-400" /><strong>Low Risk:</strong> {stats.low_risk_count}</span>
                  </div>
                </div>
              )}

              {/* Main Content Split: Live Sessions (Left) & Activity Log Feed (Right) */}
              <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                
                {/* Active Sessions Table (2 Cols) */}
                <div className="xl:col-span-2 rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden flex flex-col justify-between">
                  <div>
                    {/* Header Controls & Filter */}
                    <div className="p-5 border-b border-slate-100 space-y-4">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                          <Activity className="h-5 w-5 text-blue-600 animate-pulse" />
                          Live Active Proctoring Sessions
                        </h2>
                        
                        <Link href="/admin/live" className="flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-700 transition-colors">
                          Open Live Proctoring Dashboard <ArrowUpRight className="h-3.5 w-3.5" />
                        </Link>
                      </div>

                      {/* Search Bar & Risk Filter Pills */}
                      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
                        <div className="relative w-full sm:w-64">
                          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                          <input
                            type="text"
                            value={sessionSearch}
                            onChange={(e) => setSessionSearch(e.target.value)}
                            placeholder="Filter by student or exam..."
                            className="w-full pl-9 pr-3 py-1.5 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          />
                        </div>

                        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg w-full sm:w-auto overflow-x-auto">
                          {(["ALL", "CRITICAL", "MEDIUM", "LOW"] as const).map((lvl) => (
                            <button
                              key={lvl}
                              type="button"
                              onClick={() => setRiskFilter(lvl)}
                              className={`px-3 py-1 text-[11px] font-semibold rounded-md transition-all ${
                                riskFilter === lvl
                                  ? "bg-white text-slate-900 shadow-sm"
                                  : "text-slate-600 hover:text-slate-900"
                              }`}
                            >
                              {lvl === "ALL" ? "All Risk" : lvl}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Table Render */}
                    {sessionsLoading ? (
                      <div className="space-y-3 p-6">
                        {[...Array(4)].map((_, i) => (
                          <div key={i} className="h-12 w-full animate-pulse rounded-lg bg-slate-100" />
                        ))}
                      </div>
                    ) : filteredSessions.length === 0 ? (
                      <div className="flex flex-col items-center justify-center py-14 text-slate-400">
                        <ShieldCheck className="h-10 w-10 mb-3 text-slate-300" />
                        <p className="text-sm font-semibold text-slate-700">No active sessions match criteria</p>
                        <p className="text-xs text-slate-400 mt-1">Sessions will update in real-time as students join exams.</p>
                      </div>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-slate-100 bg-slate-50/70 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                              <th className="px-5 py-3 text-left">Candidate</th>
                              <th className="px-5 py-3 text-left">Target Exam</th>
                              <th className="px-5 py-3 text-left">Risk Index</th>
                              <th className="px-5 py-3 text-left">Risk Level</th>
                              <th className="px-5 py-3 text-left">Started</th>
                              <th className="px-5 py-3 text-left">Action</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {filteredSessions.map((session) => (
                              <tr key={session.session_id} className="hover:bg-slate-50/70 transition-colors">
                                <td className="px-5 py-3.5">
                                  <div>
                                    <p className="font-semibold text-slate-900">{session.candidate_name || "—"}</p>
                                    <p className="text-xs text-slate-400">{session.candidate_email || ""}</p>
                                  </div>
                                </td>
                                <td className="px-5 py-3.5">
                                  <p className="text-slate-700 font-medium truncate max-w-[160px]">{session.exam_title}</p>
                                </td>
                                <td className="px-5 py-3.5">
                                  <div className="flex items-center gap-2">
                                    <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100">
                                      <div
                                        className={`h-full rounded-full transition-all ${
                                          session.current_risk_score >= 60 ? "bg-red-500" :
                                          session.current_risk_score >= 30 ? "bg-amber-400" : "bg-emerald-400"
                                        }`}
                                        style={{ width: `${Math.min(session.current_risk_score, 100)}%` }}
                                      />
                                    </div>
                                    <span className="text-xs font-mono font-medium text-slate-600">
                                      {session.current_risk_score.toFixed(1)}
                                    </span>
                                  </div>
                                </td>
                                <td className="px-5 py-3.5">
                                  <RiskBadge level={session.risk_level || "LOW"} />
                                </td>
                                <td className="px-5 py-3.5 text-xs text-slate-400">
                                  {session.started_at
                                    ? new Date(session.started_at).toLocaleTimeString()
                                    : "—"}
                                </td>
                                <td className="px-5 py-3.5">
                                  <Link
                                    href={`/admin/live?session_id=${session.session_id}`}
                                    className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-700 hover:border-blue-500 hover:text-blue-600 transition"
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

                  <div className="p-4 bg-slate-50 border-t border-slate-100 text-xs text-slate-500 flex justify-between items-center">
                    <span>Showing {filteredSessions.length} active candidate session(s)</span>
                    <Link href="/admin/live" className="text-blue-600 font-semibold hover:underline">
                      Launch Full Proctoring Grid →
                    </Link>
                  </div>
                </div>

                {/* Right Column: Live Audit Activity Feed */}
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm space-y-4 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                      <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                        <History className="h-4 w-4 text-blue-600" />
                        System Audit Feed
                      </h2>
                      <Link href="/admin/audit" className="text-xs text-blue-600 font-semibold hover:underline">
                        View Log →
                      </Link>
                    </div>

                    {activityLoading ? (
                      <div className="space-y-3 pt-3">
                        {[...Array(4)].map((_, i) => (
                          <div key={i} className="h-12 w-full animate-pulse rounded-lg bg-slate-100" />
                        ))}
                      </div>
                    ) : recentActivities.length === 0 ? (
                      <div className="py-10 text-center text-xs text-slate-400">
                        No recent system events logged.
                      </div>
                    ) : (
                      <div className="space-y-3 pt-3">
                        {recentActivities.map((act) => (
                          <div key={act.id} className="p-3 rounded-xl bg-slate-50 border border-slate-100 space-y-1">
                            <div className="flex items-center justify-between text-xs">
                              <span className="font-bold text-slate-800 font-mono text-[11px]">{act.action}</span>
                              <span className="text-[10px] text-slate-400">
                                {new Date(act.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </span>
                            </div>
                            <div className="flex items-center justify-between text-[11px] text-slate-500">
                              <span>By: {act.user} ({act.role})</span>
                              <span className="font-mono text-[10px] text-slate-400">{act.ip_address}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="pt-3 border-t border-slate-100 text-xs text-slate-500 flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-emerald-500" />
                    <span>Real-time IP & session security tracking active</span>
                  </div>
                </div>

              </div>

              {/* Quick Actions Grid */}
              <div className="space-y-4">
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-blue-600" />
                  Admin Navigation & Quick Actions
                </h2>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  {isAdmin && (
                    <>
                      <Link href="/admin/exam/builder" className="p-4 rounded-xl border border-slate-200 bg-white hover:border-blue-500 hover:shadow-sm transition group">
                        <div className="flex items-center justify-between">
                          <Plus className="h-5 w-5 text-blue-600" />
                          <ArrowUpRight className="h-4 w-4 text-slate-300 group-hover:text-blue-600 transition" />
                        </div>
                        <p className="font-bold text-slate-900 text-sm mt-2">Create Exam</p>
                        <p className="text-xs text-slate-500 mt-0.5">Questions, schedule & proctoring</p>
                      </Link>

                      <Link href="/admin/questions" className="p-4 rounded-xl border border-slate-200 bg-white hover:border-blue-500 hover:shadow-sm transition group">
                        <div className="flex items-center justify-between">
                          <HelpCircle className="h-5 w-5 text-purple-600" />
                          <ArrowUpRight className="h-4 w-4 text-slate-300 group-hover:text-purple-600 transition" />
                        </div>
                        <p className="font-bold text-slate-900 text-sm mt-2">Question Bank</p>
                        <p className="text-xs text-slate-500 mt-0.5">Manage & seed MCQs / Code tasks</p>
                      </Link>

                      <Link href="/admin/users" className="p-4 rounded-xl border border-slate-200 bg-white hover:border-blue-500 hover:shadow-sm transition group">
                        <div className="flex items-center justify-between">
                          <Users className="h-5 w-5 text-emerald-600" />
                          <ArrowUpRight className="h-4 w-4 text-slate-300 group-hover:text-emerald-600 transition" />
                        </div>
                        <p className="font-bold text-slate-900 text-sm mt-2">Manage Users</p>
                        <p className="text-xs text-slate-500 mt-0.5">Roles, accounts & status</p>
                      </Link>

                      <Link href="/admin/broadcast" className="p-4 rounded-xl border border-slate-200 bg-white hover:border-blue-500 hover:shadow-sm transition group">
                        <div className="flex items-center justify-between">
                          <Mail className="h-5 w-5 text-amber-500" />
                          <ArrowUpRight className="h-4 w-4 text-slate-300 group-hover:text-amber-500 transition" />
                        </div>
                        <p className="font-bold text-slate-900 text-sm mt-2">Broadcast Center</p>
                        <p className="text-xs text-slate-500 mt-0.5">Mass announcements & emails</p>
                      </Link>

                      <Link href="/admin/ai-test" className="p-4 rounded-xl border border-slate-200 bg-white hover:border-blue-500 hover:shadow-sm transition group">
                        <div className="flex items-center justify-between">
                          <Cpu className="h-5 w-5 text-indigo-600" />
                          <ArrowUpRight className="h-4 w-4 text-slate-300 group-hover:text-indigo-600 transition" />
                        </div>
                        <p className="font-bold text-slate-900 text-sm mt-2">AI Test Sandbox</p>
                        <p className="text-xs text-slate-500 mt-0.5">Test LLM proctoring prompts</p>
                      </Link>

                      <Link href="/admin/analytics" className="p-4 rounded-xl border border-slate-200 bg-white hover:border-blue-500 hover:shadow-sm transition group">
                        <div className="flex items-center justify-between">
                          <BarChart3 className="h-5 w-5 text-rose-600" />
                          <ArrowUpRight className="h-4 w-4 text-slate-300 group-hover:text-rose-600 transition" />
                        </div>
                        <p className="font-bold text-slate-900 text-sm mt-2">Analytics & Reports</p>
                        <p className="text-xs text-slate-500 mt-0.5">Performance & risk trends</p>
                      </Link>

                      <Link href="/admin/settings" className="p-4 rounded-xl border border-slate-200 bg-white hover:border-blue-500 hover:shadow-sm transition group">
                        <div className="flex items-center justify-between">
                          <Sliders className="h-5 w-5 text-teal-600" />
                          <ArrowUpRight className="h-4 w-4 text-slate-300 group-hover:text-teal-600 transition" />
                        </div>
                        <p className="font-bold text-slate-900 text-sm mt-2">Risk Calibrator</p>
                        <p className="text-xs text-slate-500 mt-0.5">Configure AI penalty weights</p>
                      </Link>

                      <Link href="/admin/audit" className="p-4 rounded-xl border border-slate-200 bg-white hover:border-blue-500 hover:shadow-sm transition group">
                        <div className="flex items-center justify-between">
                          <History className="h-5 w-5 text-slate-600" />
                          <ArrowUpRight className="h-4 w-4 text-slate-300 group-hover:text-slate-600 transition" />
                        </div>
                        <p className="font-bold text-slate-900 text-sm mt-2">Audit Trail</p>
                        <p className="text-xs text-slate-500 mt-0.5">Log of all admin activities</p>
                      </Link>
                    </>
                  )}
                </div>
              </div>
            </>
          )}

          {/* ── REVIEWER VIEW ── */}
          {isReviewer && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Link href="/admin/review" className="group rounded-2xl border border-slate-200 bg-white p-6 shadow-sm hover:border-amber-500 hover:shadow-md transition">
                  <AlertTriangle className="h-8 w-8 text-amber-500 mb-3" />
                  <p className="text-base font-bold text-slate-900">Review Queue</p>
                  <p className="text-xs text-slate-500 mt-1">Evaluate AI-flagged sessions with video snapshots</p>
                  <p className="mt-4 text-xs font-semibold text-amber-600 group-hover:underline flex items-center gap-1">Open Queue <ArrowUpRight className="h-3.5 w-3.5" /></p>
                </Link>

                <Link href="/admin/audit" className="group rounded-2xl border border-slate-200 bg-white p-6 shadow-sm hover:border-slate-400 hover:shadow-md transition">
                  <Clock className="h-8 w-8 text-slate-500 mb-3" />
                  <p className="text-base font-bold text-slate-900">Audit Trail</p>
                  <p className="text-xs text-slate-500 mt-1">Track all reviewer decisions and actions</p>
                  <p className="mt-4 text-xs font-semibold text-slate-600 group-hover:underline flex items-center gap-1">View Audit <ArrowUpRight className="h-3.5 w-3.5" /></p>
                </Link>
              </div>

              <div className="rounded-2xl border border-amber-100 bg-amber-50/60 p-5 text-sm text-amber-800">
                <strong>Reviewer Notice:</strong> AI risk signals are recommendations. You retain final authority to dismiss, escalate, or validate flagged incidents.
              </div>
            </div>
          )}

          {/* ── CANDIDATE VIEW ── */}
          {isCandidate && (
            <div className="space-y-6">
              {/* Available Exams */}
              <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
                <div className="border-b border-slate-100 px-6 py-4">
                  <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                    <BookOpen className="h-5 w-5 text-blue-600" />
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
                    <p className="text-sm font-semibold text-slate-700">No exams currently published for your cohort</p>
                    <p className="text-xs mt-1">Check back later or contact your instructor.</p>
                  </div>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {exams.filter((e) => e.status === "PUBLISHED").map((exam) => (
                      <div key={exam.id} className="flex items-center justify-between px-6 py-4 hover:bg-slate-50/70 transition-colors">
                        <div>
                          <p className="font-semibold text-slate-900 text-sm">{exam.title}</p>
                          <p className="text-xs text-slate-400 mt-0.5">
                            {exam.duration_minutes} minutes • {exam.total_marks} marks
                          </p>
                        </div>
                        <Link
                          href={`/exam/readiness?exam_id=${exam.id}`}
                          className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-700 transition-colors shadow-sm"
                        >
                          Start Exam <ArrowUpRight className="h-3.5 w-3.5" />
                        </Link>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Readiness Check Card */}
              <div className="rounded-2xl border border-blue-100 bg-blue-50/60 p-6 shadow-sm">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div>
                    <h3 className="font-bold text-slate-900 text-base">Pre-Exam System Readiness Check</h3>
                    <p className="text-xs text-slate-600 mt-1">Verify webcam, microphone, network latency, and browser compatibility prior to starting an exam.</p>
                  </div>
                  <Link
                    href="/exam/readiness"
                    className="shrink-0 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors shadow-sm"
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
