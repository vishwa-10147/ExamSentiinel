"use client";
export const dynamic = "force-dynamic";

import React, { useState, useEffect } from "react";
import { apiClient } from "@/services/apiClient";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { FileCheck2, Loader2, Send, CheckCircle2, ShieldAlert, Award } from "lucide-react";
import toast from "react-hot-toast";

interface SessionResult {
  id: string;
  candidate_id: string;
  candidate_name?: string;
  status: string;
  score: number | null;
  integrity_score: number;
  submitted_at: string | null;
  results_published: boolean;
}

export default function ResultsPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!authLoading && (!user || user.role !== "admin")) {
      router.push("/dashboard");
    }
  }, [user, authLoading, router]);

  const [exams, setExams] = useState<any[]>([]);
  const [selectedExam, setSelectedExam] = useState<string>("");
  const [sessions, setSessions] = useState<SessionResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [publishing, setPublishing] = useState(false);

  useEffect(() => {
    fetchExams();
  }, []);

  useEffect(() => {
    if (selectedExam) {
      fetchSessions(selectedExam);
    } else {
      setSessions([]);
    }
  }, [selectedExam]);

  const fetchExams = async () => {
    setLoading(true);
    try {
      const data = await apiClient.get<any>("/api/exams?limit=50&offset=0");
      const examList = Array.isArray(data) ? data : data?.exams || data?.data || [];
      setExams(examList);
      if (examList.length > 0) {
        setSelectedExam(examList[0].id);
      }
    } catch (error) {
      toast.error("Failed to fetch exams");
      console.error(error);
      setExams([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchSessions = async (examId: string) => {
    setSessionsLoading(true);
    try {
      const data = await apiClient.get<SessionResult[]>(`/api/results/admin/exam/${examId}/sessions`);
      setSessions(Array.isArray(data) ? data : []);
    } catch (error) {
      setSessions([]);
      toast.error("Failed to fetch exam results");
    } finally {
      setSessionsLoading(false);
    }
  };

  const handlePublish = async () => {
    if (!selectedExam) return;
    setPublishing(true);
    try {
      await apiClient.post(`/api/results/publish/${selectedExam}`, {});
      toast.success("Results published successfully!");
      fetchSessions(selectedExam);
    } catch (error) {
      toast.error("Failed to publish results. Please try again.");
      console.error(error);
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="space-y-6 p-6 sm:p-8 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <FileCheck2 className="h-6 w-6 text-blue-600" />
            Results & Score Publication
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Review candidate scores, integrity risk scores, and publish final examination grades.
          </p>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-6">
        {loading ? (
          <div className="flex justify-center items-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          </div>
        ) : (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row gap-4 items-end justify-between bg-slate-50 p-4 rounded-xl border border-slate-200">
              <div className="flex-1 w-full sm:max-w-md">
                <label className="block text-sm font-semibold text-slate-900 mb-1">
                  Select Target Exam
                </label>
                <select
                  className="w-full border-slate-300 rounded-lg shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
                  value={selectedExam}
                  onChange={(e) => setSelectedExam(e.target.value)}
                >
                  <option value="">-- Select an Exam --</option>
                  {exams.map((exam) => (
                    <option key={exam.id} value={exam.id}>
                      {exam.title} ({exam.status})
                    </option>
                  ))}
                </select>
              </div>

              <button
                onClick={handlePublish}
                disabled={publishing || !selectedExam || sessions.length === 0}
                className="flex items-center gap-2 bg-blue-600 text-white px-5 py-2.5 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-sm font-semibold text-sm"
              >
                {publishing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                Publish Results to Candidates
              </button>
            </div>

            {selectedExam && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                    <Award className="h-5 w-5 text-blue-600" />
                    Candidate Submissions & Integrity Summary
                  </h3>
                  <span className="text-xs text-slate-500">{sessions.length} Session(s) Recorded</span>
                </div>

                {sessionsLoading ? (
                  <div className="py-12 flex justify-center">
                    <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                  </div>
                ) : (
                  <div className="overflow-x-auto rounded-xl border border-slate-200">
                    <table className="min-w-full divide-y divide-slate-200 text-sm">
                      <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-500">
                        <tr>
                          <th className="px-6 py-3.5 text-left">Candidate Name</th>
                          <th className="px-6 py-3.5 text-left">Session Status</th>
                          <th className="px-6 py-3.5 text-left">Awarded Score</th>
                          <th className="px-6 py-3.5 text-left">Proctor Risk Index</th>
                          <th className="px-6 py-3.5 text-left">Publication Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 bg-white">
                        {sessions.length === 0 ? (
                          <tr>
                            <td colSpan={5} className="px-6 py-8 text-center text-slate-400">
                              No submissions found for this exam.
                            </td>
                          </tr>
                        ) : (
                          sessions.map((session) => (
                            <tr key={session.id} className="hover:bg-slate-50 transition-colors">
                              <td className="px-6 py-4 whitespace-nowrap">
                                <div>
                                  <p className="font-semibold text-slate-900">{session.candidate_name || "Candidate"}</p>
                                  <p className="text-xs text-slate-400 font-mono">{session.candidate_id}</p>
                                </div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                                  session.status === "SUBMITTED" || session.status === "completed"
                                    ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                    : "bg-amber-50 text-amber-700 border border-amber-200"
                                }`}>
                                  {session.status}
                                </span>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap font-semibold text-slate-800">
                                {session.score !== null ? `${session.score} pts` : "Pending Grading"}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <div className="flex items-center gap-2">
                                  <div className="h-1.5 w-16 bg-slate-100 rounded-full overflow-hidden">
                                    <div
                                      className={`h-full ${
                                        session.integrity_score >= 60 ? "bg-red-500" : session.integrity_score >= 30 ? "bg-amber-400" : "bg-emerald-400"
                                      }`}
                                      style={{ width: `${Math.min(session.integrity_score, 100)}%` }}
                                    />
                                  </div>
                                  <span className={`text-xs font-mono font-semibold ${
                                    session.integrity_score >= 60 ? "text-red-600" : session.integrity_score >= 30 ? "text-amber-600" : "text-emerald-600"
                                  }`}>
                                    {session.integrity_score.toFixed(1)}%
                                  </span>
                                </div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                {session.results_published ? (
                                  <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-full">
                                    <CheckCircle2 className="h-3.5 w-3.5" /> Published
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1 text-xs font-semibold text-slate-600 bg-slate-100 border border-slate-200 px-2.5 py-0.5 rounded-full">
                                    Draft (Unpublished)
                                  </span>
                                )}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
