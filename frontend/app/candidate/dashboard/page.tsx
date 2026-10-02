"use client";
export const dynamic = "force-dynamic";

import React, { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import {
  BookOpen,
  CheckCircle2,
  Clock,
  ShieldAlert,
  Award,
  ArrowUpRight,
  Loader2,
  PlayCircle,
  RefreshCw,
  FileText,
  Sparkles,
  Cpu,
  User,
  Video,
  AlertTriangle,
  Calendar,
  Code,
  ShieldCheck,
  TrendingUp,
  ChevronRight
} from "lucide-react";
import toast from "react-hot-toast";

interface Exam {
  id: string;
  title: string;
  description: string;
  duration_minutes: number;
  start_window: string;
  end_window: string;
  status: string;
  total_marks?: number;
}

interface SubmissionHistory {
  session_id: string;
  exam_id: string;
  exam_name: string;
  submitted_at: string | null;
  total_score: number | null;
  percentage: number | null;
  results_published: boolean;
}

export default function CandidateDashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();

  const [exams, setExams] = useState<Exam[]>([]);
  const [history, setHistory] = useState<SubmissionHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.replace("/auth/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const fetchExams = useCallback(async () => {
    try {
      const data = await apiClient.get<Exam[]>("/api/exams");
      setExams(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Failed to load available exams", err);
      setExams([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchHistory = useCallback(async () => {
    try {
      const data = await apiClient.get<SubmissionHistory[]>("/api/results/history");
      setHistory(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Failed to load test history", err);
      setHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const refreshAll = useCallback(() => {
    setLoading(true);
    setHistoryLoading(true);
    setLastRefreshed(new Date());
    void fetchExams();
    void fetchHistory();
  }, [fetchExams, fetchHistory]);

  useEffect(() => {
    if (!authLoading && user) {
      void fetchExams();
      void fetchHistory();
    }
  }, [authLoading, user, fetchExams, fetchHistory]);

  if (authLoading || !user) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  const completedExamIds = new Set(history.map((h) => h.exam_id));

  const activeExams = exams.filter((e) => {
    const isPublished = e.status.toUpperCase() === "PUBLISHED" || e.status.toUpperCase() === "LIVE";
    const isCompleted = completedExamIds.has(e.id);
    return isPublished && !isCompleted;
  });

  const publishedHistory = history.filter((h) => h.results_published && h.percentage !== null);
  
  const averagePercentage =
    publishedHistory.length > 0
      ? publishedHistory.reduce((acc, curr) => acc + (curr.percentage || 0), 0) / publishedHistory.length
      : 0;

  return (
    <div className="flex-1 w-full pb-12">
      {/* Sticky Header */}
      <div className="sticky top-0 z-10 border-b border-slate-200 bg-white/80 backdrop-blur px-6 sm:px-8 py-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 max-w-7xl mx-auto">
          <div>
            <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <BookOpen className="h-6 w-6 text-blue-600" />
              Candidate Exam Portal
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
              Welcome back, <span className="font-semibold text-slate-800">{user.full_name}</span>
              {user.roll_no && <span className="ml-2 font-mono text-slate-400">({user.roll_no})</span>}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-xs text-slate-500 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg hidden sm:block">
              Refreshed: {lastRefreshed.toLocaleTimeString()}
            </div>

            <button
              onClick={refreshAll}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50 transition-colors"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading || historyLoading ? "animate-spin text-blue-600" : ""}`} />
              <span>Refresh</span>
            </button>

            <Link
              href="/exam/readiness"
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-700 transition-colors shadow-sm"
            >
              <Video className="h-3.5 w-3.5" />
              System Readiness Check
            </Link>
          </div>
        </div>
      </div>

      <div className="px-6 sm:px-8 py-6 space-y-8 max-w-7xl mx-auto">

        {/* Top Key Metrics */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Available Exams</span>
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-white">
                <BookOpen className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-3 text-3xl font-bold text-slate-900">{activeExams.length}</p>
            <p className="mt-1 text-xs text-slate-400">Active & ready to launch</p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Tests Completed</span>
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-600 text-white">
                <CheckCircle2 className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-3 text-3xl font-bold text-slate-900">{history.length}</p>
            <p className="mt-1 text-xs text-slate-400">Submissions recorded</p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Avg Score</span>
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-600 text-white">
                <Award className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-3 text-3xl font-bold text-slate-900">
              {publishedHistory.length > 0 ? `${averagePercentage.toFixed(1)}%` : "N/A"}
            </p>
            <p className="mt-1 text-xs text-slate-400">Across published grades</p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">System Integrity</span>
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-600">
                <ShieldCheck className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-3 text-sm font-bold text-emerald-700">Verified & Active</p>
            <p className="mt-1 text-xs text-slate-400">Webcam & Browser Lock</p>
          </div>
        </div>

        {/* System Check Banner */}
        <div className="rounded-2xl border border-blue-200 bg-gradient-to-r from-blue-50 via-indigo-50 to-white p-6 shadow-sm">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-full bg-blue-600 text-white text-[11px] font-bold uppercase tracking-wider">
                  Mandatory Step
                </span>
                <h3 className="font-bold text-slate-900 text-base">Pre-Exam System Readiness Verification</h3>
              </div>
              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                Check camera feed, microphone levels, network latency, and browser lockdown before starting any examination.
              </p>
            </div>
            
            <Link
              href="/exam/readiness"
              className="shrink-0 flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-xs font-bold text-white hover:bg-blue-700 transition shadow-md"
            >
              Run System Check <ArrowUpRight className="h-4 w-4" />
            </Link>
          </div>
        </div>

        {/* Main Grid: Available Exams & Recent Submissions */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

          {/* Left: Available Examinations (2 Cols) */}
          <div className="xl:col-span-2 rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden flex flex-col justify-between">
            <div>
              <div className="p-5 border-b border-slate-100 flex items-center justify-between">
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <PlayCircle className="h-5 w-5 text-blue-600" />
                  Available & Scheduled Examinations
                </h2>
                <span className="text-xs text-slate-500">{activeExams.length} Active</span>
              </div>

              {loading || historyLoading ? (
                <div className="space-y-3 p-6">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="h-16 w-full animate-pulse rounded-xl bg-slate-100" />
                  ))}
                </div>
              ) : activeExams.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-500 space-y-3 text-center px-4">
                  <div className="h-12 w-12 rounded-full bg-emerald-50 text-emerald-600 border border-emerald-200 flex items-center justify-center">
                    <CheckCircle2 className="h-6 w-6" />
                  </div>
                  <h3 className="text-base font-bold text-slate-900">
                    {history.length > 0 ? "All assigned exams completed!" : "No active exams available"}
                  </h3>
                  <p className="text-xs text-slate-500 max-w-sm">
                    {history.length > 0
                      ? `You have completed all ${history.length} exam(s). Review your scores and reports under My Results.`
                      : "No active exams are currently assigned for your cohort. Check back later."}
                  </p>
                  {history.length > 0 && (
                    <Link
                      href="/candidate/results"
                      className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white font-bold text-xs rounded-xl hover:bg-blue-700 transition shadow-sm"
                    >
                      <Award className="h-4 w-4" /> View My Completed Results →
                    </Link>
                  )}
                </div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {activeExams.map((exam) => (
                    <div key={exam.id} className="p-6 hover:bg-slate-50/80 transition-colors space-y-3">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="inline-flex items-center rounded-full bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 text-xs font-bold text-emerald-700">
                              LIVE NOW
                            </span>
                            <h3 className="font-bold text-slate-900 text-base">{exam.title}</h3>
                          </div>
                          <p className="text-xs text-slate-500 line-clamp-2 mt-1">
                            {exam.description || "No specific guidelines specified for this assessment."}
                          </p>
                        </div>

                        <Link
                          href={`/exam/readiness?exam_id=${exam.id}`}
                          className="shrink-0 flex items-center gap-1.5 rounded-xl bg-blue-600 px-4 py-2 text-xs font-bold text-white hover:bg-blue-700 transition shadow-sm self-start sm:self-auto"
                        >
                          Start Exam <ArrowUpRight className="h-3.5 w-3.5" />
                        </Link>
                      </div>

                      <div className="flex items-center gap-4 text-xs text-slate-500 pt-1 border-t border-slate-100">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3.5 w-3.5 text-slate-400" /> {exam.duration_minutes} Minutes
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3.5 w-3.5 text-slate-400" />
                          {exam.start_window ? new Date(exam.start_window).toLocaleDateString() : "TBD"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="p-4 bg-slate-50 border-t border-slate-100 text-xs text-slate-500 flex justify-between items-center">
              <span>Ensure continuous webcam connection during all exams.</span>
              <Link href="/candidate/practice" className="text-blue-600 font-semibold hover:underline">
                Practice Sandbox →
              </Link>
            </div>
          </div>

          {/* Right: Submissions & Integrity Rules (1 Col) */}
          <div className="space-y-6">

            {/* Test History */}
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <FileText className="h-4 w-4 text-blue-600" />
                  My Submissions
                </h2>
                <Link href="/candidate/results" className="text-xs text-blue-600 font-semibold hover:underline">
                  View All →
                </Link>
              </div>

              {historyLoading ? (
                <div className="space-y-2">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="h-12 w-full animate-pulse rounded-lg bg-slate-100" />
                  ))}
                </div>
              ) : history.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-400">
                  No exam submissions recorded yet.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {history.slice(0, 4).map((item) => (
                    <div key={item.session_id} className="p-3 rounded-xl bg-slate-50 border border-slate-100 space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-bold text-slate-900 truncate max-w-[140px]">{item.exam_name}</span>
                        {item.results_published && item.percentage !== null ? (
                          <span className="font-mono font-bold text-emerald-600">{item.percentage.toFixed(1)}%</span>
                        ) : (
                          <span className="text-[10px] text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full font-medium">
                            Grading
                          </span>
                        )}
                      </div>
                      <div className="text-[10px] text-slate-400">
                        Submitted: {item.submitted_at ? new Date(item.submitted_at).toLocaleDateString() : "Recently"}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Test Rules Callout */}
            <div className="rounded-2xl border border-slate-900 bg-slate-900 p-5 text-white shadow-sm space-y-3">
              <div className="flex items-center gap-2 text-xs font-semibold text-blue-400 uppercase tracking-wider">
                <ShieldAlert className="h-4 w-4" /> AI Proctoring Guidelines
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                ExamSentinel monitors webcam feed, audio signals, and tab state during your test.
              </p>
              <div className="space-y-1.5 text-[11px] text-slate-400 pt-1">
                <div className="flex items-center gap-1.5">• Keep your face centered in camera view</div>
                <div className="flex items-center gap-1.5">• Do not switch browser tabs or windows</div>
                <div className="flex items-center gap-1.5">• Single active login session enforced</div>
              </div>
            </div>

          </div>

        </div>

        {/* Candidate Shortcuts Navigation */}
        <div className="space-y-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-blue-600" />
            Candidate Tools & Shortcuts
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Link
              href="/candidate/practice"
              className="p-4 rounded-xl border border-slate-200 bg-white hover:border-blue-500 hover:shadow-sm transition group"
            >
              <div className="flex items-center justify-between">
                <Cpu className="h-5 w-5 text-indigo-600" />
                <ChevronRight className="h-4 w-4 text-slate-300 group-hover:text-indigo-600 transition" />
              </div>
              <p className="font-bold text-slate-900 text-sm mt-2">Practice Sandbox</p>
              <p className="text-xs text-slate-500 mt-0.5">Test questions & AI environment</p>
            </Link>

            <Link
              href="/candidate/problems"
              className="p-4 rounded-xl border border-slate-200 bg-white hover:border-blue-500 hover:shadow-sm transition group"
            >
              <div className="flex items-center justify-between">
                <Code className="h-5 w-5 text-purple-600" />
                <ChevronRight className="h-4 w-4 text-slate-300 group-hover:text-purple-600 transition" />
              </div>
              <p className="font-bold text-slate-900 text-sm mt-2">Coding Problems</p>
              <p className="text-xs text-slate-500 mt-0.5">Practice coding challenges</p>
            </Link>

            <Link
              href="/candidate/results"
              className="p-4 rounded-xl border border-slate-200 bg-white hover:border-blue-500 hover:shadow-sm transition group"
            >
              <div className="flex items-center justify-between">
                <Award className="h-5 w-5 text-emerald-600" />
                <ChevronRight className="h-4 w-4 text-slate-300 group-hover:text-emerald-600 transition" />
              </div>
              <p className="font-bold text-slate-900 text-sm mt-2">My Grades & Results</p>
              <p className="text-xs text-slate-500 mt-0.5">View published test scores</p>
            </Link>

            <Link
              href="/candidate/profile"
              className="p-4 rounded-xl border border-slate-200 bg-white hover:border-blue-500 hover:shadow-sm transition group"
            >
              <div className="flex items-center justify-between">
                <User className="h-5 w-5 text-slate-700" />
                <ChevronRight className="h-4 w-4 text-slate-300 group-hover:text-slate-700 transition" />
              </div>
              <p className="font-bold text-slate-900 text-sm mt-2">My Profile</p>
              <p className="text-xs text-slate-500 mt-0.5">Account settings & credentials</p>
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
}
