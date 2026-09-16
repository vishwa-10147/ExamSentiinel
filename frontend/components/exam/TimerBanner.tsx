"use client";

import React, { useEffect, useState } from "react";

interface TimerBannerProps {
  initialSeconds: number;
  onTimeout?: () => void;
  examTitle?: string;
}

export const TimerBanner: React.FC<TimerBannerProps> = ({
  initialSeconds,
  onTimeout,
  examTitle,
}) => {
  const [secondsLeft, setSecondsLeft] = useState<number>(initialSeconds);

  useEffect(() => {
    setSecondsLeft(initialSeconds);
  }, [initialSeconds]);

  useEffect(() => {
    if (secondsLeft <= 0) {
      if (onTimeout) onTimeout();
      return;
    }

    const timer = setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          if (onTimeout) onTimeout();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [secondsLeft, onTimeout]);

  const hours = Math.floor(secondsLeft / 3600);
  const minutes = Math.floor((secondsLeft % 3600) / 60);
  const seconds = secondsLeft % 60;

  const formattedTime = `${hours > 0 ? `${String(hours).padStart(2, "0")}:` : ""}${String(
    minutes
  ).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;

  const isWarning = secondsLeft > 60 && secondsLeft <= 300; // <= 5 mins
  const isCritical = secondsLeft <= 60; // <= 1 min

  return (
    <div className="w-full">
      {/* 5-minute warning banner */}
      {isWarning && (
        <div className="bg-amber-950/80 border-b border-amber-600/50 px-4 py-2 text-center text-amber-200 text-xs font-semibold flex items-center justify-center gap-2 animate-pulse">
          <svg className="w-4 h-4 text-amber-400 shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          Warning: Less than 5 minutes remaining! Complete and review your answers.
        </div>
      )}

      {/* 1-minute critical banner */}
      {isCritical && secondsLeft > 0 && (
        <div className="bg-red-950/90 border-b border-red-600 px-4 py-2 text-center text-red-200 text-xs font-bold flex items-center justify-center gap-2 animate-bounce">
          <svg className="w-4 h-4 text-red-400 shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          Critical: Under 60 seconds! Your exam will automatically submit on timeout.
        </div>
      )}

      <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 shadow-inner">
        <svg className={`w-4 h-4 ${isCritical ? "text-red-400 animate-spin" : isWarning ? "text-amber-400" : "text-slate-400"}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Time Remaining:</span>
        <span
          className={`font-mono font-bold text-sm tracking-widest ${
            isCritical ? "text-red-400" : isWarning ? "text-amber-400" : "text-white"
          }`}
        >
          {formattedTime}
        </span>
      </div>
    </div>
  );
};
