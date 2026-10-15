import React from "react";
import { CheckCircle2, CircleDashed, Circle } from "lucide-react";
import { Difficulty, ProblemStatus, Verdict, VERDICT_LABELS } from "@/services/practiceService";

const DIFFICULTY_STYLES: Record<Difficulty, string> = {
  EASY: "text-emerald-700 bg-emerald-50 border-emerald-200 dark:text-emerald-300 dark:bg-emerald-500/10 dark:border-emerald-500/30",
  MEDIUM: "text-amber-700 bg-amber-50 border-amber-200 dark:text-amber-300 dark:bg-amber-500/10 dark:border-amber-500/30",
  HARD: "text-rose-700 bg-rose-50 border-rose-200 dark:text-rose-300 dark:bg-rose-500/10 dark:border-rose-500/30",
};

export const DIFFICULTY_TEXT: Record<Difficulty, string> = {
  EASY: "text-emerald-600 dark:text-emerald-400",
  MEDIUM: "text-amber-600 dark:text-amber-400",
  HARD: "text-rose-600 dark:text-rose-400",
};

export function DifficultyBadge({ difficulty }: { difficulty: Difficulty }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${DIFFICULTY_STYLES[difficulty]}`}>
      {difficulty.charAt(0) + difficulty.slice(1).toLowerCase()}
    </span>
  );
}

export function StatusIcon({ status }: { status: ProblemStatus }) {
  if (status === "solved") return <CheckCircle2 className="h-4 w-4 text-emerald-500" aria-label="Solved" />;
  if (status === "attempted") return <CircleDashed className="h-4 w-4 text-amber-500" aria-label="Attempted" />;
  return <Circle className="h-4 w-4 text-slate-300 dark:text-slate-600" aria-label="Not started" />;
}

export function verdictColor(verdict: Verdict): string {
  if (verdict === "ACCEPTED") return "text-emerald-600 dark:text-emerald-400";
  if (verdict === "SYSTEM_ERROR" || verdict === "PENDING") return "text-slate-500 dark:text-slate-400";
  if (verdict === "COMPILE_ERROR") return "text-amber-600 dark:text-amber-400";
  return "text-rose-600 dark:text-rose-400";
}

export function VerdictText({ verdict, className = "" }: { verdict: Verdict; className?: string }) {
  return <span className={`font-semibold ${verdictColor(verdict)} ${className}`}>{VERDICT_LABELS[verdict]}</span>;
}
