"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import { CalendarClock, CheckCircle2, Loader2, Timer, Users } from "lucide-react";
import { PhaseBadge, formatWhen } from "@/components/contests/PhaseBadge";
import {
  ContestSummary,
  clockSkew,
  contestService,
  formatCountdown,
  formatDuration,
} from "@/services/contestService";

export default function ContestsPage() {
  const [contests, setContests] = useState<ContestSummary[] | null>(null);
  const [skew, setSkew] = useState(0);
  const [now, setNow] = useState(Date.now());
  const [error, setError] = useState<string | null>(null);
  const [registering, setRegistering] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await contestService.list();
      setContests(r.items);
      setSkew(clockSkew(r.server_time));
      setError(null);
    } catch (e: any) {
      setError(e?.message || "Failed to load contests.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Tick every second; reload when a countdown reaches zero so the phase flips.
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const serverNow = now + skew;
  useEffect(() => {
    if (!contests) return;
    const flipped = contests.some(
      (c) =>
        (c.phase === "upcoming" && new Date(c.starts_at).getTime() <= serverNow) ||
        (c.phase === "running" && new Date(c.ends_at).getTime() <= serverNow)
    );
    if (flipped) void load();
  }, [serverNow, contests, load]);

  const register = async (slug: string) => {
    setRegistering(slug);
    try {
      const updated = await contestService.register(slug);
      setContests((cs) => cs?.map((c) => (c.slug === slug ? { ...c, ...updated } : c)) ?? null);
      toast.success("You are registered.");
    } catch (e: any) {
      toast.error(e?.message || "Registration failed.");
    } finally {
      setRegistering(null);
    }
  };

  return (
    <div className="flex-1 overflow-auto p-6 pb-12 sm:p-8">
      <div className="mx-auto w-full max-w-5xl space-y-6">
        <div className="border-b border-slate-200 pb-5 dark:border-slate-700">
          <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-900 dark:text-white">
            <Timer className="h-7 w-7 text-blue-600 dark:text-blue-400" /> Contests
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Timed problem sets with a live leaderboard. Register, then solve as many problems as you can before the clock runs out.
          </p>
        </div>

        {error && <p className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300">{error}</p>}

        {!contests ? (
          <div className="flex items-center justify-center py-16 text-slate-500 dark:text-slate-400">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading contests…
          </div>
        ) : contests.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 p-10 text-center text-slate-500 dark:border-slate-600 dark:text-slate-400">
            No contests have been scheduled yet.
          </div>
        ) : (
          <ul className="space-y-3" aria-label="Contests">
            {contests.map((c) => {
              const target = c.phase === "upcoming" ? c.starts_at : c.ends_at;
              const remaining = new Date(target).getTime() - serverNow;
              return (
                <li
                  key={c.id}
                  className="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:flex-row sm:items-center dark:border-slate-700 dark:bg-slate-800"
                >
                  <div className="min-w-0 flex-1 space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <Link href={`/candidate/contests/${c.slug}`} className="text-lg font-semibold text-slate-900 hover:text-blue-600 dark:text-white dark:hover:text-blue-400">
                        {c.title}
                      </Link>
                      <PhaseBadge phase={c.phase} />
                      {c.registered && (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                          <CheckCircle2 className="h-3.5 w-3.5" /> Registered
                        </span>
                      )}
                    </div>
                    <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-slate-500 dark:text-slate-400">
                      <span className="inline-flex items-center gap-1"><CalendarClock className="h-4 w-4" /> {formatWhen(c.starts_at)}</span>
                      <span>{formatDuration(c.duration_minutes)}</span>
                      <span>{c.problem_count} problem{c.problem_count === 1 ? "" : "s"}</span>
                      <span className="inline-flex items-center gap-1"><Users className="h-4 w-4" /> {c.participants}</span>
                    </p>
                  </div>
                  <div className="flex items-center gap-3 sm:flex-col sm:items-end">
                    {c.phase !== "ended" && (
                      <span className="font-mono text-sm tabular-nums text-slate-700 dark:text-slate-200" aria-label={c.phase === "upcoming" ? "Starts in" : "Ends in"}>
                        {c.phase === "upcoming" ? "Starts in " : "Ends in "}
                        {formatCountdown(remaining)}
                      </span>
                    )}
                    {c.phase !== "ended" && !c.registered ? (
                      <button
                        onClick={() => void register(c.slug)}
                        disabled={registering === c.slug}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
                      >
                        {registering === c.slug && <Loader2 className="h-4 w-4 animate-spin" />} Register
                      </button>
                    ) : (
                      <Link
                        href={`/candidate/contests/${c.slug}`}
                        className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
                      >
                        {c.phase === "running" ? "Enter" : c.phase === "ended" ? "Results" : "View"}
                      </Link>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
