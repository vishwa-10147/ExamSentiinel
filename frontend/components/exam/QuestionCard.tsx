"use client";

import React from "react";
import dynamic from "next/dynamic";
import { QuestionCandidate } from "@/services/examService";

// Lazy load Monaco Editor (massive bundle) only when needed, disable SSR
const Editor = dynamic(() => import("@monaco-editor/react"), { 
  ssr: false, 
  loading: () => <div className="w-full h-full flex items-center justify-center text-slate-500 text-sm">Loading IDE...</div>
});

interface QuestionCardProps {
  question: QuestionCandidate;
  index: number;
  total: number;
  responseData: any;
  isFlagged: boolean;
  onAnswerChange: (data: any) => void;
  onToggleFlag: () => void;
  onClearResponse: () => void;
  onNext: () => void;
  onPrev: () => void;
  isFirst: boolean;
  isLast: boolean;
}

export const QuestionCard: React.FC<QuestionCardProps> = ({
  question,
  index,
  total,
  responseData,
  isFlagged,
  onAnswerChange,
  onToggleFlag,
  onClearResponse,
  onNext,
  onPrev,
  isFirst,
  isLast,
}) => {
  const handleSingleOption = (optId: string) => {
    onAnswerChange({ selected_option_id: optId });
  };

  const handleMultiOption = (optId: string) => {
    const currentList: string[] = Array.isArray(responseData?.selected_option_ids)
      ? [...responseData.selected_option_ids]
      : [];
    const idx = currentList.indexOf(optId);
    if (idx >= 0) {
      currentList.splice(idx, 1);
    } else {
      currentList.push(optId);
    }
    onAnswerChange({ selected_option_ids: currentList });
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    onAnswerChange({ text: e.target.value });
  };

  const essayWordCount = (responseData?.text || "")
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col justify-between min-h-[500px] shadow-lg">
      <div>
        {/* Header Bar */}
        <div className="flex flex-wrap items-center justify-between pb-4 mb-4 border-b border-slate-800 gap-2">
          <div className="flex items-center gap-3">
            <span className="px-3 py-1 bg-indigo-600/30 text-indigo-400 border border-indigo-500/30 rounded-full text-xs font-semibold">
              Question {index + 1} of {total}
            </span>
            <span className="text-xs font-medium text-slate-400">
              Points: <strong className="text-slate-200">{question.points}</strong>
            </span>
            <span className="px-2.5 py-0.5 bg-slate-800 text-slate-300 rounded text-xs">
              {question.type.replace("_", " ")}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onToggleFlag}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                isFlagged
                  ? "bg-amber-500/20 text-amber-300 border-amber-500/50"
                  : "bg-slate-800 text-slate-400 border-slate-700 hover:text-white"
              }`}
            >
              <svg
                className={`w-3.5 h-3.5 ${isFlagged ? "fill-amber-400 text-amber-400" : "fill-none text-current"}`}
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9"
                />
              </svg>
              {isFlagged ? "Flagged for Review" : "Flag for Review"}
            </button>
            <button
              onClick={onClearResponse}
              className="px-2.5 py-1.5 text-xs text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-lg transition-colors"
            >
              Clear
            </button>
          </div>
        </div>

        {/* Title & Content */}
        <h2 className="text-lg font-bold text-white mb-2">{question.title}</h2>
        <div
          className="prose prose-invert prose-slate max-w-none text-slate-300 text-sm mb-6 leading-relaxed"
          dangerouslySetInnerHTML={{ __html: question.content_rich_text }}
        />

        {/* Answer Options / Inputs */}
        <div className="space-y-3 mt-4">
          {question.type === "MCQ_SINGLE" && question.options && (
            <div className="space-y-2">
              {question.options.map((opt) => {
                const selected = responseData?.selected_option_id === opt.id;
                return (
                  <label
                    key={opt.id}
                    onClick={() => handleSingleOption(opt.id)}
                    className={`flex items-center gap-3 p-3.5 rounded-lg border cursor-pointer transition-all ${
                      selected
                        ? "bg-indigo-950/50 border-indigo-500 text-white shadow-sm"
                        : "bg-slate-800/60 border-slate-700 text-slate-300 hover:bg-slate-800 hover:border-slate-600"
                    }`}
                  >
                    <input
                      type="radio"
                      name={`question_${question.id}`}
                      checked={selected}
                      onChange={() => handleSingleOption(opt.id)}
                      className="text-indigo-600 focus:ring-indigo-500 h-4 w-4 bg-slate-900 border-slate-600"
                    />
                    <span className="text-sm">{opt.text}</span>
                  </label>
                );
              })}
            </div>
          )}

          {question.type === "MCQ_MULTI" && question.options && (
            <div className="space-y-2">
              <p className="text-xs text-slate-400 italic mb-1">Select all options that apply:</p>
              {question.options.map((opt) => {
                const checked =
                  Array.isArray(responseData?.selected_option_ids) &&
                  responseData.selected_option_ids.includes(opt.id);
                return (
                  <label
                    key={opt.id}
                    onClick={() => handleMultiOption(opt.id)}
                    className={`flex items-center gap-3 p-3.5 rounded-lg border cursor-pointer transition-all ${
                      checked
                        ? "bg-indigo-950/50 border-indigo-500 text-white"
                        : "bg-slate-800/60 border-slate-700 text-slate-300 hover:bg-slate-800 hover:border-slate-600"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => handleMultiOption(opt.id)}
                      className="text-indigo-600 rounded focus:ring-indigo-500 h-4 w-4 bg-slate-900 border-slate-600"
                    />
                    <span className="text-sm">{opt.text}</span>
                  </label>
                );
              })}
            </div>
          )}

          {question.type === "SHORT_ANSWER" && (
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Your Answer:
              </label>
              <input
                type="text"
                value={responseData?.text || ""}
                onChange={handleTextChange}
                placeholder="Type your brief answer here..."
                className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
              />
            </div>
          )}

          {question.type === "ESSAY" && (
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Essay Response:
                </label>
                <span className="text-xs text-slate-400 font-mono">Words: {essayWordCount}</span>
              </div>
              <textarea
                value={responseData?.text || ""}
                onChange={handleTextChange}
                rows={8}
                placeholder="Write your comprehensive response here..."
                className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm font-sans"
              />
            </div>
          )}

          {question.type === "CODING" && (
            <div className="border border-slate-700 rounded-lg overflow-hidden flex flex-col h-[400px]">
              <div className="flex items-center justify-between bg-slate-800 px-4 py-2 border-b border-slate-700">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Code Editor
                  </span>
                  <select className="bg-slate-900 border border-slate-700 text-xs text-white rounded px-2 py-1 outline-none">
                    <option value="python">Python</option>
                    <option value="javascript">JavaScript</option>
                    <option value="typescript">TypeScript</option>
                    <option value="java">Java</option>
                    <option value="cpp">C++</option>
                  </select>
                </div>
                <button className="px-3 py-1 bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-600/40 rounded text-xs font-semibold flex items-center gap-1 transition-colors">
                  <svg className="w-3 h-3 fill-current" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg> Run Code
                </button>
              </div>
              <div className="flex-1">
                <Editor
                  height="100%"
                  theme="vs-dark"
                  defaultLanguage="python"
                  value={responseData?.text || "# Write your code here\n"}
                  onChange={(val) => onAnswerChange({ text: val || "" })}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    padding: { top: 16 },
                    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                  }}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer Navigation */}
      <div className="flex items-center justify-between pt-6 mt-6 border-t border-slate-800">
        <button
          onClick={onPrev}
          disabled={isFirst}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
            isFirst
              ? "bg-slate-800 text-slate-500 cursor-not-allowed"
              : "bg-slate-800 text-slate-200 hover:bg-slate-700 hover:text-white"
          }`}
        >
          &larr; Previous
        </button>

        <button
          onClick={onNext}
          disabled={isLast}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
            isLast
              ? "bg-slate-800 text-slate-500 cursor-not-allowed"
              : "bg-indigo-600 text-white hover:bg-indigo-500 shadow-md shadow-indigo-600/30"
          }`}
        >
          Next &rarr;
        </button>
      </div>
    </div>
  );
};
