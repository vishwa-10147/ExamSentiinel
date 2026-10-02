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
  const [completedMap, setCompletedMap] = useState<Record<string, string>>({}); // exam_id -> session_id
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [filter, setFilter] = useState<"ALL" | "AVAILABLE" | "SCHEDULED" | "COMPLETED">("ALL");

  const [now, setNow] = useState<number>(Date.now());

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    const timer = setInterval(() => {
      setNow(Date.now());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (isLoading || !user) return;
    
    const fetchData = async () => {
      try {
        setLoading(true);
        const [examsData, historyData] = await Promise.all([
          apiClient.get<Exam[]>("/api/exams").catch(() => []),
          apiClient.get<any[]>("/api/results/history").catch(() => []),
        ]);

        const publishedExams = Array.isArray(examsData)
          ? examsData.filter((e) => e.status && (e.status.toUpperCase() === "PUBLISHED" || e.status.toUpperCase() === "LIVE"))
          : [];
        setExams(publishedExams);
        
        const map: Record<string, string> = {};
        if (Array.isArray(historyData)) {
          historyData.forEach((h: any) => {
            if (h.exam_id && h.session_id) {
              map[h.exam_id] = h.session_id;
            }
          });
        }
        setCompletedMap(map);
      } catch (err: any) {
        console.error("Failed to fetch exams", err);
        toast.error("Failed to load your examinations.");
        setExams([]);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
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

  // Format date nicely with time
  const formatWindowDate = (dStr: string) => {
    if (!dStr) return "TBD";
    const d = new Date(dStr);
    if (isNaN(d.getTime())) return "TBD";
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  };

  // Safe UTC parser
  const parseDate = (dStr: string) => {
    if (!dStr) return 0;
    let s = dStr;
    if (!s.endsWith("Z") && !s.includes("+") && !s.includes("-", 10)) {
      s += "Z";
    }
    return new Date(s).getTime();
  };

  // Calculate availability status
  const processedExams = exams.map((exam) => {
    const isCompleted = !!completedMap[exam.id];
    const sessionId = completedMap[exam.id];

    if (isCompleted) {
      return {
        ...exam,
        availability: "COMPLETED" as const,
        sessionId,
        countdownText: "Completed",
        canStart: false,
      };
    }

    const start = parseDate(exam.start_window);
    const end = parseDate(exam.end_window);

    let availability: "AVAILABLE" | "SCHEDULED" | "CLOSED" | "COMPLETED" = "CLOSED";
    let countdownText = "";

    if (now < start) {
      availability = "SCHEDULED";
      const diffSec = Math.ceil((start - now) / 1000);
      if (diffSec <= 3600) {
        const mins = Math.floor(diffSec / 60);
        const secs = diffSec % 60;
        countdownText = `Starts in ${mins}m ${secs < 10 ? "0" : ""}${secs}s`;
      } else {
        countdownText = `Scheduled for ${formatWindowDate(exam.start_window)}`;
      }
    } else if (now <= end) {
      availability = "AVAILABLE";
    } else {
      availability = "CLOSED";
    }

    return {
      ...exam,
      availability,
      countdownText,
      canStart: availability === "AVAILABLE",
    };
  });

  const filteredExams = processedExams.filter((exam) => {
    const matchesSearch =
      exam.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (exam.description && exam.description.toLowerCase().includes(searchTerm.toLowerCase()));

    if (!matchesSearch) return false;

    if (filter === "COMPLETED") {
      return exam.availability === "COMPLETED";
    }

    // In ALL, AVAILABLE, SCHEDULED tabs: hide COMPLETED exams so candidates see only active/upcoming ones!
    if (exam.availability === "COMPLETED") return false;

    if (filter === "AVAILABLE") return exam.availability === "AVAILABLE";
    if (filter === "SCHEDULED") return exam.availability === "SCHEDULED";

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
              Browse available assessments, check start windows, launch proctored exams, and view past results.
            </p>
          </div>
          <button
            onClick={() => router.push("/candidate/results")}
            className="self-start sm:self-auto px-4 py-2 bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 rounded-xl text-xs font-bold transition flex items-center gap-1.5 shadow-sm"
          >
            <ShieldCheck className="h-4 w-4" /> View All Exam Results →
          </button>
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
            {(["ALL", "AVAILABLE", "SCHEDULED", "COMPLETED"] as const).map((f) => (
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
                {f === "ALL" ? "Active Exams" : f === "AVAILABLE" ? "Available Now" : f === "SCHEDULED" ? "Upcoming" : "Completed"}
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
                : "No exams are currently assigned or active for your cohort."}
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
                        exam.availability === "COMPLETED"
                          ? "bg-purple-50 text-purple-700 border-purple-200"
                          : exam.canStart
                          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                          : exam.availability === "SCHEDULED"
                          ? "bg-blue-50 text-blue-700 border-blue-200"
                          : "bg-slate-100 text-slate-600 border-slate-200"
                      }`}
                    >
                      {exam.availability === "COMPLETED" ? "COMPLETED" : exam.canStart ? "AVAILABLE NOW" : exam.availability}
                    </span>
                  </div>

                  <p className="text-xs text-slate-500 line-clamp-2">
                    {exam.description || "No specific instructions specified for this examination."}
                  </p>

                  <div className="flex flex-col gap-1.5 text-xs text-slate-600 pt-3 border-t border-slate-100 bg-slate-50/50 p-3 rounded-xl border border-slate-100">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 text-slate-700 font-semibold">
                        <Clock className="h-4 w-4 text-blue-600" />
                        <span>{exam.duration_minutes} Minutes</span>
                      </div>
                      <div className="flex items-center gap-1 text-slate-500 text-[11px]">
                        <Calendar className="h-3.5 w-3.5 text-slate-400" />
                        <span>Schedule Window</span>
                      </div>
                    </div>
                    <div className="flex flex-col gap-0.5 text-[11px] text-slate-600 pt-1 border-t border-slate-200/60">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Starts:</span>
                        <span className="font-medium text-slate-800">{formatWindowDate(exam.start_window)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Ends:</span>
                        <span className="font-medium text-slate-800">{formatWindowDate(exam.end_window)}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="pt-2">
                  {exam.availability === "COMPLETED" ? (
                    <button
                      onClick={() => router.push(exam.sessionId ? `/candidate/results/${exam.sessionId}` : "/candidate/results")}
                      className="w-full flex items-center justify-center gap-2 rounded-xl bg-purple-600 hover:bg-purple-700 active:bg-purple-800 px-4 py-2.5 text-sm font-bold text-white shadow-md transition"
                    >
                      <CheckCircle2 className="h-4 w-4" /> View Detailed Results & Score
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  ) : (
                    <button
                      onClick={() => router.push(`/exam/readiness?exam_id=${exam.id}`)}
                      disabled={!exam.canStart}
                      className={`w-full flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold shadow-md transition disabled:cursor-not-allowed ${
                        exam.canStart
                          ? "bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white shadow-emerald-200"
                          : "bg-slate-100 text-slate-500 border border-slate-200 disabled:shadow-none"
                      }`}
                    >
                      {exam.canStart ? (
                        <>
                          <PlayCircle className="h-4 w-4" /> Start Exam & Check System
                        </>
                      ) : exam.availability === "SCHEDULED" ? (
                        <>
                          <Clock className="h-4 w-4 text-blue-600 animate-pulse" />
                          <span>{exam.countdownText}</span>
                        </>
                      ) : (
                        "Exam Window Closed"
                      )}
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
