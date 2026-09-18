"use client";

import React, { useState } from "react";
import dynamic from "next/dynamic";
import { QuestionCandidate } from "@/services/examService";
import { apiClient } from "@/services/apiClient";

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
  const [isExecuting, setIsExecuting] = useState(false);
  const [output, setOutput] = useState<string[]>([]);
  const [activeLang, setActiveLang] = useState("python");

  const runCode = async () => {
    if (!responseData?.text) return;
    setIsExecuting(true);
    setOutput(["Executing code..."]);
    try {
      // Ensure we extract session_id from URL or pass it down. 
      // For now, we assume window.location parsing or it's fetched. 
      // Actually, QuestionCard doesn't know session_id. Let's just pull it from pathname.
      const sessionId = window.location.pathname.split("/").pop();
      
      const data = await apiClient.post("/api/code/execute", {
        session_id: sessionId,
        question_id: question.id,
        language: activeLang,
        source_code: responseData.text
      });
      let outLines: string[] = [];
      if (data.stderr) {
         outLines.push("=== Error ===");
         outLines = outLines.concat(data.stderr.split('\\n'));
      }
      if (data.stdout) {
         outLines = outLines.concat(data.stdout.split('\\n'));
      }
      if (outLines.length === 0 || (outLines.length === 1 && outLines[0] === "")) {
        outLines = ["(Program exited successfully with no output)"];
      }
      setOutput(outLines.filter((line: string) => line.trim() !== ""));
    } catch (e: any) {
      setOutput([`Execution failed: ${e.message}`]);
    } finally {
      setIsExecuting(false);
    }
  };
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
          {question.type === "SQL" && (
            <div className="border border-slate-700 rounded-lg overflow-hidden flex flex-col h-[600px] mb-4">
              <div className="flex items-center justify-between bg-slate-800 px-4 py-2 border-b border-slate-700">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    SQL Editor (SQLite)
                  </span>
                </div>
                <button 
                  onClick={() => {
                     const old = activeLang;
                     setActiveLang("sql");
                     runCode().then(() => setActiveLang(old));
                  }}
                  disabled={isExecuting}
                  className="px-3 py-1 bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-600/40 rounded text-xs font-semibold flex items-center gap-1 transition-colors disabled:opacity-50"
                >
                  <svg className="w-3 h-3 fill-current" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg> 
                  {isExecuting ? "Executing..." : "Run Query"}
                </button>
              </div>
              
              {/* Schema Viewer */}
              {(question as any).database_schema && (
                <div className="bg-slate-900 border-b border-slate-700 p-3 overflow-x-auto text-xs text-slate-400 font-mono">
                  <div className="text-[10px] uppercase text-slate-500 mb-1 font-bold">Database Schema</div>
                  <pre>{(question as any).database_schema}</pre>
                </div>
              )}

              <div className="w-full h-[350px] md:h-[500px] border-b border-slate-700">
                <Editor
                  height="100%"
                  theme="vs-dark"
                  language="sql"
                  value={responseData?.text || "-- Write your SQL query here
"}
                  onChange={(val) => onAnswerChange({ text: val || "" })}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    lineHeight: 24,
                    padding: { top: 16, bottom: 16 },
                  }}
                />
              </div>
              {/* Output Panel */}
              <div className="h-48 border-t border-slate-700 bg-slate-900 text-slate-300 font-mono text-sm overflow-y-auto p-4 flex flex-col">
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-2 font-semibold">Query Result</div>
                {output.length > 0 ? (
                  output.map((line, i) => (
                    <div key={i} className="whitespace-pre-wrap">{line}</div>
                  ))
                ) : (
                  <div className="text-slate-600 italic">No output yet. Click 'Run Query' to execute.</div>
                )}
              </div>
            </div>
          )}



          {question.type === "CODING" && (
            <div className="border border-slate-700 rounded-lg overflow-hidden flex flex-col h-[600px] mb-4">
              <div className="flex items-center justify-between bg-slate-800 px-4 py-2 border-b border-slate-700">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Code Editor
                  </span>
                  <select 
                    value={activeLang}
                    onChange={(e) => setActiveLang(e.target.value)}
                    className="bg-slate-900 border border-slate-700 text-xs text-white rounded px-2 py-1 outline-none"
                  >
                    <option value="python">Python</option>
                    <option value="javascript">JavaScript</option>
                    <option value="java">Java</option>
                    <option value="c">C</option>
                    <option value="cpp">C++</option>
                  </select>
                </div>
                <button 
                  onClick={runCode}
                  disabled={isExecuting}
                  className="px-3 py-1 bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-600/40 rounded text-xs font-semibold flex items-center gap-1 transition-colors disabled:opacity-50"
                >
                  <svg className="w-3 h-3 fill-current" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg> 
                  {isExecuting ? "Running..." : "Run Code"}
                </button>
              </div>
              <div className="w-full h-[350px] md:h-[500px] border-b border-slate-700">
                <Editor
                  height="100%"
                  theme="vs-dark"
                  language={activeLang}
                  value={responseData?.text || "# Write your code here\\n"}
                  onChange={(val) => onAnswerChange({ text: val || "" })}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    lineHeight: 24,
                    padding: { top: 16, bottom: 16 },
                  }}
                />
              </div>
              {/* Output Panel */}
              <div className="h-48 border-t border-slate-700 bg-slate-900 text-slate-300 font-mono text-sm overflow-y-auto p-4 flex flex-col">
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-2 font-semibold">Console Output</div>
                {output.length > 0 ? (
                  output.map((line, i) => (
                    <div key={i} className="whitespace-pre-wrap">{line}</div>
                  ))
                ) : (
                  <div className="text-slate-600 italic">No output yet. Click 'Run Code' to test your solution.</div>
                )}
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
