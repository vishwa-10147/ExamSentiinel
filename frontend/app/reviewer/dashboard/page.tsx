"use client";
export const dynamic = "force-dynamic";

import React, { useEffect, useState, useMemo, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import {
  FileCheck2,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Search,
  RefreshCw,
  Eye,
  ShieldAlert,
  History,
  FileText,
  Check,
  X,
  ArrowUpRight,
  Filter,
  Layers,
  Award
} from "lucide-react";
import toast, { Toaster } from "react-hot-toast";

interface ReviewQueueItem {
  session_id: string;
  candidate_name: string;
  candidate_email?: string;
  exam_title: string;
  exam_id?: string;
  risk_score: number;
  risk_level: string;
  submitted_at: string;
  flagged_events_count: number;
  status: "PENDING_REVIEW" | "APPROVED" | "FLAGGED_VIOLATION" | string;
}

interface AuditLog {
  id: string;
  action: string;
  user: string;
  timestamp: string;
  details?: string;
}

export default function ReviewerDashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();

  const [queue, setQueue] = useState<ReviewQueueItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "PENDING_REVIEW" | "APPROVED" | "FLAGGED">("PENDING_REVIEW");

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/auth/login");
    }
  }, [isLoading, isAuthenticated, router]);

  const fetchReviewQueue = useCallback(async () => {
    try {
      // Fetch review queue from backend API
      const response = await apiClient.get<ReviewQueueItem[]>("/api/proctoring/review-queue");
      const list = Array.isArray(response) ? response : (response as any)?.items || [];
      setQueue(list);
      setLastRefreshed(new Date());
    } catch (err) {
      console.error("Failed to load review queue", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAuditLogs = useCallback(async () => {
    try {
      const logs = await apiClient.get<AuditLog[]>("/api/users/audit-logs?limit=5");
      setAuditLogs(Array.isArray(logs) ? logs : []);
    } catch {
      setAuditLogs([]);
    }
  }, []);

  useEffect(() => {
    if (!isLoading && user && ["admin", "reviewer"].includes(user.role)) {
      void fetchReviewQueue();
      void fetchAuditLogs();
      const interval = setInterval(() => {
        void fetchReviewQueue();
        void fetchAuditLogs();
      }, 30000);
      return () => clearInterval(interval);
    }
  }, [isLoading, user, fetchReviewQueue, fetchAuditLogs]);

  const handleApproveSession = async (sessionId: string, candidateName: string) => {
    try {
      await apiClient.post(`/api/proctoring/sessions/${sessionId}/approve`, {
        notes: "Verified compliant by reviewer."
      });
      toast.success(`Session for ${candidateName} approved.`);
      void fetchReviewQueue();
    } catch (err: any) {
      toast.error(err?.message || "Failed to approve session.");
    }
  };

  const handleFlagViolation = async (sessionId: string, candidateName: string) => {
    const reason = window.prompt(`Enter violation summary for candidate "${candidateName}":`, "Confirmed academic integrity violation upon video snapshot review.");
    if (!reason) return;

    try {
      await apiClient.post(`/api/proctoring/sessions/${sessionId}/flag-violation`, {
        reason,
        notes: reason
      });
      toast.success(`Session for ${candidateName} flagged for integrity violation.`);
      void fetchReviewQueue();
    } catch (err: any) {
      toast.error(err?.message || "Failed to flag session.");
    }
  };

  const filteredQueue = useMemo(() => {
    return queue.filter((item) => {
      const name = item.candidate_name || "";
      const exam = item.exam_title || "";
      const email = item.candidate_email || "";

      const matchesSearch =
        !searchQuery.trim() ||
        name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        exam.toLowerCase().includes(searchQuery.toLowerCase()) ||
        email.toLowerCase().includes(searchQuery.toLowerCase());

      let matchesStatus = true;
      if (statusFilter === "PENDING_REVIEW") matchesStatus = item.status === "PENDING_REVIEW" || !item.status;
      if (statusFilter === "APPROVED") matchesStatus = item.status === "APPROVED";
      if (statusFilter === "FLAGGED") matchesStatus = item.status === "FLAGGED_VIOLATION";

      return matchesSearch && matchesStatus;
    });
  }, [queue, searchQuery, statusFilter]);

  if (isLoading || !user) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-900 text-slate-300">
        <div className="flex items-center gap-3">
          <RefreshCw className="h-6 w-6 animate-spin text-amber-500" />
          <span>Loading Reviewer Evaluation Center...</span>
        </div>
      </div>
    );
  }

  // Statistics
  const pendingCount = queue.filter((i) => i.status === "PENDING_REVIEW" || !i.status).length;
  const approvedCount = queue.filter((i) => i.status === "APPROVED").length;
  const flaggedCount = queue.filter((i) => i.status === "FLAGGED_VIOLATION").length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 sm:p-6 lg:p-8 space-y-6">
      <Toaster position="top-right" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/20">
              Evaluation & Human Review
            </span>
            <span className="flex items-center gap-1.5 text-xs text-blue-400 bg-blue-500/10 border border-blue-500/20 px-2.5 py-0.5 rounded-full font-medium">
              <span className="h-2 w-2 rounded-full bg-blue-400 animate-pulse" /> Post-Exam Audit Channel
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white flex items-center gap-3">
            <FileCheck2 className="h-7 w-7 text-amber-500" />
            Reviewer Marking & Audit Command Center
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Inspect AI risk snapshots, evaluate subjective answers, and issue final grading approvals.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-2 text-xs text-slate-400 bg-slate-900 border border-slate-800 px-3 py-2 rounded-xl">
            <Clock className="h-3.5 w-3.5 text-amber-400" />
            <span>Updated: {lastRefreshed.toLocaleTimeString()}</span>
          </div>
          <button
            onClick={() => void fetchReviewQueue()}
            className="inline-flex items-center gap-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 rounded-xl text-xs font-semibold transition-colors shadow-sm"
          >
            <RefreshCw className="h-3.5 w-3.5 text-amber-400" /> Refresh Queue
          </button>
          <Link
            href="/admin/review"
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-amber-600/30"
          >
            Full Review Queue <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Awaiting Evaluation</span>
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-amber-400 mt-3">{pendingCount}</p>
          <p className="text-xs text-slate-500 mt-1">Sessions pending human signoff</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Approved Sessions</span>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-emerald-400 mt-3">{approvedCount}</p>
          <p className="text-xs text-slate-500 mt-1">Validated & score published</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Confirmed Violations</span>
            <div className="p-2 rounded-xl bg-red-500/10 text-red-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-red-400 mt-3">{flaggedCount}</p>
          <p className="text-xs text-slate-500 mt-1">Academic integrity breaches</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Total Queue Volume</span>
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400">
              <Layers className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-white mt-3">{queue.length}</p>
          <p className="text-xs text-slate-500 mt-1">Recorded exam submissions</p>
        </div>
      </div>

      {/* Notice Banner */}
      <div className="bg-gradient-to-r from-slate-900 to-amber-950/40 border border-amber-500/30 rounded-2xl p-5 flex items-start gap-4">
        <div className="p-2 rounded-xl bg-amber-500/20 text-amber-400 shrink-0">
          <Award className="w-6 h-6" />
        </div>
        <div className="space-y-1">
          <h3 className="font-bold text-white text-sm">Human-in-the-Loop Evaluation Policy</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            AI risk scores are advisory recommendations derived from face-tracking and browser telemetry. You retain full human authority to approve scores, adjust points, or log integrity infractions.
          </p>
        </div>
      </div>

      {/* Main Split Content: Review Queue Table & Audit Logs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Review Queue (2 Cols) */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden flex flex-col shadow-xl">
          <div className="p-5 border-b border-slate-800 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <FileText className="w-5 h-5 text-amber-400" /> Pending Examination Review Queue
              </h2>

              <div className="flex items-center gap-2">
                {(["PENDING_REVIEW", "APPROVED", "FLAGGED", "ALL"] as const).map((filter) => (
                  <button
                    key={filter}
                    type="button"
                    onClick={() => setStatusFilter(filter)}
                    className={`px-3 py-1 text-xs font-bold rounded-xl transition-all ${
                      statusFilter === filter
                        ? "bg-amber-600 text-white shadow-md shadow-amber-600/30"
                        : "bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800"
                    }`}
                  >
                    {filter === "PENDING_REVIEW" ? "Pending" : filter}
                  </button>
                ))}
              </div>
            </div>

            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-3.5 top-3 h-4 w-4 text-slate-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search candidate name, email, or exam title..."
                className="w-full pl-10 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500"
              />
            </div>
          </div>

          <div className="overflow-x-auto flex-1">
            {loading ? (
              <div className="p-12 text-center text-slate-500">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-amber-500" />
                <p className="text-xs">Fetching review queue items...</p>
              </div>
            ) : filteredQueue.length === 0 ? (
              <div className="p-12 text-center text-slate-500">
                <CheckCircle2 className="w-10 h-10 mx-auto mb-2 text-emerald-500 opacity-60" />
                <p className="text-sm font-semibold text-slate-300">All submissions in queue evaluated!</p>
                <p className="text-xs text-slate-500 mt-1">No candidate sessions require review under selected filter.</p>
              </div>
            ) : (
              <table className="w-full text-sm text-left text-slate-400">
                <thead className="text-xs uppercase tracking-wider text-slate-500 bg-slate-950 border-b border-slate-800 font-semibold">
                  <tr>
                    <th className="px-5 py-3">Candidate</th>
                    <th className="px-5 py-3">Exam Title</th>
                    <th className="px-5 py-3">Risk Level</th>
                    <th className="px-5 py-3">Status</th>
                    <th className="px-5 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredQueue.map((item) => {
                    const isApproved = item.status === "APPROVED";
                    const isFlagged = item.status === "FLAGGED_VIOLATION";

                    return (
                      <tr key={item.session_id} className="hover:bg-slate-950/60 transition-colors">
                        <td className="px-5 py-4 font-semibold text-white">
                          <div>
                            <p className="text-slate-200">{item.candidate_name}</p>
                            {item.candidate_email && <p className="text-[11px] font-mono text-slate-500 font-normal">{item.candidate_email}</p>}
                          </div>
                        </td>
                        <td className="px-5 py-4 font-medium text-slate-300">
                          {item.exam_title}
                        </td>
                        <td className="px-5 py-4">
                          <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${
                            (item.risk_level || "").toUpperCase() === "HIGH" || (item.risk_level || "").toUpperCase() === "CRITICAL"
                              ? "bg-red-500/20 text-red-400 border-red-500/30"
                              : (item.risk_level || "").toUpperCase() === "MEDIUM"
                              ? "bg-amber-500/20 text-amber-400 border-amber-500/30"
                              : "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                          }`}>
                            {item.risk_level || "LOW"}
                          </span>
                        </td>
                        <td className="px-5 py-4 text-xs font-semibold">
                          {isApproved ? (
                            <span className="text-emerald-400 flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> Approved</span>
                          ) : isFlagged ? (
                            <span className="text-red-400 flex items-center gap-1"><ShieldAlert className="w-3.5 h-3.5" /> Flagged</span>
                          ) : (
                            <span className="text-amber-400 flex items-center gap-1"><Clock className="w-3.5 h-3.5" /> Pending Review</span>
                          )}
                        </td>
                        <td className="px-5 py-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Link
                              href={`/admin/review?session_id=${item.session_id}`}
                              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold transition flex items-center gap-1"
                              title="Inspect full session telemetry & snapshot"
                            >
                              <Eye className="w-3.5 h-3.5" /> Inspect
                            </Link>

                            {!isApproved && !isFlagged && (
                              <>
                                <button
                                  onClick={() => handleApproveSession(item.session_id, item.candidate_name)}
                                  className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition flex items-center gap-1"
                                  title="Approve session"
                                >
                                  <Check className="w-3.5 h-3.5" /> Approve
                                </button>
                                <button
                                  onClick={() => handleFlagViolation(item.session_id, item.candidate_name)}
                                  className="px-2.5 py-1 bg-red-600 hover:bg-red-500 text-white rounded-lg text-xs font-semibold transition flex items-center gap-1"
                                  title="Flag violation"
                                >
                                  <X className="w-3.5 h-3.5" /> Flag
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Audit Log Feed (1 Col) */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <History className="w-4 h-4 text-amber-400" /> Review Audit Log Feed
              </h2>
              <Link href="/admin/audit" className="text-xs text-amber-400 font-semibold hover:underline">
                View All →
              </Link>
            </div>

            <div className="space-y-3 pt-3">
              {auditLogs.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-6">No recent audit log actions recorded.</p>
              ) : (
                auditLogs.map((log) => (
                  <div key={log.id} className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-1 text-xs">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-amber-400 font-mono text-[11px]">{log.action}</span>
                      <span className="text-[10px] text-slate-500">{new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                    <p className="text-slate-300 text-[11px]">By: {log.user}</p>
                    {log.details && <p className="text-slate-500 text-[10px] truncate">{log.details}</p>}
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="pt-3 border-t border-slate-800 text-xs text-slate-500 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>Review decisions logged to immutable audit trail</span>
          </div>
        </div>

      </div>
    </div>
  );
}
