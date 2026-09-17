"use client";

import React, { useState } from "react";
import Sidebar from "@/components/Sidebar";
import Editor from "@monaco-editor/react";
import { Play, RotateCcw, Terminal, Code2, CheckCircle2 } from "lucide-react";

export default function PracticeCodingPage() {
  const defaultCode = `// Welcome to ExamSentinel Practice Playground
// Write your JavaScript code here and hit 'Run Code' to test it.

function findMax(arr) {
  let max = arr[0];
  for (let i = 1; i < arr.length; i++) {
    if (arr[i] > max) {
      max = arr[i];
    }
  }
  return max;
}

const numbers = [12, 45, 7, 89, 34, 102, 5];
console.log("The array is:", numbers);
console.log("The maximum value is:", findMax(numbers));`;

  const [code, setCode] = useState(defaultCode);
  const [output, setOutput] = useState<string[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [activeTab, setActiveTab] = useState("console");

  const runCode = () => {
    setIsRunning(true);
    setOutput(["Running in local sandbox..."]);
    
    setTimeout(() => {
      let logs: string[] = [];
      const originalConsoleLog = console.log;
      console.log = (...args) => {
        logs.push(args.map(a => (typeof a === 'object' ? JSON.stringify(a) : String(a))).join(' '));
      };

      try {
        // eslint-disable-next-line no-new-func
        const fn = new Function(code);
        fn();
      } catch (err: any) {
        logs.push(`Error: ${err.message}`);
      } finally {
        console.log = originalConsoleLog;
        setOutput(logs.length > 0 ? logs : ["(No output returned)"]);
        setIsRunning(false);
      }
    }, 600);
  };

  const resetCode = () => {
    setCode(defaultCode);
    setOutput([]);
  };

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        
        {/* Header */}
        <div className="bg-white border-b border-slate-200 px-8 py-4 flex items-center justify-between shrink-0">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
              <Code2 className="h-6 w-6 text-blue-600" />
              Coding Practice Sandbox
            </h1>
            <p className="text-slate-500 text-sm mt-1">Hone your algorithms in a safe, isolated environment before taking an exam.</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={resetCode}
              disabled={isRunning}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50"
            >
              <RotateCcw className="h-4 w-4" /> Reset
            </button>
            <button
              onClick={runCode}
              disabled={isRunning}
              className="flex items-center gap-2 px-5 py-2 text-sm font-bold text-white bg-emerald-600 rounded-lg hover:bg-emerald-500 disabled:opacity-70 transition-colors shadow-sm"
            >
              {isRunning ? <span className="animate-pulse flex items-center gap-2"><Play className="h-4 w-4 opacity-50" /> Running...</span> : <><Play className="h-4 w-4" /> Run Code</>}
            </button>
          </div>
        </div>

        {/* Editor Split Pane */}
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden bg-slate-100 p-6 gap-6">
          
          {/* Editor Side */}
          <div className="flex-1 flex flex-col bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="bg-slate-900 px-4 py-2 flex items-center justify-between border-b border-slate-800">
              <span className="text-slate-300 text-xs font-semibold uppercase tracking-wider flex items-center gap-2">
                <Code2 className="h-4 w-4 text-blue-400" /> main.js
              </span>
              <span className="text-xs text-slate-500 font-mono">JavaScript (Node v20)</span>
            </div>
            <div className="flex-1 relative">
              <Editor
                height="100%"
                language="javascript"
                theme="vs-dark"
                value={code}
                onChange={(val) => setCode(val || "")}
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                  fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                  padding: { top: 16 },
                  scrollBeyondLastLine: false,
                  smoothScrolling: true,
                }}
              />
            </div>
          </div>

          {/* Terminal/Output Side */}
          <div className="w-full md:w-1/3 flex flex-col bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="flex border-b border-slate-200 bg-slate-50">
              <button 
                onClick={() => setActiveTab('console')}
                className={`flex-1 py-3 text-sm font-semibold flex items-center justify-center gap-2 transition-colors ${activeTab === 'console' ? 'text-blue-700 bg-white border-b-2 border-blue-600' : 'text-slate-500 hover:text-slate-700'}`}
              >
                <Terminal className="h-4 w-4" /> Output Console
              </button>
              <button 
                onClick={() => setActiveTab('testcases')}
                className={`flex-1 py-3 text-sm font-semibold flex items-center justify-center gap-2 transition-colors ${activeTab === 'testcases' ? 'text-blue-700 bg-white border-b-2 border-blue-600' : 'text-slate-500 hover:text-slate-700'}`}
              >
                <CheckCircle2 className="h-4 w-4" /> Test Cases
              </button>
            </div>
            
            <div className="flex-1 bg-[#1e1e1e] p-4 overflow-y-auto font-mono text-sm">
              {activeTab === 'console' ? (
                <div className="space-y-1">
                  {output.length === 0 ? (
                    <div className="text-slate-500 italic mt-2">Ready. Click 'Run Code' to execute.</div>
                  ) : (
                    output.map((line, idx) => (
                      <div key={idx} className={`${line.startsWith('Error:') ? 'text-red-400' : 'text-emerald-400'}`}>
                        <span className="text-slate-600 mr-2">›</span>
                        {line}
                      </div>
                    ))
                  )}
                </div>
              ) : (
                <div className="text-slate-400 p-4 text-center mt-10">
                  <CheckCircle2 className="h-8 w-8 text-slate-600 mx-auto mb-3" />
                  <p>No formal test cases assigned.</p>
                  <p className="text-xs mt-1">This is a free-play sandbox.</p>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
