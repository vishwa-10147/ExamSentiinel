"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import Sidebar from "@/components/Sidebar";
import {
  ShieldAlert,
  Users,
  CheckCircle2,
  Clock,
  AlertTriangle,
  PlayCircle,
  FileText,
  Activity,
  ArrowUpRight,
} from "lucide-react";

interface DashboardStats {
  active_exams: number;
  total_active_sessions: number;
  submitted_sessions: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
}

export default function DashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const [stats, setStats] = React.useState<DashboardStats | null>(null);
  const [dashboardError, setDashboardError] = React.useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isLoading || !user || !["admin", "proctor"].includes(user.role)) return;
    let socket: WebSocket | null = null;
    const loadStats = async () => {
      try {
        const data = await apiClient.get<DashboardStats>("/api/dashboard/stats");
        setStats(data);
      } catch (err) {
        setDashboardError(err instanceof Error ? err.message : "Dashboard data is unavailable");
      }
    };
    void loadStats();
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const wsBase = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
    if (token && typeof window !== "undefined") {
      socket = new WebSocket(`${wsBase}/api/ws/dashboard?token=${encodeURIComponent(token)}`);
      socket.onmessage = () => void loadStats();
    }
    return () => {
      if (socket) {
        if (socket.readyState === WebSocket.CONNECTING) {
          socket.addEventListener('open', () => socket?.close());
        } else {
          socket.close();
        }
      }
    };
  }, [isLoading, user]);

  if (isLoading || !user) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center text-slate-500">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="flex flex-1">
      <Sidebar />

      <div className="flex-1 p-6 sm:p-8 max-w-7xl">
        {/* Header greeting */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Welcome, {user.full_name}
            </h1>
            <p className="text-sm text-slate-500">
              Institution Portal — Role: <span className="font-semibold text-blue-600 capitalize">{user.role}</span>
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 border border-emerald-200">
              <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
              Platform Active
            </span>
          </div>
        </div>

        {/* Dynamic content per role */}
        {user.role === "admin" && (
          <div className="mt-8 space-y-8">
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-xs font-semibold uppercase tracking-wider">Active Exams</span>
                  <Activity className="h-4 w-4 text-blue-600" />
                </div>
                <p className="mt-2 text-3xl font-bold text-slate-900">{stats?.active_exams ?? "—"}</p>
                <p className="mt-1 text-xs text-emerald-600">{stats?.total_active_sessions ?? "—"} students connected</p>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-xs font-semibold uppercase tracking-wider">Flagged Sessions</span>
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                </div>
                <p className="mt-2 text-3xl font-bold text-slate-900">{stats ? stats.high_risk_count + stats.medium_risk_count : "—"}</p>
                <p className="mt-1 text-xs text-amber-600">Requires human review</p>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-xs font-semibold uppercase tracking-wider">Completed Reviews</span>
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                </div>
                <p className="mt-2 text-3xl font-bold text-slate-900">{stats?.submitted_sessions ?? "—"}</p>
                <p className="mt-1 text-xs text-slate-500">Submitted sessions</p>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-xs font-semibold uppercase tracking-wider">Enrolled Candidates</span>
                  <Users className="h-4 w-4 text-purple-500" />
                </div>
                <p className="mt-2 text-3xl font-bold text-slate-900">{stats?.low_risk_count ?? "—"}</p>
                <p className="mt-1 text-xs text-slate-500">Low-risk active sessions</p>
              </div>
            </div>
            {dashboardError && <p className="text-sm text-amber-700">{dashboardError}</p>}

            {/* Quick Actions */}
              <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="text-base font-bold text-slate-900">Quick Administrative Actions</h2>
                <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <button 
                    onClick={() => router.push("/admin/exam/builder")}
                    className="flex items-center justify-between rounded-lg border border-slate-200 p-4 text-left hover:border-blue-500 hover:bg-blue-50/40 transition"
                  >
                    <div>
                      <p className="font-semibold text-slate-900 text-sm">Create New Exam</p>
                      <p className="text-xs text-slate-500">Configure schedule, questions & proctoring</p>
                    </div>
                    <ArrowUpRight className="h-4 w-4 text-slate-400" />
                  </button>
                  <button 
                    onClick={() => router.push("/admin/review")}
                    className="flex items-center justify-between rounded-lg border border-slate-200 p-4 text-left hover:border-blue-500 hover:bg-blue-50/40 transition"
                  >
                    <div>
                      <p className="font-semibold text-slate-900 text-sm">Review Queue</p>
                      <p className="text-xs text-slate-500">Adjudicate flagged proctoring signals</p>
                    </div>
                    <ArrowUpRight className="h-4 w-4 text-slate-400" />
                  </button>
                  <button 
                    onClick={() => router.push("/admin/audit")}
                    className="flex items-center justify-between rounded-lg border border-slate-200 p-4 text-left hover:border-blue-500 hover:bg-blue-50/40 transition"
                  >
                    <div>
                      <p className="font-semibold text-slate-900 text-sm">Audit Trail</p>
                      <p className="text-xs text-slate-500">Inspect system and reviewer activity</p>
                    </div>
                    <ArrowUpRight className="h-4 w-4 text-slate-400" />
                  </button>
                </div>
              </div>
          </div>
        )}

        {user.role === "proctor" && (
          <div className="mt-8 space-y-6">
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-bold text-slate-900">Live Proctoring Center</h2>
              <p className="text-sm text-slate-500 mt-1">
                Real-time multi-candidate monitoring grid and telemetry feed
              </p>
              <div className="mt-6 border-t border-slate-100 pt-4">
                <p className="text-sm text-slate-600">
                  Ready to launch live session grid for scheduled examinations.
                </p>
              </div>
            </div>
          </div>
        )}

        {user.role === "reviewer" && (
          <div className="mt-8 space-y-6">
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-bold text-slate-900">Evidence Review Queue</h2>
              <p className="text-sm text-slate-500 mt-1">
                Evaluate AI-surfaced proctoring signals with video snapshots and timeline scrubber
              </p>
              <div className="mt-6 rounded-lg bg-amber-50 p-4 border border-amber-200 text-sm text-amber-800">
                Reminder: Signals are not verdicts. You have full authority to dismiss, escalate, or record findings.
              </div>
            </div>
          </div>
        )}

        {user.role === "candidate" && (
          <div className="mt-8 space-y-6">
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-bold text-slate-900">My Exam Portal</h2>
              <p className="text-sm text-slate-500 mt-1">
                Access scheduled exams, verify system readiness, and view past results
              </p>

              <div className="mt-6 border border-slate-200 rounded-lg p-4 bg-slate-50">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">Pre-Exam System Readiness</h3>
                    <p className="text-xs text-slate-500">Check webcam, microphone, and browser compatibility</p>
                  </div>
                  <button
                    onClick={() => router.push("/exam/readiness")}
                    className="rounded-lg bg-blue-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-blue-500 transition-colors"
                  >
                    Run System Check
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
