import fs from 'fs';
import path from 'path';

const code = `"use client";
import React, { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { apiClient } from "@/services/apiClient";
import { toast } from "react-hot-toast";

export default function GradingDashboard() {
  const { id: examId } = useParams();
  const [loading, setLoading] = useState(true);
  const [sessions, setSessions] = useState<any[]>([]);
  const [plagiarismFlags, setPlagiarismFlags] = useState<any[]>([]);
  const [selectedSession, setSelectedSession] = useState<any | null>(null);

  useEffect(() => {
    fetchData();
  }, [examId]);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Fetch submissions
      const data = await apiClient.get<any[]>(\`/api/reports/\${examId}/grading\`);
      setSessions(data);
      
      // Fetch plagiarism flags
      try {
        const flags = await apiClient.get<any[]>(\`/api/reports/\${examId}/plagiarism\`);
        setPlagiarismFlags(flags);
      } catch (err) {
        console.error("Failed to load plagiarism flags");
      }
    } catch (err: any) {
      toast.error("Failed to load grading data");
    } finally {
      setLoading(false);
    }
  };

  const submitGrade = async (responseId: string, marks: number, isCorrect: boolean) => {
    try {
      await apiClient.post(\`/api/reports/grade/\${responseId}\`, {
        marks_awarded: marks,
        is_correct: isCorrect
      });
      toast.success("Grade saved!");
      
      // Update local state
      setSessions(prev => prev.map(s => {
        if (s.session_id === selectedSession?.session_id) {
          return {
            ...s,
            responses: s.responses.map((r: any) => 
              r.response_id === responseId ? { ...r, marks_awarded: marks, is_correct: isCorrect } : r
            )
          };
        }
        return s;
      });
      
      // Update selected session
      setSelectedSession((prev: any) => ({
        ...prev,
        responses: prev.responses.map((r: any) => 
          r.response_id === responseId ? { ...r, marks_awarded: marks, is_correct: isCorrect } : r
        )
      }));
    } catch (err) {
      toast.error("Failed to save grade");
    }
  };

  if (loading) return <div className="p-8 text-center text-slate-500">Loading submissions...</div>;

  return (
    <div className="max-w-7xl mx-auto p-4 md:p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Professor Grading Dashboard</h1>
        <p className="text-slate-500">Review code submissions and detect plagiarism</p>
      </div>
      
      {plagiarismFlags.length > 0 && (
        <div className="mb-8 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
          <h2 className="text-lg font-bold text-red-700 dark:text-red-400 mb-2 flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            Plagiarism Detected!
          </h2>
          <ul className="space-y-2">
            {plagiarismFlags.map((flag, idx) => (
              <li key={idx} className="text-sm text-red-800 dark:text-red-300">
                <span className="font-semibold">{flag.student_a}</span> and <span className="font-semibold">{flag.student_b}</span> have a <span className="font-bold underline">{flag.similarity_score}%</span> similarity match on Question ID {flag.question_id.slice(0, 8)}.
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="col-span-1 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-white dark:bg-slate-900 flex flex-col">
          <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 font-semibold shrink-0">
            Student Submissions
          </div>
          <div className="overflow-y-auto flex-1 max-h-[60vh] md:max-h-[800px]">
            {sessions.length === 0 ? (
              <div className="p-4 text-sm text-slate-500">No submissions found.</div>
            ) : (
              sessions.map(s => (
                <button
                  key={s.session_id}
                  onClick={() => setSelectedSession(s)}
                  className={\`w-full text-left p-4 border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors \${selectedSession?.session_id === s.session_id ? 'bg-indigo-50 dark:bg-indigo-900/20 border-l-4 border-l-indigo-600' : ''}\`}
                >
                  <div className="font-medium text-sm text-slate-900 dark:text-slate-100">{s.candidate_name}</div>
                  <div className="text-xs text-slate-500 truncate">{s.candidate_email}</div>
                  <div className="text-[10px] text-slate-400 mt-1">Submitted: {new Date(s.submitted_at).toLocaleString()}</div>
                </button>
              ))
            )}
          </div>
        </div>
        
        <div className="col-span-1 md:col-span-3">
          {!selectedSession ? (
            <div className="h-64 flex items-center justify-center text-slate-400 border border-slate-200 dark:border-slate-800 rounded-xl border-dashed">
              Select a student to view their submission.
            </div>
          ) : (
            <div className="space-y-6">
              <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
                <h2 className="text-xl font-bold mb-1 text-slate-900 dark:text-white">{selectedSession.candidate_name}</h2>
                <div className="text-sm text-slate-500 mb-6">{selectedSession.candidate_email}</div>
                
                <h3 className="font-semibold text-lg mb-4 border-b pb-2 dark:border-slate-800 text-slate-900 dark:text-white">Exam Answers</h3>
                {selectedSession.responses.length === 0 ? (
                  <p className="text-slate-500 text-sm">No answers submitted.</p>
                ) : (
                  <div className="space-y-8">
                    {selectedSession.responses.map((r: any, idx: number) => (
                      <div key={r.response_id} className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
                        <div className="bg-slate-50 dark:bg-slate-800 p-4 border-b border-slate-200 dark:border-slate-700 flex justify-between items-start flex-wrap gap-2">
                          <div>
                            <div className="font-semibold text-slate-800 dark:text-slate-200">Q{idx + 1}: {r.question_title}</div>
                            <div className="text-xs text-slate-500 mt-1">Type: {r.question_type} | Max Points: {r.question_points}</div>
                          </div>
                          <div className="flex flex-col items-end gap-2 shrink-0">
                            {r.marks_awarded !== null ? (
                              <span className="px-2 py-1 bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 text-xs font-bold rounded shadow-sm">
                                Graded: {r.marks_awarded} / {r.question_points}
                              </span>
                            ) : (
                              <span className="px-2 py-1 bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 text-xs font-bold rounded shadow-sm">
                                Needs Grading
                              </span>
                            )}
                          </div>
                        </div>
                        
                        <div className="p-4 overflow-x-hidden">
                          {r.question_type === "CODE" ? (
                            <pre className="bg-slate-950 text-slate-300 p-4 rounded-lg overflow-x-auto text-sm font-mono leading-relaxed shadow-inner max-w-full whitespace-pre-wrap break-all">
                              {r.response_data?.code || r.response_data?.text || "No code provided."}
                            </pre>
                          ) : (
                            <div className="text-sm text-slate-700 dark:text-slate-300 overflow-x-auto break-words">
                              {JSON.stringify(r.response_data)}
                            </div>
                          )}
                        </div>
                        
                        <div className="bg-slate-50 dark:bg-slate-900/50 p-4 border-t border-slate-200 dark:border-slate-700">
                          <form 
                            onSubmit={(e) => {
                              e.preventDefault();
                              const formData = new FormData(e.currentTarget as HTMLFormElement);
                              submitGrade(
                                r.response_id, 
                                Number(formData.get("marks")), 
                                formData.get("isCorrect") === "on"
                              );
                            }}
                            className="flex flex-wrap items-center gap-4"
                          >
                            <div className="flex items-center gap-2">
                              <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Marks:</label>
                              <input 
                                type="number" 
                                name="marks" 
                                step="0.5" 
                                max={r.question_points}
                                min={0}
                                defaultValue={r.marks_awarded ?? 0}
                                className="w-20 px-2 py-1 border rounded dark:bg-slate-800 dark:border-slate-600 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none" 
                                required
                              />
                              <span className="text-sm text-slate-500">/ {r.question_points}</span>
                            </div>
                            
                            <div className="flex items-center gap-2 ml-4">
                              <input 
                                type="checkbox" 
                                name="isCorrect" 
                                id={\`correct-\${r.response_id}\`}
                                defaultChecked={r.is_correct ?? false}
                                className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 dark:bg-slate-800 dark:border-slate-600"
                              />
                              <label htmlFor={\`correct-\${r.response_id}\`} className="text-sm font-medium text-slate-700 dark:text-slate-300">Mark as Correct</label>
                            </div>
                            
                            <button 
                              type="submit"
                              className="ml-auto px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-md shadow transition-colors w-full sm:w-auto mt-2 sm:mt-0"
                            >
                              Save Grade
                            </button>
                          </form>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
`;

const outPath = path.join('frontend', 'app', 'admin', 'exam', '[id]', 'grading');
fs.mkdirSync(outPath, { recursive: true });
fs.writeFileSync(path.join(outPath, 'page.tsx'), code);
