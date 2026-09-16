"use client";

import React from "react";

interface SubmitModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirmSubmit: () => void;
  isSubmitting: boolean;
  totalQuestions: number;
  answeredCount: number;
  unansweredCount: number;
  flaggedCount: number;
}

export const SubmitModal: React.FC<SubmitModalProps> = ({
  isOpen,
  onClose,
  onConfirmSubmit,
  isSubmitting,
  totalQuestions,
  answeredCount,
  unansweredCount,
  flaggedCount,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-md w-full p-6 shadow-2xl">
        <div className="flex items-center gap-3 mb-4">
          <div className="h-10 w-10 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center shrink-0">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Submit Examination?</h3>
            <p className="text-xs text-slate-400">Please review your completion status below.</p>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-3 gap-2 my-5 bg-slate-950/60 p-3 rounded-xl border border-slate-800 text-center">
          <div>
            <div className="text-xs text-slate-400">Answered</div>
            <div className="text-xl font-bold text-emerald-400">{answeredCount}</div>
          </div>
          <div>
            <div className="text-xs text-slate-400">Unanswered</div>
            <div className={`text-xl font-bold ${unansweredCount > 0 ? "text-amber-400" : "text-slate-400"}`}>
              {unansweredCount}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-400">Flagged</div>
            <div className="text-xl font-bold text-amber-400">{flaggedCount}</div>
          </div>
        </div>

        {/* Warning if unanswered */}
        {unansweredCount > 0 && (
          <div className="p-3 bg-amber-950/40 border border-amber-800/50 rounded-lg text-xs text-amber-300 mb-5 flex items-start gap-2">
            <svg className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <span>You still have {unansweredCount} unanswered question{unansweredCount > 1 ? "s" : ""}. Once submitted, answers cannot be edited.</span>
          </div>
        )}

        <p className="text-xs text-slate-400 mb-6">
          Are you sure you want to finish and submit your exam? Your responses will be permanently locked.
        </p>

        {/* Buttons */}
        <div className="flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg transition-colors"
          >
            Review Questions
          </button>
          <button
            onClick={onConfirmSubmit}
            disabled={isSubmitting}
            className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg transition-all shadow-md shadow-emerald-600/30 flex items-center gap-2"
          >
            {isSubmitting ? (
              <>
                <svg className="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Submitting...
              </>
            ) : (
              "Confirm & Submit"
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
