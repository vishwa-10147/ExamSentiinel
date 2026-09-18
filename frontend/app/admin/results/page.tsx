"use client";

import React, { useState, useEffect } from "react";
import { apiClient } from "@/services/apiClient";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { FileCheck2, Loader2, Send } from "lucide-react";
import toast from "react-hot-toast";

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
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
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
      // Fallback for mock if necessary
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
    try {
      // Trying to fetch sessions for this exam
      const data = await apiClient.get<any>(`/api/results/admin/exam/${examId}/sessions`);
      setSessions(Array.isArray(data) ? data : data?.data || []);
    } catch (error) {
      setSessions([]);
      toast.error("Failed to fetch sessions");
    }
  };

  const handlePublish = async () => {
    if (!selectedExam) return;
    setPublishing(true);
    try {
      await apiClient.post(`/api/results/publish/${selectedExam}`, {});
      toast.success("Results published successfully");
    } catch (error) {
      toast.error("Failed to publish results. Please try again.");
      console.error(error);
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <FileCheck2 className="h-6 w-6 text-blue-600" />
            Results & Grading
          </h1>
          <p className="text-slate-500 text-sm mt-1">Review and publish exam results.</p>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
        {loading ? (
          <div className="flex justify-center items-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          </div>
        ) : (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row gap-4 items-end">
              <div className="flex-1 w-full">
                <label className="block text-sm font-medium text-slate-700 mb-1">Select Exam</label>
                <select
                  className="w-full border-slate-300 rounded-lg shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  value={selectedExam}
                  onChange={(e) => setSelectedExam(e.target.value)}
                >
                  <option value="">-- Select an Exam --</option>
                  {exams.map((exam) => (
                    <option key={exam.id} value={exam.id}>{exam.title}</option>
                  ))}
                </select>
              </div>
              <button
                onClick={handlePublish}
                disabled={publishing || !selectedExam}
                className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                {publishing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                Publish Results
              </button>
            </div>

            {selectedExam && (
              <div className="mt-8">
                <h3 className="text-lg font-semibold text-slate-800 mb-4">Exam Sessions</h3>
                <div className="overflow-x-auto rounded-lg border border-slate-200">
                  <table className="min-w-full divide-y divide-slate-200">
                    <thead className="bg-slate-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Session ID</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Candidate ID</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Score</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Integrity</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-slate-200">
                      {sessions.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="px-6 py-4 text-center text-sm text-slate-500">
                            No sessions found for this exam.
                          </td>
                        </tr>
                      ) : (
                        sessions.map((session) => (
                          <tr key={session.id}>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">{session.id}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{session.candidate_id}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                              <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                session.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                              }`}>
                                {session.status}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{session.score ?? 'N/A'}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                              <span className={`font-medium ${
                                session.integrity_score >= 80 ? 'text-green-600' : session.integrity_score >= 50 ? 'text-yellow-600' : 'text-red-600'
                              }`}>
                                {session.integrity_score}%
                              </span>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
