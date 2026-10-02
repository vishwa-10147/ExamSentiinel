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
    if (data.selected_option_id !== undefined && data.selected_option_id !== null && String(data.selected_option_id).trim() !== "") return true;
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
    <div className="bg-white border border-slate-200 rounded-2xl p-5 flex flex-col h-full shadow-sm">
      <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-4">Question Palette</h3>

      {/* Legend & Stats */}
      <div className="grid grid-cols-3 gap-2 mb-5 text-center">
        <div className="bg-emerald-50 p-2.5 rounded-xl border border-emerald-100">
          <div className="text-[11px] font-semibold text-emerald-700">Answered</div>
          <div className="text-lg font-bold text-emerald-800">{answeredCount}</div>
        </div>
        <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
          <div className="text-[11px] font-semibold text-slate-500">Unanswered</div>
          <div className="text-lg font-bold text-slate-700">{unansweredCount}</div>
        </div>
        <div className="bg-amber-50 p-2.5 rounded-xl border border-amber-100">
          <div className="text-[11px] font-semibold text-amber-700">Flagged</div>
          <div className="text-lg font-bold text-amber-800">{flaggedCount}</div>
        </div>
      </div>

      {/* Palette Buttons */}
      <div className="grid grid-cols-5 gap-2 overflow-y-auto max-h-[350px] p-1">
        {questions.map((q, idx) => {
          const active = idx === currentIndex;
          const answered = isAnswered(q.id);
          const flagged = isFlagged(q.id);

          let buttonClasses = "relative h-10 w-10 flex items-center justify-center rounded-xl font-bold text-xs transition-all ";

          if (active) {
            buttonClasses += "ring-2 ring-blue-600 ring-offset-2 ring-offset-white font-extrabold shadow-md ";
          }

          if (answered) {
            buttonClasses += "bg-emerald-600 text-white shadow-sm hover:bg-emerald-700 ";
          } else {
            buttonClasses += "bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200 ";
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
                <span className="absolute -top-1 -right-1 h-3.5 w-3.5 bg-amber-500 rounded-full border-2 border-white flex items-center justify-center shadow-sm">
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
