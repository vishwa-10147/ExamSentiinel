"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { BarChart3, Code2, Flame, Search, Target, Trophy, X } from "lucide-react";
import {
  Difficulty,
  LeaderboardEntry,
  PracticeStats,
  ProblemListItem,
  practiceService,
} from "@/services/practiceService";
import { DifficultyBadge, DIFFICULTY_TEXT, StatusIcon, VerdictText } from "@/components/practice/badges";

const DIFFICULTIES: Difficulty[] = ["EASY", "MEDIUM", "HARD"];

function ProgressRing({ solved, total }: { solved: number; total: number }) {
  const pct = total ? solved / total : 0;
  const r = 34;
  const c = 2 * Math.PI * r;
  return (
    <svg viewBox="0 0 80 80" className="h-24 w-24 -rotate-90">
      <circle cx="40" cy="40" r={r} className="fill-none stroke-slate-200 dark:stroke-slate-700" strokeWidth="7" />
      <circle
        cx="40" cy="40" r={r} className="fill-none stroke-emerald-500 transition-all duration-700"
        strokeWidth="7" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - pct)}
      />
    </svg>
  );
}

function ActivityStrip({ activity }: { activity: Record<string, number> }) {
  // Last 26 weeks, one column per week, Sunday-first.
  const weeks = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const start = new Date(today);
    start.setDate(start.getDate() - (25 * 7 + today.getDay()));
    const cols: { date: string; count: number; future: boolean }[][] = [];
    for (let w = 0; w < 26; w++) {
      const col = [];
      for (let d = 0; d < 7; d++) {
        const day = new Date(start);
        day.setDate(start.getDate() + w * 7 + d);
        const key = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(day.getDate()).padStart(2, "0")}`;
        col.push({ date: key, count: activity[key] || 0, future: day > today });
      }
      cols.push(col);
    }
    return cols;
  }, [activity]);

  const shade = (n: number) =>
    n === 0 ? "bg-slate-100 dark:bg-slate-800" : n < 3 ? "bg-emerald-200 dark:bg-emerald-900" : n < 6 ? "bg-emerald-400 dark:bg-emerald-700" : "bg-emerald-600 dark:bg-emerald-500";

  return (
    <div className="flex gap-[3px] overflow-x-auto pb-1" aria-label="Submission activity over the last 26 weeks">
      {weeks.map((col, i) => (
        <div key={i} className="flex flex-col gap-[3px]">
          {col.map((d) => (
            <div
              key={d.date}
              title={d.future ? "" : `${d.count} submission${d.count === 1 ? "" : "s"} on ${d.date}`}
              className={`h-3 w-3 rounded-[3px] ${d.future ? "opacity-0" : shade(d.count)}`}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

export default function ProblemsPage() {
  const [problems, setProblems] = useState<ProblemListItem[]>([]);
  const [stats, setStats] = useState<PracticeStats | null>(null);
  const [leaders, setLeaders] = useState<LeaderboardEntry[]>([]);
  const [tags, setTags] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [difficulty, setDifficulty] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [tag, setTag] = useState<string>("");
  const [topic, setTopic] = useState<string>("");
  const [showAllTags, setShowAllTags] = useState(false);
  const [sort, setSort] = useState<"number" | "difficulty" | "acceptance" | "title">("number");

  const load = useCallback(async () => {
    try {
      const [list, st, lb, tg] = await Promise.all([
        practiceService.listProblems(),
        practiceService.stats(),
        practiceService.leaderboard(5),
        practiceService.listTags(),
      ]);
      setProblems(list.items);
      setStats(st);
      setLeaders(lb);
      setTags(tg);
      setError(null);
    } catch (e: any) {
      setError(e?.message || "Failed to load problems.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Deep links such as /candidate/problems?topic=Graphs pre-select a topic.
  useEffect(() => {
    const t = new URLSearchParams(window.location.search).get("topic");
    if (t) setTopic(t);
  }, []);

  // Problem numbers are stable IDs from the server; unnumbered problems sort last.
  const idOf = (p: ProblemListItem) => p.number ?? Number.MAX_SAFE_INTEGER;

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase().replace(/^#/, "");
    const rows = problems.filter(
      (p) =>
        (!q || p.title.toLowerCase().includes(q) || p.slug.includes(q) || String(p.number ?? "") === q || p.tags.some((t) => t.includes(q))) &&
        (!difficulty || p.difficulty === difficulty) &&
        (!status || p.status === status) &&
        (!topic || p.topic === topic) &&
        (!tag || p.tags.includes(tag))
    );
    const rank: Record<Difficulty, number> = { EASY: 0, MEDIUM: 1, HARD: 2 };
    return [...rows].sort((a, b) => {
      if (sort === "title") return a.title.localeCompare(b.title);
      if (sort === "acceptance") return (b.acceptance_rate ?? -1) - (a.acceptance_rate ?? -1) || idOf(a) - idOf(b);
      if (sort === "difficulty") return rank[a.difficulty] - rank[b.difficulty] || idOf(a) - idOf(b);
      return idOf(a) - idOf(b);
    });
  }, [problems, search, difficulty, status, tag, topic, sort]);

  const counts = useMemo(() => {
    const c: Record<string, { total: number; solved: number }> = { "": { total: 0, solved: 0 } };
    for (const d of DIFFICULTIES) c[d] = { total: 0, solved: 0 };
    for (const p of problems) {
      for (const key of ["", p.difficulty]) {
        c[key].total += 1;
        if (p.status === "solved") c[key].solved += 1;
      }
    }
    return c;
  }, [problems]);

  const clearFilters = () => {
    setSearch("");
    setDifficulty("");
    setStatus("");
    setTag("");
    setTopic("");
  };
  const hasFilters = search || difficulty || status || tag || topic;

  return (
    <div className="flex-1 overflow-auto p-6 pb-12 sm:p-8">
      <div className="mx-auto w-full max-w-7xl space-y-6">
        <div className="flex flex-col justify-between gap-3 border-b border-slate-200 pb-5 dark:border-slate-700 sm:flex-row sm:items-end">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-900 dark:text-white">
              <Code2 className="h-7 w-7 text-blue-600 dark:text-blue-400" />
              Problem Set
            </h1>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Practice coding problems with instant feedback. Practice never affects your exam results.
            </p>
          </div>
          <div className="flex gap-2">
            <Link
              href="/candidate/progress"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              <BarChart3 className="h-4 w-4" /> Progress &amp; history
            </Link>
            <Link
              href="/candidate/practice"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              Open Playground
            </Link>
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300">
            {error}
          </div>
        )}

        {/* Progress */}
        {stats && (
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="flex items-center gap-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800">
              <div className="relative">
                <ProgressRing solved={stats.solved_total} total={stats.problems_total} />
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-xl font-bold text-slate-900 dark:text-white">{stats.solved_total}</span>
                  <span className="text-[10px] uppercase tracking-wide text-slate-500 dark:text-slate-400">of {stats.problems_total}</span>
                </div>
              </div>
              <div className="flex-1 space-y-2">
                {DIFFICULTIES.map((d) => {
                  const p = stats.by_difficulty[d];
                  return (
                    <div key={d}>
                      <div className="flex justify-between gap-2 text-xs">
                        <span className={`font-semibold ${DIFFICULTY_TEXT[d]}`}>{d.charAt(0) + d.slice(1).toLowerCase()}</span>
                        <span className="text-slate-500 dark:text-slate-400">{p.solved}/{p.total}</span>
                      </div>
                      <div className="mt-1 h-1.5 rounded-full bg-slate-100 dark:bg-slate-700">
                        <div
                          className={`h-1.5 rounded-full ${d === "EASY" ? "bg-emerald-500" : d === "MEDIUM" ? "bg-amber-500" : "bg-rose-500"}`}
                          style={{ width: `${p.total ? (100 * p.solved) / p.total : 0}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800 lg:col-span-2">
              <div className="mb-3 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
                <span className="flex items-center gap-1.5 text-slate-700 dark:text-slate-200">
                  <Flame className="h-4 w-4 text-orange-500" />
                  <strong>{stats.current_streak_days}</strong> day streak
                </span>
                <span className="flex items-center gap-1.5 text-slate-700 dark:text-slate-200">
                  <Target className="h-4 w-4 text-blue-500" />
                  <strong>{stats.acceptance_rate ?? "—"}{stats.acceptance_rate != null && "%"}</strong> acceptance
                </span>
                <span className="text-slate-500 dark:text-slate-400">{stats.submissions_total} submissions</span>
              </div>
              <ActivityStrip activity={stats.activity} />
            </div>
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
          {/* Problem table */}
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative min-w-[200px] flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search by title, #ID or tag"
                  aria-label="Search problems"
                  className="w-full rounded-xl border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                />
              </div>
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as typeof sort)}
                aria-label="Sort problems"
                className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
              >
                <option value="number">Sort: ID</option>
                <option value="difficulty">Sort: Easy → Hard</option>
                <option value="acceptance">Sort: Acceptance (high → low)</option>
                <option value="title">Sort: Title</option>
              </select>
              <select
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                aria-label="Filter by topic"
                className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
              >
                <option value="">All topics</option>
                {(stats?.by_topic ?? []).map((t) => (
                  <option key={t.topic} value={t.topic}>
                    {t.topic} ({t.solved}/{t.total})
                  </option>
                ))}
              </select>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                aria-label="Filter by status"
                className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
              >
                <option value="">Any status</option>
                <option value="todo">Not started</option>
                <option value="attempted">Attempted</option>
                <option value="solved">Solved</option>
              </select>
              {hasFilters && (
                <button onClick={clearFilters} className="inline-flex items-center gap-1 rounded-lg px-2 py-2 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-white">
                  <X className="h-4 w-4" /> Clear
                </button>
              )}
            </div>

            <div className="flex flex-wrap gap-1 rounded-xl bg-slate-100 p-1 dark:bg-slate-800" role="tablist" aria-label="Difficulty">
              {(["", ...DIFFICULTIES] as const).map((d) => (
                <button
                  key={d || "all"}
                  role="tab"
                  aria-selected={difficulty === d}
                  onClick={() => setDifficulty(d)}
                  className={`flex-1 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                    difficulty === d
                      ? "bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-white"
                      : "text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200"
                  }`}
                >
                  <span className={d ? DIFFICULTY_TEXT[d] : ""}>{d ? d.charAt(0) + d.slice(1).toLowerCase() : "All"}</span>
                  <span className="ml-1.5 text-xs tabular-nums text-slate-400">
                    {counts[d]?.solved ?? 0}/{counts[d]?.total ?? 0}
                  </span>
                </button>
              ))}
            </div>

            {tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {(showAllTags ? tags : tags.slice(0, 16)).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTag(tag === t ? "" : t)}
                    className={`rounded-full border px-2.5 py-1 text-xs font-medium transition ${
                      tag === t
                        ? "border-blue-600 bg-blue-600 text-white"
                        : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                    }`}
                  >
                    {t}
                  </button>
                ))}
                {tags.length > 16 && (
                  <button onClick={() => setShowAllTags((v) => !v)} className="px-2 py-1 text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline">
                    {showAllTags ? "Fewer tags" : `All ${tags.length} tags`}
                  </button>
                )}
              </div>
            )}

            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-800">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400 dark:bg-slate-900/50">
                  <tr>
                    <th className="w-12 px-4 py-3">Status</th>
                    <th className="w-14 px-2 py-3 text-right">#</th>
                    <th className="px-4 py-3">Title</th>
                    <th className="hidden px-4 py-3 md:table-cell">Topic</th>
                    <th className="w-28 px-4 py-3 text-right">Acceptance</th>
                    <th className="w-28 px-4 py-3">Difficulty</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                  {loading &&
                    Array.from({ length: 6 }).map((_, i) => (
                      <tr key={i}>
                        <td colSpan={6} className="px-4 py-3">
                          <div className="h-4 animate-pulse rounded bg-slate-100 dark:bg-slate-700" />
                        </td>
                      </tr>
                    ))}
                  {!loading && filtered.length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-4 py-10 text-center text-slate-500 dark:text-slate-400">
                        No problems match these filters.
                      </td>
                    </tr>
                  )}
                  {filtered.map((p) => (
                    <tr key={p.id} className="transition hover:bg-slate-50 dark:hover:bg-slate-700/40">
                      <td className="px-4 py-3"><StatusIcon status={p.status} /></td>
                      <td className="px-2 py-3 text-right tabular-nums text-slate-400">{p.number ?? "—"}</td>
                      <td className="px-4 py-3">
                        <Link href={`/candidate/problems/${p.slug}`} className="font-medium text-slate-900 hover:text-blue-600 dark:text-white dark:hover:text-blue-400">
                          {p.title}
                        </Link>
                        <div className="mt-0.5 flex flex-wrap gap-1 md:hidden">
                          {p.topic && <span className="text-[11px] text-slate-500 dark:text-slate-400">{p.topic}</span>}
                        </div>
                      </td>
                      <td className="hidden px-4 py-3 md:table-cell">
                        {p.topic && (
                          <button
                            onClick={() => setTopic(topic === p.topic ? "" : p.topic!)}
                            className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600 hover:bg-blue-50 dark:hover:bg-blue-500/10 hover:text-blue-700 dark:bg-slate-700 dark:text-slate-300"
                          >
                            {p.topic}
                          </button>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-slate-600 dark:text-slate-300">
                        {p.acceptance_rate != null ? `${p.acceptance_rate}%` : "—"}
                      </td>
                      <td className="px-4 py-3"><DifficultyBadge difficulty={p.difficulty} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Sidebar */}
          <aside className="space-y-6">
            {stats && (stats.by_topic?.length ?? 0) > 0 && (
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800">
                <h2 className="mb-3 text-sm font-bold text-slate-900 dark:text-white">Topics</h2>
                <ul className="space-y-2">
                  {stats.by_topic.map((t) => (
                    <li key={t.topic}>
                      <button
                        onClick={() => setTopic(topic === t.topic ? "" : t.topic)}
                        aria-pressed={topic === t.topic}
                        className={`w-full rounded-lg px-2 py-1 text-left text-xs transition ${
                          topic === t.topic ? "bg-blue-50 dark:bg-blue-500/10" : "hover:bg-slate-50 dark:hover:bg-slate-700/40"
                        }`}
                      >
                        <div className="flex justify-between gap-2">
                          <span className="font-medium text-slate-700 dark:text-slate-200">{t.topic}</span>
                          <span className="tabular-nums text-slate-500 dark:text-slate-400">{t.solved}/{t.total}</span>
                        </div>
                        <div className="mt-1 h-1 rounded-full bg-slate-100 dark:bg-slate-700">
                          <div className="h-1 rounded-full bg-emerald-500" style={{ width: `${t.total ? (100 * t.solved) / t.total : 0}%` }} />
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800">
              <h2 className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-white">
                <Trophy className="h-4 w-4 text-amber-500" /> Top Solvers
              </h2>
              {leaders.length === 0 ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">Be the first to solve a problem!</p>
              ) : (
                <ol className="space-y-2">
                  {leaders.map((l) => (
                    <li key={l.user_id} className="flex items-center gap-3 text-sm">
                      <span className="w-5 text-center font-bold text-slate-400">{l.rank}</span>
                      <span className="flex-1 truncate text-slate-800 dark:text-slate-200">{l.name}</span>
                      <span className="tabular-nums font-semibold text-slate-900 dark:text-white">{l.solved}</span>
                    </li>
                  ))}
                </ol>
              )}
            </div>

            {stats && stats.recent.length > 0 && (
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800">
                <h2 className="mb-3 text-sm font-bold text-slate-900 dark:text-white">Recent Submissions</h2>
                <ul className="space-y-2.5">
                  {stats.recent.slice(0, 6).map((r, i) => (
                    <li key={i} className="text-sm">
                      <Link href={`/candidate/problems/${r.slug}`} className="block truncate text-slate-800 hover:text-blue-600 dark:text-slate-200">
                        {r.title}
                      </Link>
                      <div className="flex justify-between gap-2 text-xs">
                        <VerdictText verdict={r.verdict} />
                        <span className="text-slate-400">{new Date(r.created_at).toLocaleDateString()}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </aside>
        </div>
      </div>
    </div>
  );
}
