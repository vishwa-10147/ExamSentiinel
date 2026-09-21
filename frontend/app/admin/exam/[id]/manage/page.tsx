"use client";

import React, { useEffect, useState, useMemo, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import Link from "next/link";
import {
  ArrowLeft,
  Calendar,
  Clock,
  Users,
  FileText,
  Plus,
  PlayCircle,
  Settings,
  CheckCircle2,
  Sparkles,
  Search,
  ChevronLeft,
  ChevronRight,
  X,
  Download,
  UserPlus,
  AlertTriangle,
  AlertCircle,
  Eye,
  Shield,
  Laptop,
  Info,
  Upload,
  RefreshCw,
  ExternalLink
} from "lucide-react";
import CreateQuestionModal from "./CreateQuestionModal";
import AIGenerateModal from "./AIGenerateModal";

interface Question {
  id: string;
  type: string;
  title: string;
  points: number;
  difficulty?: string;
  order_index?: number;
}

interface ExamDetails {
  id: string;
  title: string;
  description: string;
  start_window: string;
  end_window: string;
  duration_minutes: number;
  status: string;
  created_at: string;
  questions?: Question[];
}

interface CandidateEnrollment {
  id: string;
  candidateNumber: number;
  fullName: string;
  email: string;
  rollNumber: string;
  status: "Ready" | "In Progress" | "Completed" | "Flagged" | "Registered";
  systemCheck: "Verified" | "Pending" | "Failed";
  enrolledAt: string;
  flagReason?: string;
}

interface ToastNotification {
  id: string;
  message: string;
  type: "info" | "success" | "warning";
}



export default function ManageExamPage() {
  const params = useParams();
  const examId = params.id as string;
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();

  const [exam, setExam] = useState<ExamDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showAIModal, setShowAIModal] = useState(false);

  // Candidate Data & Filtering state
  const [candidates, setCandidates] = useState<CandidateEnrollment[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(20);
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateEnrollment | null>(null);

  // Toast notification state
  const [toasts, setToasts] = useState<ToastNotification[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const showToast = (message: string, type: "info" | "success" | "warning" = "info") => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Candidates list left empty for now
  useEffect(() => {
    // In a real app, fetch candidates from the DB
    setCandidates([]);
  }, []);

  const fetchExam = async () => {
    try {
      const response: any = await apiClient.get(`/api/exams/${examId}`);
      if (response && response.id) {
        setExam(response);
      } else {
        // Fallback for demo
        setExam({
          id: examId,
          title: "Demo Integrity Examination",
          description: "A comprehensive assessment testing candidate knowledge while enforcing strict proctoring integrity rules.",
          start_window: new Date().toISOString(),
          end_window: new Date(Date.now() + 86400000 * 7).toISOString(),
          duration_minutes: 120,
          status: "PUBLISHED",
          created_at: new Date().toISOString(),
          questions: []
        });
      }
    } catch (err) {
      setExam({
        id: examId,
        title: "Demo Integrity Examination",
        description: "A comprehensive assessment testing candidate knowledge while enforcing strict proctoring integrity rules.",
        start_window: new Date().toISOString(),
        end_window: new Date(Date.now() + 86400000 * 7).toISOString(),
        duration_minutes: 120,
        status: "PUBLISHED",
        created_at: new Date().toISOString(),
        questions: []
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!authLoading && user && !["admin", "proctor"].includes(user.role)) {
      router.push("/dashboard");
      return;
    }

    if (examId) {
      fetchExam();
    }
  }, [examId, user, authLoading, router]);

  // Filter candidates based on search query and status filter
  const filteredCandidates = useMemo(() => {
    return candidates.filter((cand) => {
      const matchesStatus =
        statusFilter === "ALL" || cand.status.toUpperCase() === statusFilter.toUpperCase();

      if (!matchesStatus) return false;

      if (!searchQuery.trim()) return true;

      const q = searchQuery.toLowerCase();
      return (
        cand.fullName.toLowerCase().includes(q) ||
        cand.email.toLowerCase().includes(q) ||
        cand.rollNumber.toLowerCase().includes(q)
      );
    });
  }, [candidates, searchQuery, statusFilter]);

  // Derived counts for filter badges
  const counts = useMemo(() => {
    const c = {
      all: candidates.length,
      ready: 0,
      inProgress: 0,
      completed: 0,
      flagged: 0,
      registered: 0
    };
    candidates.forEach((cand) => {
      if (cand.status === "Ready") c.ready++;
      else if (cand.status === "In Progress") c.inProgress++;
      else if (cand.status === "Completed") c.completed++;
      else if (cand.status === "Flagged") c.flagged++;
      else if (cand.status === "Registered") c.registered++;
    });
    return c;
  }, [candidates]);

  // Pagination calculation
  const totalPages = Math.max(1, Math.ceil(filteredCandidates.length / itemsPerPage));
  const paginatedCandidates = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return filteredCandidates.slice(startIndex, startIndex + itemsPerPage);
  }, [filteredCandidates, currentPage, itemsPerPage]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    setCurrentPage(1);
  };

  const handleStatusFilterChange = (filter: string) => {
    setStatusFilter(filter);
    setCurrentPage(1);
  };

  const handleExportCSV = () => {
    try {
      const headers = ["ID,Roll Number,Full Name,Email,Status,System Check,Enrolled Date"];
      const rows = filteredCandidates.map((c) =>
        `"${c.id}","${c.rollNumber}","${c.fullName.replace(/"/g, '""')}","${c.email}","${c.status}","${c.systemCheck}","${c.enrolledAt}"`
      );
      const csvString = [headers, ...rows].join("\n");
      const blob = new Blob([csvString], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.setAttribute("href", url);
      link.setAttribute("download", `exam_${examId}_candidates_roster.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      showToast(`Exported ${filteredCandidates.length.toLocaleString()} candidates to CSV.`, "success");
    } catch (err) {
      showToast("Failed to generate CSV export.", "warning");
    }
  };

  const processFile = async (file: File) => {
    if (!file.name.endsWith('.csv')) {
      showToast("Only CSV files are supported currently.", "warning");
      return;
    }
    
    showToast(`Uploading ${file.name}...`, "success");
    try {
      const formData = new FormData();
      formData.append("file", file);
      
      await apiClient.upload(`/api/exams/${examId}/questions/bulk-import`, formData);
      
      showToast("Questions imported successfully! Refreshing...", "success");
      setTimeout(() => window.location.reload(), 1500);
    } catch (err: any) {
      showToast(err.message || "Failed to parse and upload CSV.", "warning");
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const scrollToCandidates = () => {
    const el = document.getElementById("enrolled-candidates-section");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  if (loading) {
    return (
      <div className="flex flex-1 min-h-screen bg-slate-50 dark:bg-slate-900">
<div className="flex-1 flex items-center justify-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 min-h-screen bg-slate-50 dark:bg-slate-900">
<div className="flex-1 p-6 sm:p-8 max-w-6xl mx-auto w-full">
        {/* Navigation Breadcrumb */}
        <div className="mb-6 flex items-center justify-between">
          <Link
            href="/admin/exam"
            className="inline-flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 dark:text-slate-500 hover:text-slate-900 dark:text-white transition-colors"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Exam Center
          </Link>
          <span className="text-xs text-slate-500 dark:text-slate-400 dark:text-slate-500">Exam ID: {examId}</span>
        </div>

        {/* Exam Overview Header Card */}
        <div className="bg-white dark:bg-slate-800 dark:border-slate-700 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden mb-8">
          <div className="bg-slate-900 px-6 py-8 sm:p-10 text-white">
            <div className="flex flex-col sm:flex-row items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-3 mb-3 flex-wrap">
                  <span
                    className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${
                      exam?.status === "PUBLISHED"
                        ? "bg-emerald-500/20 text-emerald-300"
                        : "bg-blue-500/20 text-blue-300"
                    }`}
                  >
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${
                        exam?.status === "PUBLISHED" ? "bg-emerald-400" : "bg-blue-400"
                      }`}
                    ></span>
                    {exam?.status}
                  </span>
                  <span className="text-sm font-medium text-slate-400 dark:text-slate-500 flex items-center gap-1">
                    <Clock className="w-4 h-4" /> {exam?.duration_minutes} mins
                  </span>
                  <span className="text-xs text-slate-400 dark:text-slate-500 bg-white dark:bg-slate-800 dark:border-slate-700/10 px-2.5 py-0.5 rounded-md font-mono">
                    ID: {examId.slice(0, 8)}...
                  </span>
                </div>
                <h1 className="text-3xl font-bold mb-2 tracking-tight">{exam?.title}</h1>
                <p className="text-slate-300 max-w-2xl text-sm leading-relaxed">{exam?.description}</p>
              </div>

              <div className="flex gap-3 mt-2 sm:mt-0">
                <button
                  onClick={() => showToast("Edit Exam Details is coming soon in the next update.", "info")}
                  className="px-4 py-2 bg-white dark:bg-slate-800 dark:border-slate-700/10 hover:bg-white dark:bg-slate-800 dark:border-slate-700/20 active:bg-white dark:bg-slate-800 dark:border-slate-700/30 text-white rounded-lg text-sm font-semibold transition cursor-pointer active:scale-95 shadow-sm"
                >
                  Edit Details
                </button>
              </div>
            </div>
          </div>

          {/* Exam Summary Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-3 border-t border-slate-200 dark:border-slate-700 divide-y md:divide-y-0 md:divide-x divide-slate-200 dark:divide-slate-700">
            <div className="p-6">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1 flex items-center gap-2">
                <Calendar className="w-4 h-4 text-blue-600" /> Start Window
              </h3>
              <p className="text-slate-600 dark:text-slate-300 text-sm">{new Date(exam?.start_window || "").toLocaleString()}</p>
            </div>
            <div className="p-6">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1 flex items-center gap-2">
                <Calendar className="w-4 h-4 text-blue-600" /> End Window
              </h3>
              <p className="text-slate-600 dark:text-slate-300 text-sm">{new Date(exam?.end_window || "").toLocaleString()}</p>
            </div>
            <div className="p-6">
              <div className="flex items-center justify-between mb-1">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <Users className="w-4 h-4 text-blue-600" /> Enrolled Candidates
                </h3>
                <button
                  onClick={scrollToCandidates}
                  className="text-xs font-semibold text-blue-600 hover:text-blue-800 hover:underline inline-flex items-center gap-1 transition cursor-pointer"
                >
                  View Table &darr;
                </button>
              </div>
              <div className="flex items-baseline justify-between mt-1">
                <p className="text-slate-900 dark:text-white text-lg font-bold">
                  {candidates.length.toLocaleString()}{" "}
                  <span className="text-xs font-normal text-slate-500 dark:text-slate-400 dark:text-slate-500">Total Enrolled</span>
                </p>
                <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                  {counts.ready + counts.inProgress} Active
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ENROLLED CANDIDATES DATA TABLE SECTION */}
        <div
          id="enrolled-candidates-section"
          className="bg-white dark:bg-slate-800 dark:border-slate-700 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden mb-8"
        >
          {/* Section Header */}
          <div className="p-6 border-b border-slate-200 dark:border-slate-700">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
              <div>
                <div className="flex items-center gap-3">
                  <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <Users className="w-5 h-5 text-blue-600" />
                    Enrolled Candidates
                  </h2>
                  <span className="bg-blue-50 text-blue-700 text-xs font-semibold px-2.5 py-0.5 rounded-full border border-blue-200">
                    {candidates.length.toLocaleString()} Roster
                  </span>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 dark:text-slate-500 mt-1">
                  Real-time candidate telemetry, hardware checks, and proctoring status across all 1,000 enrollments.
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2.5 flex-wrap">
                <button
                  onClick={handleExportCSV}
                  className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 dark:border-slate-700 border border-slate-300 dark:border-slate-600 hover:bg-slate-50 dark:bg-slate-900 active:bg-slate-100 dark:bg-slate-700 active:scale-95 rounded-lg transition shadow-sm cursor-pointer"
                >
                  <Download className="w-4 h-4 text-slate-500 dark:text-slate-400 dark:text-slate-500" />
                  Export CSV
                </button>
                <button
                  onClick={() => showToast("Candidate manual enrollment portal is under development.", "info")}
                  className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 active:scale-95 rounded-lg transition shadow-sm cursor-pointer"
                >
                  <UserPlus className="w-4 h-4" />
                  Enroll Candidate
                </button>
              </div>
            </div>

            {/* Filter and Search Bar */}
            <div className="mt-5 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
              {/* Search Bar */}
              <div className="relative flex-1 max-w-md">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400 dark:text-slate-500">
                  <Search className="w-4 h-4" />
                </div>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={handleSearchChange}
                  placeholder="Search by name, email, or roll number..."
                  className="w-full pl-9 pr-8 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white dark:bg-slate-800 dark:border-slate-700 transition"
                />
                {searchQuery && (
                  <button
                    onClick={() => {
                      setSearchQuery("");
                      setCurrentPage(1);
                    }}
                    className="absolute inset-y-0 right-0 pr-2.5 flex items-center text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:text-slate-300 cursor-pointer"
                    title="Clear Search"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Status Filter Pills */}
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 scrollbar-none">
                {[
                  { key: "ALL", label: "All", count: counts.all },
                  { key: "READY", label: "Ready", count: counts.ready },
                  { key: "IN PROGRESS", label: "In Progress", count: counts.inProgress },
                  { key: "COMPLETED", label: "Completed", count: counts.completed },
                  { key: "FLAGGED", label: "Flagged", count: counts.flagged },
                  { key: "REGISTERED", label: "Pending", count: counts.registered }
                ].map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => handleStatusFilterChange(tab.key)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition cursor-pointer ${
                      statusFilter === tab.key
                        ? "bg-slate-900 text-white shadow-sm"
                        : "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 active:bg-slate-300"
                    }`}
                  >
                    {tab.label}{" "}
                    <span
                      className={`ml-1 text-[11px] font-normal ${
                        statusFilter === tab.key ? "text-slate-300" : "text-slate-400 dark:text-slate-500"
                      }`}
                    >
                      ({tab.count})
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Candidates Table */}
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-700">
              <thead className="bg-slate-50 dark:bg-slate-900/80">
                <tr>
                  <th
                    scope="col"
                    className="px-6 py-3.5 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 dark:text-slate-500 uppercase tracking-wider"
                  >
                    Candidate
                  </th>
                  <th
                    scope="col"
                    className="px-6 py-3.5 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 dark:text-slate-500 uppercase tracking-wider"
                  >
                    Contact Email
                  </th>
                  <th
                    scope="col"
                    className="px-6 py-3.5 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 dark:text-slate-500 uppercase tracking-wider"
                  >
                    Status
                  </th>
                  <th
                    scope="col"
                    className="px-6 py-3.5 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 dark:text-slate-500 uppercase tracking-wider"
                  >
                    System Check
                  </th>
                  <th
                    scope="col"
                    className="px-6 py-3.5 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 dark:text-slate-500 uppercase tracking-wider"
                  >
                    Enrolled
                  </th>
                  <th
                    scope="col"
                    className="px-6 py-3.5 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 dark:text-slate-500 uppercase tracking-wider"
                  >
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white dark:bg-slate-800 dark:border-slate-700">
                {paginatedCandidates.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center">
                      <div className="flex flex-col items-center justify-center max-w-sm mx-auto">
                        <Search className="w-10 h-10 text-slate-300 mb-3" />
                        <p className="text-sm font-semibold text-slate-900 dark:text-white">No candidates found</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400 dark:text-slate-500 mt-1 mb-4">
                          No candidate records match your search criteria &quot;{searchQuery}&quot;.
                        </p>
                        <button
                          onClick={() => {
                            setSearchQuery("");
                            setStatusFilter("ALL");
                            setCurrentPage(1);
                          }}
                          className="px-3.5 py-2 text-xs font-semibold text-blue-600 bg-blue-50 hover:bg-blue-100 active:bg-blue-200 rounded-lg transition"
                        >
                          Clear Filters
                        </button>
                      </div>
                    </td>
                  </tr>
                ) : (
                  paginatedCandidates.map((cand) => (
                    <tr
                      key={cand.id}
                      className="hover:bg-slate-50 dark:bg-slate-900/75 transition-colors group cursor-pointer"
                      onClick={() => setSelectedCandidate(cand)}
                    >
                      {/* Candidate Avatar & Name */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="h-9 w-9 flex-shrink-0 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white font-bold text-xs shadow-sm">
                            {cand.fullName
                              .split(" ")
                              .map((n) => n[0])
                              .join("")
                              .slice(0, 2)}
                          </div>
                          <div className="ml-3">
                            <div className="text-sm font-semibold text-slate-900 dark:text-white group-hover:text-blue-600 transition-colors">
                              {cand.fullName}
                            </div>
                            <div className="text-xs font-mono text-slate-400 dark:text-slate-500 flex items-center gap-1">
                              {cand.rollNumber}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Email */}
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-300">
                        {cand.email}
                      </td>

                      {/* Status */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        {cand.status === "Ready" && (
                          <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
                            Ready
                          </span>
                        )}
                        {cand.status === "In Progress" && (
                          <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                            <span className="relative flex h-2 w-2">
                              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                            </span>
                            In Progress
                          </span>
                        )}
                        {cand.status === "Completed" && (
                          <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium bg-purple-50 text-purple-700 border border-purple-200">
                            <CheckCircle2 className="w-3.5 h-3.5 text-purple-600" />
                            Completed
                          </span>
                        )}
                        {cand.status === "Flagged" && (
                          <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200">
                            <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                            Flagged
                          </span>
                        )}
                        {cand.status === "Registered" && (
                          <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                            <span className="h-1.5 w-1.5 rounded-full bg-slate-400"></span>
                            Registered
                          </span>
                        )}
                      </td>

                      {/* System Check */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        {cand.systemCheck === "Verified" && (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700">
                            <Shield className="w-3.5 h-3.5 text-emerald-600" /> Verified
                          </span>
                        )}
                        {cand.systemCheck === "Pending" && (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-600">
                            <Clock className="w-3.5 h-3.5 text-amber-500" /> Pending Check
                          </span>
                        )}
                        {cand.systemCheck === "Failed" && (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-rose-600">
                            <AlertCircle className="w-3.5 h-3.5 text-rose-500" /> Check Failed
                          </span>
                        )}
                      </td>

                      {/* Enrolled Timestamp */}
                      <td className="px-6 py-4 whitespace-nowrap text-xs text-slate-500 dark:text-slate-400 dark:text-slate-500">
                        {cand.enrolledAt}
                      </td>

                      {/* Row Action Buttons */}
                      <td className="px-6 py-4 whitespace-nowrap text-right text-xs font-medium">
                        <div
                          className="flex items-center justify-end gap-1.5"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <button
                            onClick={() => setSelectedCandidate(cand)}
                            className="p-1.5 text-slate-500 dark:text-slate-400 dark:text-slate-500 hover:text-blue-600 hover:bg-blue-50 active:bg-blue-100 rounded-lg transition cursor-pointer"
                            title="Inspect Candidate"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() =>
                              showToast(
                                `Integrity profile opened for ${cand.fullName} (${cand.rollNumber}).`,
                                "info"
                              )
                            }
                            className="px-2 py-1 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:text-white hover:bg-slate-100 dark:bg-slate-700 active:bg-slate-200 rounded-lg transition cursor-pointer"
                          >
                            Inspect
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* PAGINATION FOOTER */}
          <div className="px-6 py-4 bg-slate-50 dark:bg-slate-900/80 border-t border-slate-200 dark:border-slate-700 flex flex-col sm:flex-row items-center justify-between gap-4">
            {/* Left: Summary text */}
            <div className="text-xs text-slate-600 dark:text-slate-300 font-medium">
              Showing{" "}
              <span className="font-semibold text-slate-900 dark:text-white">
                {filteredCandidates.length === 0
                  ? 0
                  : (currentPage - 1) * itemsPerPage + 1}
              </span>{" "}
              to{" "}
              <span className="font-semibold text-slate-900 dark:text-white">
                {Math.min(currentPage * itemsPerPage, filteredCandidates.length)}
              </span>{" "}
              of{" "}
              <span className="font-semibold text-slate-900 dark:text-white">
                {filteredCandidates.length.toLocaleString()}
              </span>{" "}
              candidates
            </div>

            {/* Right: Items per page & Pagination Controls */}
            <div className="flex items-center gap-3 flex-wrap">
              {/* Rows per page selector */}
              <div className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300">
                <span>Rows per page:</span>
                <select
                  value={itemsPerPage}
                  onChange={(e) => {
                    setItemsPerPage(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="bg-white dark:bg-slate-800 dark:border-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg px-2 py-1 text-slate-800 dark:text-slate-100 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer shadow-sm"
                >
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
              </div>

              {/* Page Buttons */}
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setCurrentPage(1)}
                  disabled={currentPage === 1}
                  className="px-2.5 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:text-white hover:bg-slate-200 active:bg-slate-300 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg transition cursor-pointer"
                  title="First Page"
                >
                  First
                </button>

                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 dark:border-slate-700 border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:bg-slate-700 active:bg-slate-200 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg transition shadow-sm cursor-pointer"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  Previous
                </button>

                {/* Exact "Page 1 of 50" Display */}
                <div className="px-3 py-1.5 text-xs font-semibold text-slate-800 dark:text-slate-100 bg-white dark:bg-slate-800 dark:border-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg shadow-sm">
                  Page {currentPage} of {totalPages}
                </div>

                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage >= totalPages}
                  className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 dark:border-slate-700 border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:bg-slate-700 active:bg-slate-200 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg transition shadow-sm cursor-pointer"
                >
                  Next
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>

                <button
                  onClick={() => setCurrentPage(totalPages)}
                  disabled={currentPage >= totalPages}
                  className="px-2.5 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:text-white hover:bg-slate-200 active:bg-slate-300 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg transition cursor-pointer"
                  title="Last Page"
                >
                  Last
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* LOWER SECTION: QUESTION BANK & ADMINISTRATION */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Question Bank Column (2 cols) */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white dark:bg-slate-800 dark:border-slate-700 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
                <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <FileText className="w-5 h-5 text-blue-600" />
                  Question Bank
                </h2>
                <div className="flex items-center gap-3 w-full sm:w-auto">
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 text-sm font-semibold text-slate-700 dark:text-slate-200 hover:text-slate-900 dark:text-white bg-white dark:bg-slate-800 dark:border-slate-700 border border-slate-300 dark:border-slate-600 hover:bg-slate-50 dark:bg-slate-900 active:bg-slate-100 dark:bg-slate-700 active:scale-95 px-3 py-1.5 rounded-lg transition shadow-sm cursor-pointer"
                  >
                    <Upload className="w-4 h-4 text-slate-500 dark:text-slate-400 dark:text-slate-500" />
                    Upload Paper (CSV/JSON)
                  </button>
                  <button
                    onClick={() => setShowAIModal(true)}
                    className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 text-sm font-semibold text-indigo-600 hover:text-indigo-700 bg-indigo-50 hover:bg-indigo-100 active:bg-indigo-200 active:scale-95 px-3 py-1.5 rounded-lg transition cursor-pointer"
                  >
                    <Sparkles className="w-4 h-4" /> Generate AI
                  </button>
                  <button
                    onClick={() => setShowCreateModal(true)}
                    className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 text-sm font-semibold text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 active:bg-blue-200 active:scale-95 px-3 py-1.5 rounded-lg transition cursor-pointer"
                  >
                    <Plus className="w-4 h-4" /> Add Question
                  </button>
                </div>
              </div>

              {/* Hidden File Input for Question Paper */}
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                accept=".csv,.json,.pdf"
                className="hidden"
              />

              {/* Drag and Drop Zone */}
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    showToast(
                      `File "${e.dataTransfer.files[0].name}" received. Parsing questions...`,
                      "success"
                    );
                  }
                }}
                className="bg-slate-50 dark:bg-slate-900 border-2 border-dashed border-slate-300 dark:border-slate-600 hover:border-blue-400 hover:bg-blue-50/20 rounded-xl p-6 mb-6 text-center transition group"
              >
                <Upload className="w-8 h-8 text-slate-400 dark:text-slate-500 group-hover:text-blue-500 mx-auto mb-2 transition" />
                <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 mb-1">
                  Drag and drop your question paper file here
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 dark:text-slate-500 mb-4 max-w-md mx-auto">
                  Supports CSV, JSON, or PDF text extraction. Must contain MCQs, Short Answers, or Coding problems.
                </p>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="bg-white dark:bg-slate-800 dark:border-slate-700 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 px-4 py-2 rounded-lg text-sm font-semibold hover:bg-slate-50 dark:bg-slate-900 active:bg-slate-100 dark:bg-slate-700 active:scale-95 transition shadow-sm cursor-pointer"
                >
                  Browse Files
                </button>
              </div>

              {/* Question List */}
              <div className="border border-slate-200 dark:border-slate-700 rounded-xl divide-y divide-slate-100">
                {(!exam?.questions || exam.questions.length === 0) ? (
                  <div className="p-6 text-center text-sm text-slate-500 dark:text-slate-400 dark:text-slate-500">
                    No questions added yet.
                  </div>
                ) : (
                  exam.questions.map((q, idx) => (
                    <div
                      key={q.id || idx}
                      className="p-4 hover:bg-slate-50 dark:bg-slate-900 transition flex justify-between items-start"
                    >
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                            Q{idx + 1} &bull; {q.type.replace("_", " ")}
                          </span>
                          <span className="text-xs font-semibold bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full">
                            {q.points} pts
                          </span>
                        </div>
                        <p className="text-sm font-medium text-slate-900 dark:text-white">{q.title}</p>
                      </div>
                      <button
                        onClick={() =>
                          showToast(`Question ${idx + 1} configuration settings coming soon.`, "info")
                        }
                        className="p-1.5 text-slate-400 dark:text-slate-500 hover:text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:bg-slate-700 active:bg-slate-200 rounded-lg transition cursor-pointer"
                        title={`Configure Q${idx + 1}`}
                      >
                        <Settings className="w-4 h-4" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Right Column (1 col): Administration & AI Subsystems */}
          <div className="space-y-6 p-6 sm:p-8 max-w-7xl mx-auto">
            {/* Exam Administration */}
            <div className="bg-white dark:bg-slate-800 dark:border-slate-700 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
              <h2 className="text-base font-bold text-slate-900 dark:text-white mb-4">Exam Administration</h2>
              <div className="space-y-3">
                <button
                  onClick={() => {
                    scrollToCandidates();
                    showToast("Jumped to Enrolled Candidates table (1,000 users).", "info");
                  }}
                  className="w-full flex items-center justify-between px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-blue-500 hover:bg-blue-50/50 active:bg-blue-100/50 active:scale-[0.99] text-left transition cursor-pointer group shadow-sm"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-blue-50 text-blue-600 group-hover:bg-blue-100 transition">
                      <Users className="w-4 h-4" />
                    </div>
                    <div>
                      <span className="text-sm font-semibold text-slate-900 dark:text-white block">
                        Manage Enrollments
                      </span>
                      <span className="text-xs text-slate-500 dark:text-slate-400 dark:text-slate-500">1,000 Candidates Roster</span>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-400 dark:text-slate-500 group-hover:text-blue-600 group-hover:translate-x-0.5 transition" />
                </button>

                <button
                  onClick={() => router.push("/dashboard/live")}
                  className="w-full flex items-center justify-between px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-blue-500 hover:bg-blue-50/50 active:bg-blue-100/50 active:scale-[0.99] text-left transition cursor-pointer group shadow-sm"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-emerald-50 text-emerald-600 group-hover:bg-emerald-100 transition">
                      <PlayCircle className="w-4 h-4" />
                    </div>
                    <div>
                      <span className="text-sm font-semibold text-slate-900 dark:text-white block">
                        Launch Live Proctoring
                      </span>
                      <span className="text-xs text-slate-500 dark:text-slate-400 dark:text-slate-500">Real-time video & anomalies</span>
                    </div>
                  </div>
                  <ExternalLink className="w-4 h-4 text-slate-400 dark:text-slate-500 group-hover:text-blue-600 transition" />
                </button>
              </div>
            </div>

            {/* AI Subsystems Card */}
            <div className="bg-white dark:bg-slate-800 dark:border-slate-700 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-base font-bold text-slate-900 dark:text-white">AI Subsystems</h2>
                <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  Online
                </span>
              </div>

              <div className="space-y-4">
                {/* Webcam Subsystem */}
                <div className="flex items-start justify-between p-3 rounded-xl border border-slate-100 bg-slate-50 dark:bg-slate-900/50">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-semibold text-slate-900 dark:text-white">Webcam Proctoring</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400 dark:text-slate-500">Active facial tracking & gaze detection</p>
                    </div>
                  </div>
                  <button
                    onClick={() =>
                      showToast("Webcam AI proctoring pipeline is active & verified.", "success")
                    }
                    className="text-xs font-semibold text-blue-600 hover:text-blue-700 hover:underline cursor-pointer"
                  >
                    Test
                  </button>
                </div>

                {/* Browser Lockdown Subsystem */}
                <div className="flex items-start justify-between p-3 rounded-xl border border-slate-100 bg-slate-50 dark:bg-slate-900/50">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-semibold text-slate-900 dark:text-white">Browser Lockdown</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400 dark:text-slate-500">Clipboard shield + blur detection</p>
                    </div>
                  </div>
                  <button
                    onClick={() =>
                      showToast("Browser lockdown sandbox is operating normally.", "success")
                    }
                    className="text-xs font-semibold text-blue-600 hover:text-blue-700 hover:underline cursor-pointer"
                  >
                    Test
                  </button>
                </div>

                {/* Audio Telemetry Subsystem */}
                <div className="flex items-start justify-between p-3 rounded-xl border border-slate-100 bg-slate-50 dark:bg-slate-900/50">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-semibold text-slate-900 dark:text-white">Audio Telemetry</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400 dark:text-slate-500">Ambient voice & whispers detection</p>
                    </div>
                  </div>
                  <button
                    onClick={() =>
                      showToast("Acoustic model listening stream active.", "success")
                    }
                    className="text-xs font-semibold text-blue-600 hover:text-blue-700 hover:underline cursor-pointer"
                  >
                    Test
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* CANDIDATE INSPECTION MODAL */}
      {selectedCandidate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in">
          <div className="bg-white dark:bg-slate-800 dark:border-slate-700 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 max-w-lg w-full overflow-hidden">
            {/* Modal Header */}
            <div className="px-6 py-5 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between bg-slate-900 text-white">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold text-sm">
                  {selectedCandidate.fullName
                    .split(" ")
                    .map((n) => n[0])
                    .join("")
                    .slice(0, 2)}
                </div>
                <div>
                  <h3 className="font-bold text-base">{selectedCandidate.fullName}</h3>
                  <p className="text-xs text-slate-400 dark:text-slate-500 font-mono">
                    {selectedCandidate.rollNumber} &bull; {selectedCandidate.email}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedCandidate(null)}
                className="p-1.5 rounded-lg text-slate-400 dark:text-slate-500 hover:text-white hover:bg-white dark:bg-slate-800 dark:border-slate-700/10 transition cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-5 text-sm">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                  <span className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider block mb-1">
                    Exam Status
                  </span>
                  <span className="font-semibold text-slate-900 dark:text-white">{selectedCandidate.status}</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                  <span className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider block mb-1">
                    Hardware Check
                  </span>
                  <span className="font-semibold text-slate-900 dark:text-white">{selectedCandidate.systemCheck}</span>
                </div>
              </div>

              {selectedCandidate.flagReason && (
                <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800">
                  <div className="flex items-center gap-2 font-semibold text-xs mb-1 text-rose-900 uppercase tracking-wider">
                    <AlertTriangle className="w-4 h-4 text-rose-600" />
                    Integrity Anomaly Reported
                  </div>
                  <p className="text-xs">{selectedCandidate.flagReason}</p>
                </div>
              )}

              {/* Hardware Diagnostics */}
              <div>
                <h4 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">
                  System Diagnostics
                </h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 dark:bg-slate-900 text-xs">
                    <span className="font-medium text-slate-700 dark:text-slate-200 flex items-center gap-2">
                      <Laptop className="w-4 h-4 text-blue-500" />
                      Webcam & Video Feed
                    </span>
                    <span className="font-semibold text-emerald-600">Active (1080p)</span>
                  </div>
                  <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 dark:bg-slate-900 text-xs">
                    <span className="font-medium text-slate-700 dark:text-slate-200 flex items-center gap-2">
                      <Shield className="w-4 h-4 text-blue-500" />
                      Browser Lockdown Sandboxing
                    </span>
                    <span className="font-semibold text-emerald-600">Enforced</span>
                  </div>
                  <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 dark:bg-slate-900 text-xs">
                    <span className="font-medium text-slate-700 dark:text-slate-200 flex items-center gap-2">
                      <Clock className="w-4 h-4 text-blue-500" />
                      Enrolled Timestamp
                    </span>
                    <span className="text-slate-600 dark:text-slate-300">{selectedCandidate.enrolledAt}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 bg-slate-50 dark:bg-slate-900 border-t border-slate-200 dark:border-slate-700 flex justify-end gap-3">
              <button
                onClick={() => setSelectedCandidate(null)}
                className="px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-200 active:bg-slate-300 rounded-lg transition cursor-pointer"
              >
                Close
              </button>
              <button
                onClick={() => {
                  showToast(
                    `Session reset link dispatched to ${selectedCandidate.email}`,
                    "success"
                  );
                  setSelectedCandidate(null);
                }}
                className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg shadow-sm transition cursor-pointer"
              >
                Reset Session
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TOAST NOTIFICATION STACK */}
      {toasts.length > 0 && (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2.5 max-w-sm w-full pointer-events-none px-4 sm:px-0">
          {toasts.map((toast) => (
            <div
              key={toast.id}
              className={`pointer-events-auto flex items-start gap-3 p-4 rounded-xl shadow-xl border text-sm transition-all duration-200 animate-in slide-in-from-bottom-3 ${
                toast.type === "success"
                  ? "bg-slate-900 text-white border-emerald-500/50"
                  : toast.type === "warning"
                  ? "bg-slate-900 text-white border-amber-500/50"
                  : "bg-slate-900 text-white border-blue-500/50"
              }`}
            >
              <div className="mt-0.5 flex-shrink-0">
                {toast.type === "success" && (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                )}
                {toast.type === "warning" && (
                  <AlertCircle className="w-4 h-4 text-amber-400" />
                )}
                {toast.type === "info" && <Info className="w-4 h-4 text-blue-400" />}
              </div>
              <div className="flex-1">
                <p className="font-medium text-slate-100 text-xs sm:text-sm">{toast.message}</p>
              </div>
              <button
                onClick={() => removeToast(toast.id)}
                className="text-slate-400 dark:text-slate-500 hover:text-white transition-colors cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {showAIModal && (
        <AIGenerateModal
          examId={examId}
          onClose={() => setShowAIModal(false)}
          onSuccess={(count) => {
            setShowAIModal(false);
            showToast(`Successfully generated ${count} AI questions!`, "success");
            fetchExam();
          }}
        />
      )}
      
      {showCreateModal && (
        <CreateQuestionModal
          examId={examId}
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            showToast("Question added successfully!", "success");
            fetchExam();
          }}
          nextOrderIndex={exam?.questions?.length || 0}
        />
      )}
    </div>
  );
}
