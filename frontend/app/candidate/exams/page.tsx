"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import {
  BookOpen,
  Clock,
  Calendar,
  ChevronRight,
  Search,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ShieldCheck,
  PlayCircle
} from "lucide-react";
import toast from "react-hot-toast";

export const dynamic = "force-dynamic";

interface Exam {
  id: string;
  title: string;
  description: string;
  duration_minutes: number;
  late_entry_minutes?: number;
  start_window: string;
  end_window: string;
  status: string;
  total_marks?: number;
}

export default function CandidateExamsPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [filter, setFilter] = useState<"ALL" | "AVAILABLE" | "SCHEDULED">("ALL");

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isLoading || !user) return;
    
    const fetchExams = async () => {
      try {
        setLoading(true);
        const data = await apiClient.get<Exam[]>("/api/exams");
        setExams(Array.isArray(data) ? data : []);
      } catch (err: any) {
        console.error("Failed to fetch exams", err);
        toast.error("Failed to load your examinations.");
        setExams([]);
      } finally {
        setLoading(false);
      }
    };
    
    fetchExams();
  }, [isLoading, user]);

  if (isLoading || !user) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <div className="flex items-center gap-2 text-slate-500">
          <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
          <span>Loading Examination Portal...</span>
        </div>
      </div>
    );
  }

  // Calculate availability status
  const processedExams = exams.map((exam) => {
    const now = Date.now();
    const start = new Date(exam.start_window).getTime();
    const end = new Date(exam.end_window).getTime();

    let availability: "AVAILABLE" | "SCHEDULED" | "CLOSED" = "CLOSED";
    if (now < start) {
      availability = "SCHEDULED";
    } else if (now <= end) {
      availability = "AVAILABLE";
    } else {
      availability = "CLOSED";
    }

    return {
      ...exam,
      availability,
      canStart: availability === "AVAILABLE",
    };
  });

  const filteredExams = processedExams.filter((exam) => {
    const matchesSearch =
      exam.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (exam.description && exam.description.toLowerCase().includes(searchTerm.toLowerCase()));

    if (!matchesSearch) return false;
    if (filter !== "ALL" && exam.availability !== filter) return false;

    return true;
  });

  return (
    <main className="flex-1 flex flex-col overflow-y-auto pb-12">
      <div className="w-full max-w-7xl mx-auto p-6 sm:p-8 space-y-6">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
              <BookOpen className="h-6 w-6 text-blue-600" />
              My Scheduled Examinations
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Browse available assessments, check start windows, and launch proctored exams.
            </p>
          </div>
        </div>

        {/* Filter and Search Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="relative w-full sm:w-80">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search exam title or topic..."
              className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
          </div>

          <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-lg w-full sm:w-auto overflow-x-auto">
            {(["ALL", "AVAILABLE", "SCHEDULED"] as const).map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                  filter === f
                    ? "bg-white text-blue-600 shadow-sm"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {f === "ALL" ? "All Exams" : f === "AVAILABLE" ? "Available Now" : "Upcoming"}
              </button>
            ))}
          </div>
        </div>

        {/* Main Grid */}
        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          </div>
        ) : filteredExams.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-2xl border border-slate-200 p-8 space-y-3">
            <BookOpen className="h-12 w-12 text-slate-300 mx-auto" />
            <h3 className="text-lg font-bold text-slate-900">No examinations found</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              {searchTerm || filter !== "ALL"
                ? "No exams match your current search or filter criteria."
                : "No exams are currently assigned or published for your cohort."}
            </p>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            {filteredExams.map((exam) => (
              <div
                key={exam.id}
                className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm hover:shadow-md transition-all flex flex-col justify-between space-y-4"
              >
                <div className="space-y-3">
                  <div className="flex justify-between items-start gap-2">
                    <h3 className="font-bold text-lg text-slate-900 line-clamp-1" title={exam.title}>
                      {exam.title}
                    </h3>
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold shrink-0 border ${
                        exam.canStart
                          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                          : exam.availability === "SCHEDULED"
                          ? "bg-blue-50 text-blue-700 border-blue-200"
                          : "bg-slate-100 text-slate-600 border-slate-200"
                      }`}
                    >
                      {exam.canStart ? "AVAILABLE NOW" : exam.availability}
                    </span>
                  </div>

                  <p className="text-xs text-slate-500 line-clamp-2">
                    {exam.description || "No specific instructions specified for this examination."}
                  </p>

                  <div className="grid grid-cols-2 gap-2 text-xs text-slate-600 pt-2 border-t border-slate-100">
                    <div className="flex items-center gap-1.5 text-slate-600">
                      <Clock className="h-3.5 w-3.5 text-slate-400" />
                      <span><strong>{exam.duration_minutes}</strong> Minutes</span>
                    </div>

                    <div className="flex items-center gap-1.5 text-slate-600">
                      <Calendar className="h-3.5 w-3.5 text-slate-400" />
                      <span className="truncate">
                        {exam.start_window ? new Date(exam.start_window).toLocaleDateString() : "TBD"}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="pt-2">
                  <button
                    onClick={() => router.push(`/exam/readiness?exam_id=${exam.id}`)}
                    disabled={!exam.canStart}
                    className="w-full flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-bold text-white shadow-md hover:bg-blue-700 active:bg-blue-800 transition disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400 disabled:shadow-none"
                  >
                    {exam.canStart ? (
                      <>
                        <PlayCircle className="h-4 w-4" /> Start Exam & Check System
                      </>
                    ) : exam.availability === "SCHEDULED" ? (
                      "Scheduled for Later Date"
                    ) : (
                      "Exam Window Closed"
                    )}
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
