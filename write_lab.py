import os

filepath = 'frontend/app/exam/[id]/lab/page.tsx'

content = """\"use client\";

import React, { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import FaceTracker from "@/components/FaceTracker";
import Editor from "@monaco-editor/react";
import { Play, Terminal, Code2, AlertTriangle, CheckCircle } from "lucide-react";
import { apiClient } from "@/services/apiClient";
import toast from "react-hot-toast";

export default function LabExamPage() {
  const params = useParams();
  const examId = params.id as string;
  const router = useRouter();
  const { isAuthenticated, user, isLoading: authLoading } = useAuth();
  
  const [code, setCode] = useState("def solve():\\n    # Write your solution here\\n    pass");
  const [language, setLanguage] = useState("python");
  const [output, setOutput] = useState<string[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [isProctoringActive, setIsProctoringActive] = useState(true);
  
  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push("/auth/login");
  }, [authLoading, isAuthenticated, router]);

  const handleRunCode = async () => {
    setIsRunning(true);
    setOutput(["Dispatching to secure execution cluster..."]);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/sandbox/execute, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": Bearer  },
        body: JSON.stringify({ language, source_code: code, stdin: "", time_limit_sec: 5.0, memory_limit_mb: 256 })
      });
      const data = await res.json();
      if (res.ok) {
        setOutput(data.stdout ? data.stdout.split("\\n") : []);
        if (data.stderr) {
          setOutput(prev => [...prev, ...data.stderr.split("\\n")]);
        }
      } else {
        setOutput(["Execution failed.", JSON.stringify(data)]);
      }
    } catch (err) {
      setOutput(["Connection error. Please try again."]);
    } finally {
      setIsRunning(false);
    }
  };

  const handleViolation = async (eventType: string, details: any) => {
    toast.error(Proctoring Alert: );
  };

  if (authLoading || !user) return <div className="p-8 text-center">Loading...</div>;

  return (
    <div className="flex flex-col h-screen bg-slate-900 text-white overflow-hidden">
      {/* Top Navbar */}
      <header className="flex items-center justify-between px-6 py-3 bg-slate-800 border-b border-slate-700">
        <div className="flex items-center gap-4">
          <Code2 className="h-6 w-6 text-blue-400" />
          <h1 className="text-lg font-bold">ExamSentinel Lab Environment</h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-emerald-400 text-sm font-medium bg-emerald-400/10 px-3 py-1.5 rounded-full">
            <CheckCircle className="h-4 w-4" /> Proctoring Active
          </div>
          <button className="bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded-md font-semibold text-sm transition-colors">
            Submit Exam
          </button>
        </div>
      </header>

      {/* Main Split Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Pane: Question & Proctoring */}
        <div className="w-1/3 flex flex-col border-r border-slate-700 bg-slate-800/50">
          <div className="flex-1 p-6 overflow-y-auto">
            <h2 className="text-xl font-bold mb-4">Question 1: Algorithm Design</h2>
            <div className="prose prose-invert">
              <p>Write a function that calculates the maximum value in an array.</p>
              <p><strong>Input:</strong> An array of integers.</p>
              <p><strong>Output:</strong> The maximum integer.</p>
            </div>
          </div>
          {/* Proctoring Feed */}
          <div className="p-4 border-t border-slate-700 bg-black">
            <h3 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">Live Proctoring Feed</h3>
            <div className="aspect-video bg-slate-900 rounded-lg overflow-hidden border border-slate-700 relative">
              <FaceTracker onEventDetected={handleViolation} enabled={isProctoringActive} />
            </div>
          </div>
        </div>

        {/* Right Pane: Code Editor & Terminal */}
        <div className="w-2/3 flex flex-col">
          <div className="flex items-center justify-between px-4 py-2 bg-slate-800 border-b border-slate-700">
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="bg-slate-900 border border-slate-700 text-sm rounded-md px-3 py-1.5 outline-none focus:border-blue-500"
            >
              <option value="python">Python 3</option>
              <option value="javascript">Node.js</option>
              <option value="cpp">C++</option>
              <option value="java">Java</option>
            </select>
            <button 
              onClick={handleRunCode}
              disabled={isRunning}
              className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-600/50 px-4 py-1.5 rounded-md text-sm font-semibold transition-colors"
            >
              <Play className="h-4 w-4" /> {isRunning ? "Running..." : "Run Code"}
            </button>
          </div>
          
          <div className="flex-1">
            <Editor
              height="100%"
              language={language === "cpp" ? "cpp" : language}
              theme="vs-dark"
              value={code}
              onChange={(val) => setCode(val || "")}
              options={{ minimap: { enabled: false }, fontSize: 14 }}
            />
          </div>

          {/* Terminal Output */}
          <div className="h-64 border-t border-slate-700 bg-[#1e1e1e] flex flex-col">
            <div className="flex items-center gap-2 px-4 py-2 bg-slate-800 border-b border-slate-700">
              <Terminal className="h-4 w-4 text-slate-400" />
              <span className="text-sm font-semibold text-slate-300">Console Output</span>
            </div>
            <div className="flex-1 p-4 overflow-y-auto font-mono text-sm">
              {output.length === 0 ? (
                <span className="text-slate-500">Output will appear here...</span>
              ) : (
                output.map((line, i) => (
                  <div key={i} className="text-slate-300">{line}</div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
"""

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Created lab page!")
