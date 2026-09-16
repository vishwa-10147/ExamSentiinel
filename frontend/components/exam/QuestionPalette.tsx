"use client";

import React from "react";
import { CandidateResponse, QuestionCandidate } from "@/services/examService";

interface QuestionPaletteProps {
  questions: QuestionCandidate[];
  currentIndex: number;
  responses: Record<string, CandidateResponse>;
  onSelectQuestion: (index: number) => void;
}

export const QuestionPalette: React.FC<QuestionPaletteProps> = ({
  questions,
  currentIndex,
  responses,
  onSelectQuestion,
}) => {
  const isAnswered = (qId: string) => {
    const resp = responses[qId];
    if (!resp || !resp.response_data) return false;
    const data = resp.response_data;
    if (data.selected_option_id) return true;
    if (Array.isArray(data.selected_option_ids) && data.selected_option_ids.length > 0) return true;
    if (typeof data.text === "string" && data.text.trim().length > 0) return true;
    return false;
  };

  const isFlagged = (qId: string) => {
    return !!responses[qId]?.is_flagged;
  };

  const answeredCount = questions.filter((q) => isAnswered(q.id)).length;
  const flaggedCount = questions.filter((q) => isFlagged(q.id)).length;
  const unansweredCount = questions.length - answeredCount;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col h-full">
      <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-3">Question Palette</h3>

      {/* Legend & Stats */}
      <div className="grid grid-cols-3 gap-2 mb-4 text-center">
        <div className="bg-slate-800/80 p-2 rounded-lg border border-slate-700">
          <div className="text-xs text-slate-400">Answered</div>
          <div className="text-lg font-bold text-emerald-400">{answeredCount}</div>
        </div>
        <div className="bg-slate-800/80 p-2 rounded-lg border border-slate-700">
          <div className="text-xs text-slate-400">Unanswered</div>
          <div className="text-lg font-bold text-slate-300">{unansweredCount}</div>
        </div>
        <div className="bg-slate-800/80 p-2 rounded-lg border border-slate-700">
          <div className="text-xs text-slate-400">Flagged</div>
          <div className="text-lg font-bold text-amber-400">{flaggedCount}</div>
        </div>
      </div>

      {/* Palette Buttons */}
      <div className="grid grid-cols-5 gap-2 overflow-y-auto max-h-[350px] p-1">
        {questions.map((q, idx) => {
          const active = idx === currentIndex;
          const answered = isAnswered(q.id);
          const flagged = isFlagged(q.id);

          let buttonClasses = "relative h-10 w-10 flex items-center justify-center rounded-lg font-semibold text-xs transition-all ";

          if (active) {
            buttonClasses += "ring-2 ring-indigo-500 ring-offset-2 ring-offset-slate-950 font-bold ";
          }

          if (answered) {
            buttonClasses += "bg-emerald-600/90 text-white hover:bg-emerald-500 ";
          } else {
            buttonClasses += "bg-slate-800 text-slate-300 hover:bg-slate-700 ";
          }

          return (
            <button
              key={q.id}
              onClick={() => onSelectQuestion(idx)}
              className={buttonClasses}
              title={`Question ${idx + 1}: ${answered ? "Answered" : "Unanswered"}${flagged ? " (Flagged)" : ""}`}
            >
              {idx + 1}
              {flagged && (
                <span className="absolute -top-1 -right-1 h-3.5 w-3.5 bg-amber-500 rounded-full border-2 border-slate-900 flex items-center justify-center">
                  <span className="block h-1 w-1 bg-white rounded-full"></span>
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
