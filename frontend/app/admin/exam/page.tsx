"use client";
export const dynamic = "force-dynamic";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import {
  FileText,
  Calendar,
  Clock,
  Plus,
  ArrowRight,
  MoreVertical,
  Activity,
  PlayCircle,
  Search,
  Trash2,
  Edit,
  GraduationCap,
  Layers,
  CheckCircle2,
  AlertTriangle,
  Loader2
} from "lucide-react";
import Link from "next/link";
import toast from "react-hot-toast";

interface Exam {
  id: string;
  title: string;
  description: string;
  start_window: string;
  end_window: string;
  duration_minutes: number;
  status: string;
  created_at: string;
}

export default function ExamListPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  
  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search & Filter
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "PUBLISHED" | "DRAFT" | "ARCHIVED">("ALL");
  
  // Deleting state
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteExam, setConfirmDeleteExam] = useState<Exam | null>(null);

  useEffect(() => {
    if (!isLoading && (!isAuthenticated || (user && user.role !== "admin"))) {
      router.push("/dashboard");
    }
  }, [isLoading, isAuthenticated, user, router]);

  const fetchExams = async () => {
    try {
      setLoading(true);
      const data = await apiClient.get<Exam[]>("/api/exams");
      setExams(Array.isArray(data) ? data : []);
    } catch (err: any) {
      console.error("Failed to fetch exams", err);
      setExams([]);
      setError("Failed to load exams. Please try again later.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isLoading || !user) return;
    fetchExams();
  }, [isLoading, user]);

  const handleDeleteExam = async () => {
    if (!confirmDeleteExam) return;
    const examId = confirmDeleteExam.id;
    setDeletingId(examId);

    try {
      await apiClient.delete(`/api/exams/${examId}`);
      toast.success(`Exam "${confirmDeleteExam.title}" deleted successfully.`);
      setExams((prev) => prev.filter((e) => e.id !== examId));
      setConfirmDeleteExam(null);
    } catch (err: any) {
      console.error("Delete failed", err);
      toast.error(err?.message || "Failed to delete exam.");
    } finally {
      setDeletingId(null);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toUpperCase()) {
      case "PUBLISHED":
      case "LIVE":
        return "bg-emerald-50 text-emerald-700 border-emerald-200 font-bold";
      case "DRAFT":
        return "bg-slate-100 text-slate-700 border-slate-200";
      case "ARCHIVED":
        return "bg-stone-100 text-stone-600 border-stone-200";
      default:
        return "bg-blue-50 text-blue-700 border-blue-200";
    }
  };

  if (isLoading || !user) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="flex items-center gap-2 text-slate-500">
          <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
          <span>Loading Exam Center...</span>
        </div>
      </div>
    );
  }

  // Filtered Exams logic
  const filteredExams = exams.filter((exam) => {
    const matchesSearch =
      exam.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (exam.description && exam.description.toLowerCase().includes(searchTerm.toLowerCase()));

    if (!matchesSearch) return false;
    if (statusFilter !== "ALL" && exam.status.toUpperCase() !== statusFilter) return false;

    return true;
  });

  return (
    <div className="flex-1 w-full p-6 sm:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <Layers className="h-6 w-6 text-blue-600" />
            Institutional Exam Center
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Create, manage, and monitor AI-proctored institutional assessments.
          </p>
        </div>

        {["admin", "proctor"].includes(user.role) && (
          <div className="flex items-center gap-3">
            <Link
              href="/admin/exam/builder"
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition shadow-sm"
            >
              <Plus className="h-4 w-4" />
              Create New Exam
            </Link>
          </div>
        )}
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search exams by title or keyword..."
            className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
        </div>

        <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-lg w-full sm:w-auto overflow-x-auto">
          {(["ALL", "PUBLISHED", "DRAFT", "ARCHIVED"] as const).map((st) => (
            <button
              key={st}
              type="button"
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                statusFilter === st
                  ? "bg-white text-blue-600 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {st === "ALL" ? "All Exams" : st}
            </button>
          ))}
        </div>
      </div>

      {/* Main Grid */}
      <div>
        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          </div>
        ) : error ? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-red-600">
            {error}
          </div>
        ) : filteredExams.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center shadow-sm">
            <FileText className="mx-auto h-12 w-12 text-slate-300" />
            <h3 className="mt-4 text-lg font-bold text-slate-900">No exams match your criteria</h3>
            <p className="mt-1 text-sm text-slate-500">
              {searchTerm || statusFilter !== "ALL"
                ? "Try clearing your search or changing status filters."
                : "Get started by building your first examination."}
            </p>
            {["admin", "proctor"].includes(user.role) && !searchTerm && (
              <div className="mt-6">
                <Link
                  href="/admin/exam/builder"
                  className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition shadow-sm"
                >
                  <Plus className="h-4 w-4" />
                  Create New Exam
                </Link>
              </div>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {filteredExams.map((exam) => (
              <div
                key={exam.id}
                className="flex flex-col rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden hover:shadow-md transition-shadow group"
              >
                <div className="p-6 flex-1 space-y-4">
                  <div className="flex justify-between items-start">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border ${getStatusColor(
                        exam.status
                      )}`}
                    >
                      {exam.status}
                    </span>

                    {user.role === "admin" && (
                      <button
                        onClick={() => setConfirmDeleteExam(exam)}
                        className="text-slate-400 hover:text-red-600 p-1 rounded-lg hover:bg-red-50 transition-colors"
                        title="Delete Exam"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>

                  <div>
                    <h3
                      className="text-lg font-bold text-slate-900 line-clamp-1 group-hover:text-blue-600 transition-colors"
                      title={exam.title}
                    >
                      {exam.title}
                    </h3>

                    <p className="text-xs text-slate-500 line-clamp-2 mt-1 min-h-[32px]">
                      {exam.description || "No description provided."}
                    </p>
                  </div>

                  <div className="space-y-2 pt-2 border-t border-slate-100 text-xs text-slate-600">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5 text-slate-500">
                        <Clock className="h-3.5 w-3.5 text-slate-400" /> Duration:
                      </span>
                      <strong className="text-slate-800">{exam.duration_minutes} Minutes</strong>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5 text-slate-500">
                        <Calendar className="h-3.5 w-3.5 text-slate-400" /> Start:
                      </span>
                      <span className="text-slate-800 font-medium truncate max-w-[140px]">
                        {exam.start_window ? new Date(exam.start_window).toLocaleDateString() : "TBD"}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Footer Action Buttons */}
                <div className="bg-slate-50 px-6 py-3 border-t border-slate-100 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <Link
                      href={`/admin/exam/${exam.id}/edit`}
                      className="p-1.5 rounded-lg border border-slate-200 bg-white text-slate-600 hover:text-blue-600 hover:border-blue-400 transition"
                      title="Edit Settings"
                    >
                      <Edit className="h-3.5 w-3.5" />
                    </Link>

                    <Link
                      href={`/admin/exam/${exam.id}/grading`}
                      className="p-1.5 rounded-lg border border-slate-200 bg-white text-slate-600 hover:text-purple-600 hover:border-purple-400 transition"
                      title="Grading & Submissions"
                    >
                      <GraduationCap className="h-3.5 w-3.5" />
                    </Link>
                  </div>

                  <Link
                    href={`/admin/exam/${exam.id}/manage`}
                    className="inline-flex items-center gap-1 font-semibold text-blue-600 hover:text-blue-700 transition"
                  >
                    Manage Exam <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {confirmDeleteExam && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-md w-full p-6 space-y-4">
            <div className="flex items-center gap-3 text-red-600">
              <div className="p-3 bg-red-50 rounded-xl">
                <AlertTriangle className="h-6 w-6 text-red-600" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Delete Examination</h3>
                <p className="text-xs text-slate-500">This action cannot be undone</p>
              </div>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              Are you sure you want to delete <strong className="text-slate-900">"{confirmDeleteExam.title}"</strong>? All associated questions, enrollments, and session records will be permanently removed.
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setConfirmDeleteExam(null)}
                disabled={!!deletingId}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteExam}
                disabled={!!deletingId}
                className="flex items-center gap-2 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition text-xs font-semibold shadow-sm"
              >
                {deletingId && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Delete Exam
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
