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
  sessionId?: string;
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
  sessionId,
}) => {
  const [isExecuting, setIsExecuting] = useState(false);
  const [output, setOutput] = useState<string[]>([]);
  const [activeLang, setActiveLang] = useState("python");

  const runCode = async (languageOverride = activeLang) => {
    if (!responseData?.text) return;
    setIsExecuting(true);
    setOutput(["Executing code..."]);
    try {
      if (!sessionId) throw new Error("Exam session is not ready");
      
      const data = await apiClient.post<any>("/api/code/execute", {
        session_id: sessionId,
        question_id: question.id,
        language: languageOverride,
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

  const normalizeOptions = (rawOptions: any): Array<{ id: string; text: string }> => {
    if (!rawOptions) return [];
    let opts = rawOptions;
    if (typeof opts === "string") {
      try {
        opts = JSON.parse(opts);
      } catch {
        opts = [rawOptions];
      }
    }
    if (!Array.isArray(opts)) return [];
    return opts.map((opt, idx) => {
      if (typeof opt === "string" || typeof opt === "number") {
        return { id: String(opt), text: String(opt) };
      }
      if (opt && typeof opt === "object") {
        const id = String(opt.id ?? opt.value ?? opt.text ?? idx);
        const text = String(opt.text ?? opt.label ?? opt.value ?? opt.id ?? "");
        return { id, text };
      }
      return { id: String(idx), text: String(opt) };
    });
  };

  const normalizedOptions = normalizeOptions(question.options);

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 flex flex-col justify-between min-h-[500px] shadow-sm select-none">
      <div>
        {/* Header Bar */}
        <div className="flex flex-wrap items-center justify-between pb-4 mb-4 border-b border-slate-100 gap-2">
          <div className="flex items-center gap-3">
            <span className="px-3 py-1 bg-blue-50 text-blue-700 border border-blue-200 rounded-full text-xs font-bold">
              Question {index + 1} of {total}
            </span>
            <span className="text-xs font-medium text-slate-500">
              Points: <strong className="text-slate-900">{question.points}</strong>
            </span>
            <span className="px-2.5 py-0.5 bg-slate-100 text-slate-700 rounded-md text-xs font-semibold">
              {question.type.replace("_", " ")}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onToggleFlag}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                isFlagged
                  ? "bg-amber-50 text-amber-700 border-amber-300 font-bold"
                  : "bg-slate-100 text-slate-600 border-slate-200 hover:text-slate-900 hover:bg-slate-200"
              }`}
            >
              <svg
                className={`w-3.5 h-3.5 ${isFlagged ? "fill-amber-500 text-amber-500" : "fill-none text-current"}`}
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
              className="px-2.5 py-1.5 text-xs text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors font-medium"
            >
              Clear
            </button>
          </div>
        </div>

        {/* Title & Content */}
        <h2 className="text-lg font-bold text-slate-900 mb-2">{question.title}</h2>
        <div
          className="prose prose-slate max-w-none text-slate-700 text-sm mb-6 leading-relaxed"
          dangerouslySetInnerHTML={{ __html: question.content_rich_text }}
        />

        {/* Answer Options / Inputs */}
        <div className="space-y-3 mt-4">
          {question.type === "MCQ_SINGLE" && (
            <div className="space-y-2.5">
              {normalizedOptions.length === 0 ? (
                <p className="text-xs text-slate-500 italic">No options provided for this question.</p>
              ) : (
                normalizedOptions.map((opt) => {
                  const selected = String(responseData?.selected_option_id) === String(opt.id);
                  return (
                    <div
                      key={opt.id}
                      onClick={() => handleSingleOption(opt.id)}
                      className={`flex items-center gap-3.5 p-3.5 rounded-xl border cursor-pointer transition-all ${
                        selected
                          ? "bg-blue-50/80 border-blue-600 text-blue-950 font-semibold shadow-sm ring-1 ring-blue-500/20"
                          : "bg-slate-50/80 border-slate-200 text-slate-800 hover:bg-white hover:border-slate-300 hover:shadow-sm"
                      }`}
                    >
                      <div className={`w-4 h-4 rounded-full border flex items-center justify-center shrink-0 transition-colors ${
                        selected ? "border-blue-600 bg-blue-600" : "border-slate-400 bg-white"
                      }`}>
                        {selected && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                      </div>
                      <span className="text-sm font-medium leading-normal">{opt.text}</span>
                    </div>
                  );
                })
              )}
            </div>
          )}

          {question.type === "MCQ_MULTI" && (
            <div className="space-y-2.5">
              <p className="text-xs text-slate-500 italic mb-1">Select all options that apply:</p>
              {normalizedOptions.length === 0 ? (
                <p className="text-xs text-slate-500 italic">No options provided for this question.</p>
              ) : (
                normalizedOptions.map((opt) => {
                  const checked =
                    Array.isArray(responseData?.selected_option_ids) &&
                    responseData.selected_option_ids.map(String).includes(String(opt.id));
                  return (
                    <div
                      key={opt.id}
                      onClick={() => handleMultiOption(opt.id)}
                      className={`flex items-center gap-3.5 p-3.5 rounded-xl border cursor-pointer transition-all ${
                        checked
                          ? "bg-blue-50/80 border-blue-600 text-blue-950 font-semibold shadow-sm ring-1 ring-blue-500/20"
                          : "bg-slate-50/80 border-slate-200 text-slate-800 hover:bg-white hover:border-slate-300 hover:shadow-sm"
                      }`}
                    >
                      <div className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 transition-colors ${
                        checked ? "border-blue-600 bg-blue-600" : "border-slate-400 bg-white"
                      }`}>
                        {checked && (
                          <svg className="w-3 h-3 text-white fill-current" viewBox="0 0 20 20">
                            <path d="M0 11l2-2 5 5L18 3l2 2L7 18z" />
                          </svg>
                        )}
                      </div>
                      <span className="text-sm font-medium leading-normal">{opt.text}</span>
                    </div>
                  );
                })
              )}
            </div>
          )}

          {question.type === "SHORT_ANSWER" && (
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                Your Answer:
              </label>
              <input
                type="text"
                value={responseData?.text || ""}
                onChange={handleTextChange}
                placeholder="Type your brief answer here..."
                className="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm shadow-sm"
              />
            </div>
          )}

          {question.type === "ESSAY" && (
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Essay Response:
                </label>
                <span className="text-xs text-slate-500 font-mono">Words: {essayWordCount}</span>
              </div>
              <textarea
                value={responseData?.text || ""}
                onChange={handleTextChange}
                rows={8}
                placeholder="Write your comprehensive response here..."
                className="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm font-sans shadow-sm"
              />
            </div>
          )}
          {question.type === "SQL" && (
            <div className="border border-slate-200 rounded-xl overflow-hidden flex flex-col h-[600px] mb-4 bg-white shadow-sm">
              <div className="flex items-center justify-between bg-slate-50 px-4 py-2 border-b border-slate-200">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                    SQL Editor (SQLite)
                  </span>
                </div>
                <button 
                  onClick={() => {
                     const old = activeLang;
                     setActiveLang("sql");
                     runCode("sql").then(() => setActiveLang(old));
                  }}
                  disabled={isExecuting}
                  className="px-3 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 rounded-lg text-xs font-bold flex items-center gap-1 transition-colors disabled:opacity-50"
                >
                  <svg className="w-3 h-3 fill-current" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg> 
                  {isExecuting ? "Executing..." : "Run Query"}
                </button>
              </div>
              
              {/* Schema Viewer */}
              {(question as any).database_schema && (
                <div className="bg-slate-50 border-b border-slate-200 p-3 overflow-x-auto text-xs text-slate-700 font-mono">
                  <div className="text-[10px] uppercase text-slate-500 mb-1 font-bold">Database Schema</div>
                  <pre>{(question as any).database_schema}</pre>
                </div>
              )}

              <div className="w-full h-[350px] md:h-[500px] border-b border-slate-200">
                <Editor
                  height="100%"
                  theme="vs"
                  language="sql"
                  value={responseData?.text || "-- Write your SQL query here\n"}
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
              <div className="h-48 border-t border-slate-200 bg-slate-50 text-slate-800 font-mono text-sm overflow-y-auto p-4 flex flex-col">
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-2 font-bold">Query Result</div>
                {output.length > 0 ? (
                  output.map((line, i) => (
                    <div key={i} className="whitespace-pre-wrap">{line}</div>
                  ))
                ) : (
                  <div className="text-slate-400 italic">No output yet. Click &apos;Run Query&apos; to execute.</div>
                )}
              </div>
            </div>
          )}

          {question.type === "CODING" && (
            <div className="border border-slate-200 rounded-xl overflow-hidden flex flex-col h-[600px] mb-4 bg-white shadow-sm">
              <div className="flex items-center justify-between bg-slate-50 px-4 py-2 border-b border-slate-200">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                    Code Editor
                  </span>
                  <select 
                    value={activeLang}
                    onChange={(e) => {
                      setActiveLang(e.target.value);
                      onAnswerChange({ text: responseData?.text || "", language: e.target.value });
                    }}
                    className="bg-white border border-slate-200 text-xs text-slate-800 rounded-lg px-2 py-1 outline-none font-medium"
                  >
                    <option value="python">Python</option>
                    <option value="javascript">JavaScript</option>
                    <option value="java">Java</option>
                    <option value="c">C</option>
                    <option value="cpp">C++</option>
                  </select>
                </div>
                <button 
                  onClick={() => runCode()}
                  disabled={isExecuting}
                  className="px-3 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 rounded-lg text-xs font-bold flex items-center gap-1 transition-colors disabled:opacity-50"
                >
                  <svg className="w-3 h-3 fill-current" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg> 
                  {isExecuting ? "Running..." : "Run Code"}
                </button>
              </div>
              <div className="w-full h-[350px] md:h-[500px] border-b border-slate-200">
                <Editor
                  height="100%"
                  theme="vs"
                  language={activeLang}
                  value={responseData?.text || "# Write your code here\n"}
                  onChange={(val) => onAnswerChange({ text: val || "", language: activeLang })}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    lineHeight: 24,
                    padding: { top: 16, bottom: 16 },
                  }}
                />
              </div>
              {/* Output Panel */}
              <div className="h-48 border-t border-slate-200 bg-slate-50 text-slate-800 font-mono text-sm overflow-y-auto p-4 flex flex-col">
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-2 font-bold">Console Output</div>
                {output.length > 0 ? (
                  output.map((line, i) => (
                    <div key={i} className="whitespace-pre-wrap">{line}</div>
                  ))
                ) : (
                  <div className="text-slate-400 italic">No output yet. Click &apos;Run Code&apos; to test your solution.</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer Navigation */}
      <div className="flex items-center justify-between pt-6 mt-6 border-t border-slate-100">
        <button
          onClick={onPrev}
          disabled={isFirst}
          className={`flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-bold transition-all ${
            isFirst
              ? "bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200"
              : "bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-250"
          }`}
        >
          &larr; Previous
        </button>

        <button
          onClick={onNext}
          disabled={isLast}
          className={`flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-xs font-bold transition-all ${
            isLast
              ? "bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200"
              : "bg-blue-600 text-white hover:bg-blue-700 shadow-md shadow-blue-500/20"
          }`}
        >
          Next &rarr;
        </button>
      </div>
    </div>
  );
};
