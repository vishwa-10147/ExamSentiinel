"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import toast from "react-hot-toast";
import { CalendarClock, ChevronLeft, ListChecks, Loader2, Trophy, Users } from "lucide-react";
import Markdown from "@/components/practice/Markdown";
import { DifficultyBadge, StatusIcon, VerdictText } from "@/components/practice/badges";
import { PhaseBadge, formatWhen } from "@/components/contests/PhaseBadge";
import { LANGUAGE_LABELS, PracticeLanguage } from "@/services/practiceService";
import {
  ContestDetail,
  ContestLeaderboard,
  ContestSubmission,
  clockSkew,
  contestService,
  formatCountdown,
  formatDuration,
} from "@/services/contestService";

type Tab = "problems" | "leaderboard" | "submissions";
const LEADERBOARD_REFRESH_MS = 15_000;

export default function ContestPage() {
  const params = useParams();
  const slug = String(params?.slug || "");
  const [contest, setContest] = useState<ContestDetail | null>(null);
  const [board, setBoard] = useState<ContestLeaderboard | null>(null);
  const [mine, setMine] = useState<ContestSubmission[]>([]);
  const [tab, setTab] = useState<Tab>("problems");
  const [skew, setSkew] = useState(0);
  const [now, setNow] = useState(Date.now());
  const [error, setError] = useState<string | null>(null);
  const [registering, setRegistering] = useState(false);

  const load = useCallback(async () => {
    try {
      const c = await contestService.get(slug);
      setContest(c);
      setSkew(clockSkew(c.server_time));
      setError(null);
    } catch (e: any) {
      setError(e?.message || "Contest not found.");
    }
  }, [slug]);

  const loadBoard = useCallback(() => {
    contestService.leaderboard(slug).then(setBoard).catch(() => undefined);
    contestService.submissions(slug).then(setMine).catch(() => undefined);
  }, [slug]);

  useEffect(() => {
    if (!slug) return;
    void load();
    loadBoard();
  }, [slug, load, loadBoard]);

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  // The leaderboard is live while the contest runs.
  useEffect(() => {
    if (contest?.phase !== "running") return;
    const t = setInterval(loadBoard, LEADERBOARD_REFRESH_MS);
    return () => clearInterval(t);
  }, [contest?.phase, loadBoard]);

  const serverNow = now + skew;
  // Reload when the countdown reaches the start or the end, so problems appear / submissions close.
  useEffect(() => {
    if (!contest) return;
    const boundary = contest.phase === "upcoming" ? contest.starts_at : contest.phase === "running" ? contest.ends_at : null;
    if (boundary && new Date(boundary).getTime() <= serverNow) {
      void load();
      loadBoard();
    }
  }, [serverNow, contest, load, loadBoard]);

  const register = async () => {
    setRegistering(true);
    try {
      await contestService.register(slug);
      toast.success("You are registered.");
      await load();
    } catch (e: any) {
      toast.error(e?.message || "Registration failed.");
    } finally {
      setRegistering(false);
    }
  };

  if (error) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
        <p className="text-slate-600 dark:text-slate-300">{error}</p>
        <Link href="/candidate/contests" className="text-sm font-semibold text-blue-600 hover:underline dark:text-blue-400">
          Back to contests
        </Link>
      </div>
    );
  }
  if (!contest) {
    return (
      <div className="flex h-full items-center justify-center text-slate-500 dark:text-slate-400">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading contest…
      </div>
    );
  }

  const countdownTarget = contest.phase === "upcoming" ? contest.starts_at : contest.ends_at;
  const remaining = new Date(countdownTarget).getTime() - serverNow;
  const totalPoints = contest.problems.reduce((sum, p) => sum + p.points, 0);
  const myScore = contest.problems.filter((p) => p.status === "solved").reduce((sum, p) => sum + p.points, 0);

  return (
    <div className="flex-1 overflow-auto p-6 pb-12 sm:p-8">
      <div className="mx-auto w-full max-w-6xl space-y-6">
        <Link href="/candidate/contests" className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-blue-600 dark:text-slate-300 dark:hover:text-blue-400">
          <ChevronLeft className="h-4 w-4" /> All contests
        </Link>

        <div className="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm lg:flex-row lg:items-center dark:border-slate-700 dark:bg-slate-800">
          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{contest.title}</h1>
              <PhaseBadge phase={contest.phase} />
            </div>
            <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-slate-500 dark:text-slate-400">
              <span className="inline-flex items-center gap-1"><CalendarClock className="h-4 w-4" /> {formatWhen(contest.starts_at)}</span>
              <span>{formatDuration(contest.duration_minutes)}</span>
              <span>{contest.problem_count} problems</span>
              <span className="inline-flex items-center gap-1"><Users className="h-4 w-4" /> {contest.participants} registered</span>
              <span>{contest.penalty_minutes} min penalty per rejected attempt</span>
            </p>
          </div>
          <div className="flex flex-col items-start gap-2 lg:items-end">
            {contest.phase !== "ended" ? (
              <div className="text-left lg:text-right">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  {contest.phase === "upcoming" ? "Starts in" : "Time left"}
                </div>
                <div className="font-mono text-3xl font-bold tabular-nums text-slate-900 dark:text-white" role="timer" aria-live="off">
                  {formatCountdown(remaining)}
                </div>
              </div>
            ) : (
              <div className="text-sm text-slate-500 dark:text-slate-400">The contest has ended. Submissions are closed.</div>
            )}
            {contest.registered ? (
              contest.problems.length > 0 && (
                <div className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                  Your score: {myScore} / {totalPoints}
                </div>
              )
            ) : contest.phase !== "ended" ? (
              <button
                onClick={() => void register()}
                disabled={registering}
                className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
              >
                {registering && <Loader2 className="h-4 w-4 animate-spin" />} Register
              </button>
            ) : null}
          </div>
        </div>

        {contest.description && (
          <div className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-700 dark:bg-slate-800">
            <Markdown source={contest.description} />
          </div>
        )}

        <div className="flex gap-1 border-b border-slate-200 dark:border-slate-700" role="tablist">
          {([
            ["problems", "Problems", ListChecks],
            ["leaderboard", "Leaderboard", Trophy],
            ["submissions", "My submissions", CalendarClock],
          ] as const).map(([key, label, Icon]) => (
            <button
              key={key}
              role="tab"
              aria-selected={tab === key}
              onClick={() => setTab(key)}
              className={`inline-flex items-center gap-1.5 border-b-2 px-4 py-2 text-sm font-semibold ${
                tab === key
                  ? "border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400"
                  : "border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
              }`}
            >
              <Icon className="h-4 w-4" /> {label}
            </button>
          ))}
        </div>

        {tab === "problems" &&
          (contest.problems.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 p-10 text-center text-slate-500 dark:border-slate-600 dark:text-slate-400">
              The problems are revealed when the contest starts.
              {!contest.registered && " Register now so you can submit as soon as it begins."}
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900/40 dark:text-slate-400">
                  <tr>
                    <th className="w-10 px-4 py-3"></th>
                    <th className="px-4 py-3">Problem</th>
                    <th className="px-4 py-3">Difficulty</th>
                    <th className="px-4 py-3 text-right">Points</th>
                    <th className="px-4 py-3 text-right">Solved by</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                  {contest.problems.map((p) => (
                    <tr key={p.slug} className="hover:bg-slate-50 dark:hover:bg-slate-700/40">
                      <td className="px-4 py-3"><StatusIcon status={p.status} /></td>
                      <td className="px-4 py-3">
                        <Link
                          href={`/candidate/problems/${p.slug}?contest=${encodeURIComponent(contest.slug)}`}
                          className="font-medium text-slate-900 hover:text-blue-600 dark:text-white dark:hover:text-blue-400"
                        >
                          {p.label}. {p.title}
                        </Link>
                      </td>
                      <td className="px-4 py-3"><DifficultyBadge difficulty={p.difficulty} /></td>
                      <td className="px-4 py-3 text-right font-semibold tabular-nums text-slate-700 dark:text-slate-200">{p.points}</td>
                      <td className="px-4 py-3 text-right tabular-nums text-slate-500 dark:text-slate-400">{p.solved_by}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}

        {tab === "leaderboard" && (
          <div className="space-y-2">
            {contest.phase === "running" && (
              <p className="text-xs text-slate-500 dark:text-slate-400">Updates every {LEADERBOARD_REFRESH_MS / 1000} seconds.</p>
            )}
            {!board || board.rows.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 p-10 text-center text-slate-500 dark:border-slate-600 dark:text-slate-400">
                {contest.phase === "upcoming" ? "The leaderboard opens when the contest starts." : "No participants yet."}
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
                <table className="w-full text-sm" aria-label="Leaderboard">
                  <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900/40 dark:text-slate-400">
                    <tr>
                      <th className="px-4 py-3">Rank</th>
                      <th className="px-4 py-3">Name</th>
                      <th className="px-4 py-3 text-right">Score</th>
                      <th className="px-4 py-3 text-right" title="Minutes to each accepted solution plus penalties">Penalty</th>
                      {board.labels.map((l) => (
                        <th key={l} className="px-3 py-3 text-center">{l}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                    {board.rows.map((r) => (
                      <tr key={r.user_id} className={r.is_me ? "bg-blue-50/70 dark:bg-blue-500/10" : ""}>
                        <td className="px-4 py-2.5 font-semibold tabular-nums text-slate-700 dark:text-slate-200">{r.rank}</td>
                        <td className="px-4 py-2.5 text-slate-900 dark:text-white">
                          {r.name}
                          {r.is_me && <span className="ml-1.5 text-xs font-semibold text-blue-600 dark:text-blue-400">(you)</span>}
                        </td>
                        <td className="px-4 py-2.5 text-right font-semibold tabular-nums text-slate-900 dark:text-white">{r.score}</td>
                        <td className="px-4 py-2.5 text-right tabular-nums text-slate-500 dark:text-slate-400">{r.penalty_minutes}</td>
                        {r.problems.map((cell) => (
                          <td key={cell.label} className="px-3 py-2.5 text-center tabular-nums">
                            {cell.solved ? (
                              <span className="font-semibold text-emerald-600 dark:text-emerald-400" title={`Solved at minute ${cell.solved_at_minutes}`}>
                                +{cell.rejected || ""}
                                <span className="block text-[11px] font-normal text-slate-500 dark:text-slate-400">{cell.solved_at_minutes}′</span>
                              </span>
                            ) : cell.rejected ? (
                              <span className="font-semibold text-rose-600 dark:text-rose-400">−{cell.rejected}</span>
                            ) : (
                              <span className="text-slate-300 dark:text-slate-600">·</span>
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {tab === "submissions" &&
          (mine.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 p-10 text-center text-slate-500 dark:border-slate-600 dark:text-slate-400">
              You have not submitted anything in this contest.
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900/40 dark:text-slate-400">
                  <tr>
                    <th className="px-4 py-3">Time</th>
                    <th className="px-4 py-3">Problem</th>
                    <th className="px-4 py-3">Verdict</th>
                    <th className="px-4 py-3">Language</th>
                    <th className="px-4 py-3 text-right">Tests</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                  {mine.map((s) => (
                    <tr key={s.id}>
                      <td className="px-4 py-2.5 text-slate-500 dark:text-slate-400">{new Date(s.created_at).toLocaleTimeString()}</td>
                      <td className="px-4 py-2.5">
                        <Link
                          href={`/candidate/problems/${s.problem_slug}?contest=${encodeURIComponent(contest.slug)}`}
                          className="font-medium text-slate-900 hover:text-blue-600 dark:text-white dark:hover:text-blue-400"
                        >
                          {s.label}
                        </Link>
                      </td>
                      <td className="px-4 py-2.5"><VerdictText verdict={s.verdict} /></td>
                      <td className="px-4 py-2.5 text-slate-600 dark:text-slate-300">{LANGUAGE_LABELS[s.language as PracticeLanguage] ?? s.language}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-slate-600 dark:text-slate-300">
                        {s.passed_count}/{s.total_count}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
      </div>
    </div>
  );
}
