"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient, AppealItem } from "@/services/apiClient";
import Sidebar from "@/components/Sidebar";
import {
  Scale,
  Search,
  Filter,
  AlertTriangle,
  Clock,
  CheckCircle2,
  XCircle,
  FileText,
  ChevronRight,
  ShieldAlert,
  ArrowRight,
  RefreshCw,
  SlidersHorizontal,
} from "lucide-react";

export default function AppealsListPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();

  const [appeals, setAppeals] = useState<AppealItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  // Restrict access to admin and reviewer
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/auth/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const fetchAppeals = async () => {
    setIsRefreshing(true);
    setError(null);
    try {
      const data = await apiClient.getAppeals();
      setAppeals(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load appeals");
      setAppeals([]);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    if (!authLoading && user && ["admin", "reviewer"].includes(user.role)) {
      void fetchAppeals();
    } else if (!authLoading && (!user || !["admin", "reviewer"].includes(user.role))) {
      setLoading(false);
    }
  }, [authLoading, user]);

  // Filtered and searched appeals
  const filteredAppeals = useMemo(() => {
    return appeals.filter((appeal) => {
      const matchesStatus =
        statusFilter === "ALL"
          ? true
          : statusFilter === "RESOLVED"
          ? ["RESOLVED", "UPHELD", "OVERTURNED", "REVERSED"].includes(appeal.status.toUpperCase())
          : appeal.status.toUpperCase() === statusFilter.toUpperCase();

      const query = searchQuery.trim().toLowerCase();
      const matchesSearch =
        !query ||
        appeal.case_id.toLowerCase().includes(query) ||
        appeal.candidate_name.toLowerCase().includes(query) ||
        appeal.exam_name.toLowerCase().includes(query) ||
        appeal.original_finding.toLowerCase().includes(query) ||
        (appeal.candidate_email && appeal.candidate_email.toLowerCase().includes(query));

      return matchesStatus && matchesSearch;
    });
  }, [appeals, statusFilter, searchQuery]);

  // Compute metric stats
  const stats = useMemo(() => {
    const total = appeals.length;
    const pending = appeals.filter((a) => a.status.toUpperCase() === "PENDING").length;
    const underReview = appeals.filter((a) => a.status.toUpperCase() === "UNDER_REVIEW").length;
    const resolved = appeals.filter((a) =>
      ["RESOLVED", "UPHELD", "OVERTURNED", "REVERSED"].includes(a.status.toUpperCase())
    ).length;
    return { total, pending, underReview, resolved };
  }, [appeals]);

  const renderStatusBadge = (status: string) => {
    const s = status.toUpperCase();
    if (s === "PENDING") {
      return (
        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200">
          <Clock className="w-3.5 h-3.5 mr-1 text-amber-600" />
          Pending
        </span>
      );
    }
    if (s === "UNDER_REVIEW") {
      return (
        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-800 border border-blue-200">
          <RefreshCw className="w-3.5 h-3.5 mr-1 text-blue-600" />
          Under Review
        </span>
      );
    }
    if (s === "RESOLVED" || s === "OVERTURNED" || s === "REVERSED") {
      return (
        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
          <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-600" />
          {s === "OVERTURNED" || s === "REVERSED" ? "Overturned (Passed)" : "Resolved"}
        </span>
      );
    }
    if (s === "UPHELD") {
      return (
        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-800 border border-rose-200">
          <XCircle className="w-3.5 h-3.5 mr-1 text-rose-600" />
          Upheld (Failed)
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
        {status}
      </span>
    );
  };

  if (authLoading) {
    return (
      <div className="flex h-96 items-center justify-center bg-slate-50">
        <div className="text-center text-slate-500 flex items-center gap-2">
          <RefreshCw className="w-5 h-5 animate-spin text-blue-600" />
          <span>Authenticating Appeals Access...</span>
        </div>
      </div>
    );
  }

  if (!user || !["admin", "reviewer"].includes(user.role)) {
    return (
      <div className="flex flex-1 min-h-screen bg-slate-50">
        <Sidebar />
        <main className="flex-1 p-8 flex items-center justify-center">
          <div className="bg-white rounded-2xl border border-red-200 p-8 max-w-md text-center shadow-sm">
            <div className="mx-auto w-12 h-12 bg-red-100 text-red-600 rounded-full flex items-center justify-center mb-4">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-slate-900 mb-2">Access Restricted</h2>
            <p className="text-sm text-slate-600 mb-6">
              The Appeals Center is strictly reserved for authorized proctors, reviewers, and administrators to ensure impartial case adjudication.
            </p>
            <button
              onClick={() => router.push("/admin/dashboard")}
              className="px-4 py-2 bg-slate-900 text-white text-sm font-medium rounded-lg hover:bg-slate-800 transition"
            >
              Return to Dashboard
            </button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="flex flex-1 min-h-screen bg-slate-50">
      <Sidebar />

      <main className="flex-1 p-6 sm:p-8 max-w-7xl mx-auto w-full">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-6 mb-8">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-blue-600 text-white rounded-xl shadow-sm">
                <Scale className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
                  Appeals Center
                </h1>
                <p className="text-slate-500 text-sm mt-0.5">
                  Independent secondary adjudication for candidate-contested examination findings.
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => void fetchAppeals()}
              disabled={isRefreshing}
              className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition shadow-sm disabled:opacity-60"
              title="Refresh appeals list"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin text-blue-600" : "text-slate-500"}`} />
              <span>Refresh</span>
            </button>
            <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-full bg-blue-50 text-blue-700 border border-blue-200">
              <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
              Reviewer Separation Active
            </span>
          </div>
        </div>

        {/* Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Total Appeals</p>
              <p className="text-3xl font-bold text-slate-900 mt-1">{stats.total}</p>
              <p className="text-xs text-slate-500 mt-1">Submitted by candidates</p>
            </div>
            <div className="p-3 bg-slate-100 text-slate-600 rounded-xl">
              <FileText className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-amber-600">Pending Review</p>
              <p className="text-3xl font-bold text-amber-600 mt-1">{stats.pending}</p>
              <p className="text-xs text-amber-700 mt-1">Requires reviewer assignment</p>
            </div>
            <div className="p-3 bg-amber-50 text-amber-600 rounded-xl">
              <Clock className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-blue-600">Under Review</p>
              <p className="text-3xl font-bold text-blue-600 mt-1">{stats.underReview}</p>
              <p className="text-xs text-blue-700 mt-1">Active adjudication</p>
            </div>
            <div className="p-3 bg-blue-50 text-blue-600 rounded-xl">
              <RefreshCw className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-emerald-600">Resolved Cases</p>
              <p className="text-3xl font-bold text-emerald-600 mt-1">{stats.resolved}</p>
              <p className="text-xs text-emerald-700 mt-1">Formal verdict issued</p>
            </div>
            <div className="p-3 bg-emerald-50 text-emerald-600 rounded-xl">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
        </div>

        {/* Filter and Search Bar */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden mb-6">
          <div className="p-4 border-b border-slate-200 bg-slate-50/70 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center space-x-3 flex-wrap gap-y-2">
              <div className="flex items-center space-x-2 text-slate-500 text-sm font-medium">
                <Filter className="w-4 h-4 text-slate-400" />
                <span>Filter by Status:</span>
              </div>
              <div className="flex items-center space-x-1.5 bg-slate-200/70 p-1 rounded-xl">
                {(["ALL", "PENDING", "UNDER_REVIEW", "RESOLVED"] as const).map((status) => {
                  const isActive = statusFilter === status;
                  return (
                    <button
                      key={status}
                      onClick={() => setStatusFilter(status)}
                      className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                        isActive
                          ? "bg-white text-blue-700 shadow-sm"
                          : "text-slate-600 hover:text-slate-900"
                      }`}
                    >
                      {status === "ALL" ? "All Appeals" : status.replace("_", " ")}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search candidate, exam, or Case ID..."
                className="pl-10 pr-4 py-2 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white w-full sm:w-80 transition"
              />
            </div>
          </div>

          {/* Appeals Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider font-semibold border-b border-slate-200">
                  <th className="px-6 py-4">Case ID</th>
                  <th className="px-6 py-4">Candidate Name</th>
                  <th className="px-6 py-4">Exam</th>
                  <th className="px-6 py-4">Original Finding</th>
                  <th className="px-6 py-4">Appeal Date</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-slate-500">
                      <div className="flex justify-center items-center gap-2">
                        <RefreshCw className="w-5 h-5 animate-spin text-blue-600" />
                        <span>Loading appeals queue...</span>
                      </div>
                    </td>
                  </tr>
                ) : filteredAppeals.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-slate-500">
                      <div className="max-w-sm mx-auto">
                        <Scale className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                        <p className="font-medium text-slate-700">No appeal cases match your filter</p>
                        <p className="text-xs text-slate-400 mt-1">Try resetting the status filter or clearing your search term.</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredAppeals.map((appeal) => {
                    const dateObj = new Date(appeal.appeal_date);
                    const formattedDate = !isNaN(dateObj.getTime())
                      ? dateObj.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
                      : appeal.appeal_date;
                    const formattedTime = !isNaN(dateObj.getTime())
                      ? dateObj.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })
                      : "";

                    return (
                      <tr key={appeal.id} className="hover:bg-slate-50/80 transition-colors group">
                        {/* Case ID */}
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2.5 py-1 rounded-md border border-blue-100">
                            {appeal.case_id}
                          </span>
                        </td>

                        {/* Candidate Name */}
                        <td className="px-6 py-4">
                          <div className="font-medium text-slate-900 text-sm">{appeal.candidate_name}</div>
                          {appeal.candidate_email && (
                            <div className="text-xs text-slate-500">{appeal.candidate_email}</div>
                          )}
                        </td>

                        {/* Exam */}
                        <td className="px-6 py-4">
                          <div className="text-sm font-medium text-slate-800">{appeal.exam_name}</div>
                          {appeal.original_reviewer_name && (
                            <div className="text-xs text-slate-400 mt-0.5">
                              Proctor: {appeal.original_reviewer_name}
                            </div>
                          )}
                        </td>

                        {/* Original Finding */}
                        <td className="px-6 py-4">
                          <div className="flex items-start gap-2 max-w-xs">
                            <div
                              className={`shrink-0 w-2 h-2 rounded-full mt-1.5 ${
                                appeal.risk_score > 80
                                  ? "bg-red-500"
                                  : appeal.risk_score > 50
                                  ? "bg-amber-500"
                                  : "bg-emerald-500"
                              }`}
                            />
                            <div>
                              <div className="text-xs font-semibold text-slate-800">
                                Score: {appeal.risk_score}/100
                              </div>
                              <p className="text-xs text-slate-500 line-clamp-2 mt-0.5">
                                {appeal.original_finding}
                              </p>
                            </div>
                          </div>
                        </td>

                        {/* Appeal Date */}
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-slate-800 font-medium">{formattedDate}</div>
                          <div className="text-xs text-slate-400">{formattedTime}</div>
                        </td>

                        {/* Status */}
                        <td className="px-6 py-4 whitespace-nowrap">
                          {renderStatusBadge(appeal.status)}
                        </td>

                        {/* Action Link */}
                        <td className="px-6 py-4 whitespace-nowrap text-right">
                          <Link
                            href={`/admin/appeals/${appeal.id}`}
                            className="inline-flex items-center gap-1 text-sm font-semibold text-blue-600 hover:text-blue-700 bg-blue-50/60 hover:bg-blue-100/70 px-3 py-1.5 rounded-lg transition"
                          >
                            <span>Adjudicate</span>
                            <ChevronRight className="w-4 h-4" />
                          </Link>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Information Banner */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm flex items-start gap-3.5">
          <div className="p-2 bg-blue-50 text-blue-700 rounded-lg shrink-0 mt-0.5">
            <Scale className="w-5 h-5" />
          </div>
          <div className="text-sm">
            <h4 className="font-semibold text-slate-900">ExamSentinel Integrity & Review Separation Policy</h4>
            <p className="text-slate-500 mt-1">
              To safeguard academic equity, all appeals are partitioned cryptographically from the original proctor. A secondary, independent reviewer conducts an uncompromised evaluation of frozen biometric telemetry, screen buffers, and student testimonies before any verdict is recorded.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
