"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/services/apiClient";
import { Editor } from "@monaco-editor/react";
import { Loader2, AlertCircle, Play, ChevronLeft, Terminal, CheckCircle2, XCircle } from "lucide-react";
import toast from "react-hot-toast";

interface QuestionDetail {
  id: string;
  title: string;
  difficulty: "Easy" | "Medium" | "Hard" | string;
  content_rich_text?: string;
  prompt?: string;
}

export default function SolveProblemPage() {
  const params = useParams();
  const router = useRouter();
  const { id } = params as { id: string };

  const [question, setQuestion] = useState<QuestionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  
  const [code, setCode] = useState<string>("// Write your solution here\n");
  const [language, setLanguage] = useState("javascript");
  const [submitting, setSubmitting] = useState(false);
  const [results, setResults] = useState<any>(null);

  // Tab state for the left pane
  const [leftTab, setLeftTab] = useState("description");
  // Tab state for the right bottom pane
  const [rightBottomTab, setRightBottomTab] = useState("testcases");

  useEffect(() => {
    const fetchQuestion = async () => {
      try {
        const response = await apiClient.get(`/api/questions/${id}`);
        const data = (response as any).data?.question || (response as any).data || (response as any);
        if (data && data.title) {
          setQuestion(data);
        } else {
          setQuestion({
            id,
            title: data?.title || `Question ${id}`,
            difficulty: data?.difficulty || "Medium",
            content_rich_text: "Failed to load description.",
          });
        }
      } catch (err: any) {
        setError(err.message || "Failed to load question details");
        toast.error("Failed to load question details");
      } finally {
        setLoading(false);
      }
    };
    if (id) {
      fetchQuestion();
    }
  }, [id]);

  const handleSubmit = async () => {
    setSubmitting(true);
    setResults(null);
    setRightBottomTab("testcases"); // auto switch to output
    
    try {
      const response = await apiClient.post<any>(`/api/questions/${id}/submit`, { code, language });
      setResults(response);
      if (response.overall_passed) {
        toast.success("All test cases passed! Great job!");
      } else {
        toast.error("Some test cases failed. Keep trying!");
      }
    } catch (err: any) {
      toast.error(err.message || "Failed to submit code");
    } finally {
      setSubmitting(false);
    }
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty?.toLowerCase()) {
      case "easy": return "text-emerald-500 bg-emerald-500/10";
      case "medium": return "text-yellow-500 bg-yellow-500/10";
      case "hard": return "text-red-500 bg-red-500/10";
      default: return "text-slate-500 bg-slate-500/10";
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-400 p-8 bg-[#0f111a]">
        <Loader2 className="w-8 h-8 animate-spin mb-4" />
        <p>Loading problem workspace...</p>
      </div>
    );
  }

  if (error || !question) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-red-500 p-8 bg-[#0f111a]">
        <AlertCircle className="w-8 h-8 mb-4" />
        <p>{error || "Problem not found"}</p>
        <button 
          onClick={() => router.back()}
          className="mt-4 px-4 py-2 bg-slate-800 text-slate-200 rounded-md hover:bg-slate-700"
        >
          Go Back
        </button>
      </div>
    );
  }

  const promptContent = question.content_rich_text || question.prompt || "No description provided.";

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-[#0f111a] text-slate-300 font-sans">
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#1e2029] border-b border-slate-800">
        <div className="flex items-center gap-3">
          <button 
            onClick={() => router.back()}
            className="p-1.5 hover:bg-slate-800 rounded-md text-slate-400 transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-3">
            <h1 className="text-sm font-semibold text-slate-200">{question.title}</h1>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <select 
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="text-xs bg-slate-800 border border-slate-700 text-slate-300 rounded px-2 py-1.5 outline-none focus:border-blue-500"
          >
            <option value="javascript">JavaScript</option>
            <option value="python">Python</option>
            <option value="java">Java</option>
            <option value="cpp">C++</option>
          </select>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="inline-flex items-center gap-1.5 bg-emerald-600/90 text-white px-3 py-1.5 rounded text-xs font-semibold hover:bg-emerald-500 transition-colors disabled:opacity-50"
          >
            {submitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
            Submit Code
          </button>
        </div>
      </div>

      {/* Main content - LeetCode Style Split */}
      <div className="flex flex-1 overflow-hidden p-2 gap-2">
        
        {/* LEFT PANE - Problem Description */}
        <div className="w-1/2 flex flex-col bg-[#1e2029] rounded-lg border border-slate-800 overflow-hidden">
          {/* Tabs */}
          <div className="flex items-center bg-[#282a36] border-b border-slate-800 px-2 pt-2">
            <button 
              onClick={() => setLeftTab("description")}
              className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-colors ${leftTab === 'description' ? 'bg-[#1e2029] text-white' : 'text-slate-400 hover:text-slate-200'}`}
            >
              Description
            </button>
            <button 
              onClick={() => setLeftTab("submissions")}
              className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-colors ${leftTab === 'submissions' ? 'bg-[#1e2029] text-white' : 'text-slate-400 hover:text-slate-200'}`}
            >
              Submissions
            </button>
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto p-5">
            {leftTab === "description" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-bold text-white">{question.title}</h2>
                </div>
                <div className={`inline-block px-2 py-1 rounded text-xs font-medium mb-4 ${getDifficultyColor(question.difficulty)}`}>
                  {question.difficulty}
                </div>
                
                <div className="prose prose-invert max-w-none text-slate-300 text-sm leading-relaxed whitespace-pre-wrap">
                  {promptContent}
                </div>
              </div>
            )}
            
            {leftTab === "submissions" && (
              <div className="text-center text-slate-500 mt-10 text-sm">
                <Terminal className="w-8 h-8 mx-auto mb-3 opacity-50" />
                No previous submissions.
              </div>
            )}
          </div>
        </div>

        {/* RIGHT PANE - Editor & Output */}
        <div className="w-1/2 flex flex-col gap-2 overflow-hidden">
          
          {/* Code Editor (Top) */}
          <div className={`flex flex-col bg-[#1e2029] rounded-lg border border-slate-800 overflow-hidden transition-all duration-300 ${results ? 'h-3/5' : 'h-full'}`}>
            <div className="flex items-center bg-[#282a36] border-b border-slate-800 px-4 py-2">
              <span className="text-xs font-mono text-slate-400 flex items-center gap-2">
                <Terminal className="w-3.5 h-3.5" /> Code
              </span>
            </div>
            <div className="flex-1 relative">
              <Editor
                height="100%"
                defaultLanguage="javascript"
                language={language}
                theme="vs-dark"
                value={code}
                onChange={(value) => setCode(value || "")}
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                  padding: { top: 16 },
                  scrollBeyondLastLine: false,
                  smoothScrolling: true,
                  cursorBlinking: "smooth",
                }}
              />
            </div>
          </div>

          {/* Test Cases / Output Console (Bottom) */}
          {results && (
            <div className="flex flex-col h-2/5 bg-[#1e2029] rounded-lg border border-slate-800 overflow-hidden">
              {/* Output Tabs */}
              <div className="flex items-center bg-[#282a36] border-b border-slate-800 px-2 pt-2">
                <button 
                  onClick={() => setRightBottomTab("testcases")}
                  className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-colors flex items-center gap-1.5 ${rightBottomTab === 'testcases' ? 'bg-[#1e2029] text-white' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  <Terminal className="w-3.5 h-3.5" /> Test Result
                </button>
              </div>

              {/* Output Content */}
              <div className="flex-1 overflow-y-auto p-4 font-mono text-sm bg-[#1e2029]">
                <div className={`flex items-center gap-2 font-bold mb-4 text-lg ${results.overall_passed ? 'text-emerald-400' : 'text-red-400'}`}>
                  {results.overall_passed ? <CheckCircle2 className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
                  {results.overall_passed ? 'Accepted' : 'Wrong Answer'}
                </div>
                
                <div className="flex flex-wrap gap-2 mb-4">
                  {results.test_results?.map((tc: any, i: number) => (
                    <div key={i} className={`px-3 py-1.5 rounded-md text-xs font-semibold border ${tc.passed ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>
                      Case {i + 1}
                    </div>
                  ))}
                </div>

                <div className="space-y-4">
                  {results.test_results?.map((tc: any, i: number) => (
                    <div key={i} className="bg-[#282a36] rounded-lg border border-slate-700/50 p-4">
                      <div className="font-semibold mb-3 flex items-center gap-2 text-slate-300">
                        {tc.passed ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <XCircle className="w-4 h-4 text-red-400" />}
                        Test Case {i + 1}
                        <span className="text-slate-500 font-normal ml-auto text-xs">{tc.wall_time_ms} ms</span>
                      </div>
                      
                      <div className="space-y-3">
                        <div>
                          <div className="text-slate-500 text-xs mb-1 uppercase tracking-wider">Input</div>
                          <div className="bg-[#1e2029] p-2 rounded text-slate-300 whitespace-pre-wrap border border-slate-800">{tc.input || "No input"}</div>
                        </div>
                        <div>
                          <div className="text-slate-500 text-xs mb-1 uppercase tracking-wider">Expected Output</div>
                          <div className="bg-[#1e2029] p-2 rounded text-slate-300 whitespace-pre-wrap border border-slate-800">{tc.expected}</div>
                        </div>
                        <div>
                          <div className="text-slate-500 text-xs mb-1 uppercase tracking-wider">Your Output</div>
                          <div className={`bg-[#1e2029] p-2 rounded whitespace-pre-wrap border ${tc.passed ? 'border-slate-800 text-slate-300' : 'border-red-500/30 text-red-300'}`}>
                            {tc.actual || <span className="italic opacity-30">Empty</span>}
                          </div>
                        </div>
                        
                        {tc.error && (
                          <div>
                            <div className="text-red-400/70 text-xs mb-1 uppercase tracking-wider">Runtime Error / Stderr</div>
                            <div className="bg-red-500/5 p-2 rounded text-red-400 whitespace-pre-wrap border border-red-500/20">{tc.error}</div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
