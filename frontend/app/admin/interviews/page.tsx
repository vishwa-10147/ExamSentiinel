"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Loader2, MessagesSquare, RefreshCw } from "lucide-react";
import { InterviewListItem, interviewService } from "@/services/interviewService";

const STATUS_STYLE: Record<string, string> = {
  SCHEDULED: "bg-slate-100 text-slate-600",
  READY: "bg-amber-50 text-amber-700",
  LIVE: "bg-emerald-50 text-emerald-700",
  COMPLETED: "bg-blue-50 text-blue-700",
};

export default function InterviewsPage() {
  const [items, setItems] = useState<InterviewListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      setItems(await interviewService.list());
      setError(null);
    } catch (e: any) {
      setError(e?.message || "Failed to load interviews.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="flex-1 overflow-auto p-6 pb-12 sm:p-8">
      <div className="mx-auto w-full max-w-6xl space-y-6">
        <div className="flex items-end justify-between border-b border-slate-200 pb-5 dark:border-slate-700">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-900 dark:text-white">
              <MessagesSquare className="h-7 w-7 text-indigo-600" /> Live Interviews
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              Candidates open their interview from the exam; join here to connect by video, follow the live transcript and score.
            </p>
          </div>
          <button onClick={() => void load()} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50">
            <RefreshCw className="h-4 w-4" /> Refresh
          </button>
        </div>

        {error && <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div>}

        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-800">
          <table className="w-full min-w-[700px] text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900/50">
              <tr>
                <th className="px-4 py-3">Candidate</th>
                <th className="px-4 py-3">Exam</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Consent</th>
                <th className="px-4 py-3 text-right">Transcript</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
              {loading && items.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-10 text-center text-slate-500"><Loader2 className="mx-auto h-5 w-5 animate-spin" /></td></tr>
              )}
              {!loading && items.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-10 text-center text-slate-500">No interviews yet.</td></tr>
              )}
              {items.map((i) => (
                <tr key={i.id}>
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900 dark:text-white">{i.candidate_name}</div>
                    <div className="text-xs text-slate-400">{i.candidate_email}</div>
                  </td>
                  <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{i.exam_title}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_STYLE[i.status] ?? STATUS_STYLE.SCHEDULED}`}>{i.status}</span>
                  </td>
                  <td className="px-4 py-3 text-xs">{i.recording_consent ? "Given" : "Pending"}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{i.segments} segments</td>
                  <td className="px-4 py-3 text-right">
                    <Link href={`/interview/${i.id}`} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700">
                      {i.status === "COMPLETED" ? "Review" : "Join"}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
