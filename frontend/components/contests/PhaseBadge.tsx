import React from "react";
import type { ContestPhase } from "@/services/contestService";

const PHASE_STYLES: Record<ContestPhase, string> = {
  running: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:border-emerald-500/30",
  upcoming: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-500/10 dark:text-blue-300 dark:border-blue-500/30",
  ended: "bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-700/50 dark:text-slate-300 dark:border-slate-600",
};
const PHASE_LABELS: Record<ContestPhase, string> = { running: "Live", upcoming: "Upcoming", ended: "Ended" };

export function PhaseBadge({ phase }: { phase: ContestPhase }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${PHASE_STYLES[phase]}`}>
      {phase === "running" && <span className="mr-1.5 h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />}
      {PHASE_LABELS[phase]}
    </span>
  );
}

export function formatWhen(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}
