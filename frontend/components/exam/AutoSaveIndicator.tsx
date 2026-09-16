"use client";

import React from "react";

export type SaveStatus = "saved" | "saving" | "offline" | "error";

interface AutoSaveIndicatorProps {
  status: SaveStatus;
  lastSavedAt?: Date | null;
}

export const AutoSaveIndicator: React.FC<AutoSaveIndicatorProps> = ({
  status,
  lastSavedAt,
}) => {
  return (
    <div className="flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-full bg-slate-800 border border-slate-700">
      {status === "saving" && (
        <>
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
          </span>
          <span className="text-amber-400">Saving...</span>
        </>
      )}

      {status === "saved" && (
        <>
          <span className="inline-block h-2 w-2 rounded-full bg-emerald-500"></span>
          <span className="text-emerald-400">
            Saved {lastSavedAt ? `at ${lastSavedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}` : ""}
          </span>
        </>
      )}

      {status === "offline" && (
        <>
          <span className="inline-block h-2 w-2 rounded-full bg-amber-500"></span>
          <span className="text-amber-300">Offline (Saved locally)</span>
        </>
      )}

      {status === "error" && (
        <>
          <span className="inline-block h-2 w-2 rounded-full bg-red-500"></span>
          <span className="text-red-400">Failed to save (Retrying...)</span>
        </>
      )}
    </div>
  );
};
