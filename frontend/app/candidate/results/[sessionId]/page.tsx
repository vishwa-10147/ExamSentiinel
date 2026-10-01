"use client";
export const dynamic = "force-dynamic";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/services/apiClient";
import { ArrowLeft, Award, CheckCircle2, XCircle, Clock, AlertCircle, Loader2, FileText } from "lucide-react";

export default function CandidateResultDetailPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const router = useRouter();
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    apiClient.get(`/api/reports/my-results/detailed/${sessionId}`)
      .then((res: any) => {
        setResult(res?.data || res);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load result."))
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) {
    return (
      <main className="w-full max-w-5xl mx-auto p-8 flex flex-col items-center justify-center min-h-[60vh] text-slate-500">
        <Loader2 className="w-8 h-8 animate-spin mb-3 text-blue-600" />
        <p className="text-sm font-medium">Fetching detailed examination breakdown...</p>
      </main>
    );
  }

  if (error || !result) {
    return (
      <main className="w-full max-w-5xl mx-auto p-6 sm:p-8">
        <button 
          onClick={() => router.push("/candidate/results")} 
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-blue-600 hover:text-blue-700 mb-6"
        >
          <ArrowLeft className="w-4 h-4" /> Back to My Results
        </button>
        <div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-center text-red-700 flex flex-col items-center">
          <AlertCircle className="w-10 h-10 mb-2 text-red-500" />
          <h2 className="text-lg font-bold mb-1">Result Unavailable</h2>
          <p className="text-sm">{error || "Could not retrieve session details."}</p>
        </div>
      </main>
    );
  }

  const responses = Array.isArray(result?.responses) ? result.responses : [];
  const totalAwarded = result?.total_awarded ?? result?.total_score ?? 0;
  const totalPossible = result?.total_possible ?? result?.max_score ?? 0;
  const percentage = totalPossible > 0 ? ((totalAwarded / totalPossible) * 100).toFixed(1) : "0.0";

  return (
    <main className="w-full max-w-6xl mx-auto space-y-6 p-4 sm:p-6 lg:p-8">
      {/* Navigation */}
      <button 
        onClick={() => router.push("/candidate/results")} 
        className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-600 hover:text-blue-600 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Back to My Results
      </button>

      {/* Summary Card */}
      <div className="bg-gradient-to-r from-slate-900 to-blue-950 text-white rounded-2xl p-6 sm:p-8 shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-500/20 text-blue-300 border border-blue-400/20">
            <Award className="w-3.5 h-3.5" /> Examination Report
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold">{result.exam_name || result.exam_title || "Exam Result Summary"}</h1>
          <p className="text-slate-400 text-sm">Session ID: <span className="font-mono text-slate-300">{sessionId}</span></p>
        </div>

        <div className="bg-white/10 backdrop-blur-md rounded-xl p-4 sm:p-5 border border-white/10 text-center min-w-[200px] w-full md:w-auto space-y-3">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1">Final Grade</div>
            <div className="text-3xl font-extrabold text-white">
              {totalAwarded} <span className="text-lg font-normal text-slate-400">/ {totalPossible}</span>
            </div>
            <div className="text-xs font-medium text-emerald-400 mt-1">{percentage}% Aggregate Score</div>
          </div>

          <div className="flex flex-col gap-2 pt-2 border-t border-white/10">
            <a
              href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/results/session/${sessionId}/certificate`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-bold transition-all shadow-sm"
            >
              <Award className="w-3.5 h-3.5" /> Download Certificate
            </a>
            <a
              href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/reports/session/${sessionId}/pdf`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold transition-all border border-slate-700"
            >
              <FileText className="w-3.5 h-3.5" /> PDF Audit Report
            </a>
          </div>
        </div>
      </div>

      {/* Questions Breakdown Table */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
          <h2 className="font-bold text-slate-900 flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-600" /> Question Breakdown
          </h2>
          <span className="text-xs text-slate-500 font-medium">{responses.length} Total Questions</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left text-slate-600">
            <thead className="text-xs text-slate-500 uppercase bg-slate-50 border-b border-slate-200 font-semibold">
              <tr>
                <th className="px-6 py-4">Question</th>
                <th className="px-6 py-4">Marks Awarded</th>
                <th className="px-6 py-4 text-right">Evaluation Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {responses.length === 0 ? (
                <tr>
                  <td colSpan={3} className="px-6 py-12 text-center text-slate-400 text-sm">
                    No detailed question breakdown recorded for this session.
                  </td>
                </tr>
              ) : (
                responses.map((resp: any, idx: number) => {
                  const isCorrect = resp.is_correct === true;
                  const isIncorrect = resp.is_correct === false;

                  return (
                    <tr key={resp.question_id || idx} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-6 py-4 font-semibold text-slate-900">
                        {resp.question_title || `Question ${idx + 1}`}
                      </td>
                      <td className="px-6 py-4 font-mono font-medium text-slate-800">
                        {resp.marks_awarded ?? 0} pts
                      </td>
                      <td className="px-6 py-4 text-right">
                        {isCorrect ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Correct
                          </span>
                        ) : isIncorrect ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-red-50 text-red-700 border border-red-200">
                            <XCircle className="w-3.5 h-3.5" /> Incorrect
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">
                            <Clock className="w-3.5 h-3.5" /> Pending Review
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
