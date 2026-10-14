"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { BarChart3, ChevronLeft, ChevronRight } from "lucide-react";
import {
  LANGUAGE_LABELS,
  PracticeLanguage,
  PracticeStats,
  SubmissionHistoryItem,
  VERDICT_LABELS,
  Verdict,
  practiceService,
} from "@/services/practiceService";
import { DIFFICULTY_TEXT, VerdictText } from "@/components/practice/badges";

const PAGE_SIZE = 25;
const VERDICTS = Object.keys(VERDICT_LABELS) as Verdict[];

export default function PracticeProgressPage() {
  const [stats, setStats] = useState<PracticeStats | null>(null);
  const [history, setHistory] = useState<SubmissionHistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [verdict, setVerdict] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    practiceService.stats().then(setStats).catch((e) => setError(e?.message || "Failed to load progress."));
  }, []);

  const loadHistory = useCallback(async () => {
    setLoading(true);
    try {
      const r = await practiceService.history({ verdict: verdict || undefined, limit: PAGE_SIZE, offset: page * PAGE_SIZE });
      setHistory(r.items);
      setTotal(r.total);
    } catch (e: any) {
      setError(e?.message || "Failed to load submissions.");
    } finally {
      setLoading(false);
    }
  }, [verdict, page]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="flex-1 overflow-auto p-6 pb-12 sm:p-8">
      <div className="mx-auto w-full max-w-6xl space-y-6">
        <div className="border-b border-slate-200 pb-5 dark:border-slate-700">
          <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-900 dark:text-white">
            <BarChart3 className="h-7 w-7 text-blue-600 dark:text-blue-400" /> Practice Progress
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Solved problems by topic and difficulty, and every submission you have made.{" "}
            <Link href="/candidate/problems" className="font-medium text-blue-600 dark:text-blue-400 hover:underline">Back to the problem set</Link>
          </p>
        </div>

        {error && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300">
            {error}
          </div>
        )}

        {stats && (
          <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
            <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800">
              <div>
                <div className="text-3xl font-bold text-slate-900 dark:text-white">
                  {stats.solved_total}
                  <span className="text-base font-medium text-slate-400"> / {stats.problems_total}</span>
                </div>
                <div className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">problems solved</div>
              </div>
              {(["EASY", "MEDIUM", "HARD"] as const).map((d) => (
                <div key={d} className="flex justify-between text-sm">
                  <span className={`font-semibold ${DIFFICULTY_TEXT[d]}`}>{d.charAt(0) + d.slice(1).toLowerCase()}</span>
                  <span className="tabular-nums text-slate-600 dark:text-slate-300">
                    {stats.by_difficulty[d].solved}/{stats.by_difficulty[d].total}
                  </span>
                </div>
              ))}
              <div className="border-t border-slate-100 pt-3 text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">
                {stats.submissions_total} submissions · {stats.acceptance_rate ?? "—"}
                {stats.acceptance_rate != null && "%"} accepted · {stats.current_streak_days}-day streak
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800">
              <h2 className="mb-4 text-sm font-bold text-slate-900 dark:text-white">By topic</h2>
              <div className="grid gap-x-8 gap-y-3 sm:grid-cols-2">
                {(stats.by_topic ?? []).map((t) => (
                  <Link key={t.topic} href={`/candidate/problems?topic=${encodeURIComponent(t.topic)}`} className="group block">
                    <div className="flex justify-between gap-2 text-sm">
                      <span className="font-medium text-slate-700 group-hover:text-blue-600 dark:text-slate-200">{t.topic}</span>
                      <span className="tabular-nums text-slate-500 dark:text-slate-400">
                        {t.solved}/{t.total}
                        {t.attempted > 0 && <span className="text-amber-500"> · {t.attempted} tried</span>}
                      </span>
                    </div>
                    <div className="mt-1 flex h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700">
                      <div className="bg-emerald-500" style={{ width: `${t.total ? (100 * t.solved) / t.total : 0}%` }} />
                      <div className="bg-amber-300" style={{ width: `${t.total ? (100 * t.attempted) / t.total : 0}%` }} />
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-800">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-3 dark:border-slate-700">
            <h2 className="text-sm font-bold text-slate-900 dark:text-white">Submission history ({total})</h2>
            <select
              value={verdict}
              onChange={(e) => {
                setVerdict(e.target.value);
                setPage(0);
              }}
              aria-label="Filter by verdict"
              className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm text-slate-700 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
            >
              <option value="">All verdicts</option>
              {VERDICTS.map((v) => (
                <option key={v} value={v}>{VERDICT_LABELS[v]}</option>
              ))}
            </select>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                <tr>
                  <th className="px-5 py-2">When</th>
                  <th className="px-3 py-2">Problem</th>
                  <th className="px-3 py-2">Verdict</th>
                  <th className="px-3 py-2">Language</th>
                  <th className="px-3 py-2 text-right">Tests</th>
                  <th className="px-5 py-2 text-right">Runtime</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                {!loading && history.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-5 py-10 text-center text-slate-500 dark:text-slate-400">No submissions yet.</td>
                  </tr>
                )}
                {history.map((s) => (
                  <tr key={s.id}>
                    <td className="whitespace-nowrap px-5 py-2 text-slate-500 dark:text-slate-400">{new Date(s.created_at).toLocaleString()}</td>
                    <td className="px-3 py-2">
                      <Link href={`/candidate/problems/${s.problem_slug}`} className="font-medium text-slate-800 hover:text-blue-600 dark:text-slate-100">
                        {s.problem_number != null ? `${s.problem_number}. ` : ""}{s.problem_title}
                      </Link>
                    </td>
                    <td className="px-3 py-2"><VerdictText verdict={s.verdict} /></td>
                    <td className="px-3 py-2">{LANGUAGE_LABELS[s.language as PracticeLanguage] ?? s.language}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{s.passed_count}/{s.total_count}</td>
                    <td className="px-5 py-2 text-right tabular-nums">{s.runtime_ms != null ? `${s.runtime_ms} ms` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {pages > 1 && (
            <div className="flex items-center justify-end gap-2 border-t border-slate-100 px-5 py-2 text-sm dark:border-slate-700">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                aria-label="Previous page"
                className="rounded p-1 text-slate-500 dark:text-slate-400 hover:bg-slate-100 disabled:opacity-40 dark:hover:bg-slate-700"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="tabular-nums text-slate-500 dark:text-slate-400">Page {page + 1} of {pages}</span>
              <button
                onClick={() => setPage((p) => Math.min(pages - 1, p + 1))}
                disabled={page >= pages - 1}
                aria-label="Next page"
                className="rounded p-1 text-slate-500 dark:text-slate-400 hover:bg-slate-100 disabled:opacity-40 dark:hover:bg-slate-700"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
