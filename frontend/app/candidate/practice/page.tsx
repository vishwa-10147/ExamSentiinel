"use client";

import React, { useState } from "react";
import Sidebar from "@/components/Sidebar";
import Editor from "@monaco-editor/react";
import { Play, RotateCcw, Terminal, Code2, CheckCircle2, ChevronDown } from "lucide-react";

const DEFAULT_CODES: Record<string, string> = {
  python: `# Welcome to ExamSentinel Practice Playground
# Write your Python code here and hit 'Run Code' to test it.

def find_max(arr):
    if not arr:
        return None
    return max(arr)

numbers = [12, 45, 7, 89, 34, 102, 5]
print(f"The array is: {numbers}")
print(f"The maximum value is: {find_max(numbers)}")
`,
  javascript: `// Welcome to ExamSentinel Practice Playground
// Write your JavaScript code here and hit 'Run Code' to test it.

function findMax(arr) {
  let max = arr[0];
  for (let i = 1; i < arr.length; i++) {
    if (arr[i] > max) max = arr[i];
  }
  return max;
}

const numbers = [12, 45, 7, 89, 34, 102, 5];
console.log("The array is:", numbers);
console.log("The maximum value is:", findMax(numbers));
`,
  java: `// Welcome to ExamSentinel Practice Playground
// Write your Java code here and hit 'Run Code' to test it.

public class Main {
    public static void main(String[] args) {
        int[] numbers = {12, 45, 7, 89, 34, 102, 5};
        System.out.print("The array is: ");
        for (int n : numbers) System.out.print(n + " ");
        System.out.println();
        
        int max = numbers[0];
        for (int num : numbers) {
            if (num > max) max = num;
        }
        System.out.println("The maximum value is: " + max);
    }
}
`,
  c: `// Welcome to ExamSentinel Practice Playground
// Write your C code here and hit 'Run Code' to test it.

#include <stdio.h>

int main() {
    int numbers[] = {12, 45, 7, 89, 34, 102, 5};
    int size = sizeof(numbers) / sizeof(numbers[0]);
    
    printf("The array is: ");
    for (int i = 0; i < size; i++) {
        printf("%d ", numbers[i]);
    }
    printf("\\n");
    
    int max = numbers[0];
    for (int i = 1; i < size; i++) {
        if (numbers[i] > max) max = numbers[i];
    }
    
    printf("The maximum value is: %d\\n", max);
    return 0;
}
`,
  cpp: `// Welcome to ExamSentinel Practice Playground
// Write your C++ code here and hit 'Run Code' to test it.

#include <iostream>
#include <vector>
#include <algorithm>

int main() {
    std::vector<int> numbers = {12, 45, 7, 89, 34, 102, 5};
    
    std::cout << "The array is: ";
    for (int n : numbers) {
        std::cout << n << " ";
    }
    std::cout << std::endl;
    
    int max = *std::max_element(numbers.begin(), numbers.end());
    std::cout << "The maximum value is: " << max << std::endl;
    return 0;
}
`
};

const PISTON_RUNTIMES: Record<string, { lang: string; version: string }> = {
  javascript: { lang: "javascript", version: "18.15.0" },
  python: { lang: "python", version: "3.10.0" },
  java: { lang: "java", version: "15.0.2" },
  c: { lang: "c", version: "10.2.0" },
  cpp: { lang: "c++", version: "10.2.0" },
};

export default function PracticeCodingPage() {
  const [language, setLanguage] = useState("python");
  const [code, setCode] = useState(DEFAULT_CODES["python"]);
  const [output, setOutput] = useState<string[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [activeTab, setActiveTab] = useState("console");

  const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLang = e.target.value;
    setLanguage(newLang);
    setCode(DEFAULT_CODES[newLang]);
    setOutput([]);
  };

  const runCode = async () => {
    setIsRunning(true);
    setOutput(["Dispatching to execution cluster..."]);
    setActiveTab("console");
    
    try {
      const res = await fetch("http://localhost:8000/api/sandbox/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          language: language,
          code: code
        }),
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }

      const data = await res.json();
      
      let outLines: string[] = [];
      
      if (data.stderr) {
         outLines.push("=== Error ===");
         outLines = outLines.concat(data.stderr.split('\n'));
      }
      
      if (data.stdout) {
         outLines = outLines.concat(data.stdout.split('\n'));
      }

      if (outLines.length === 0 || (outLines.length === 1 && outLines[0] === "")) {
        outLines = ["(Program exited successfully with no output)"];
      }

      setOutput(outLines.filter((line: string) => line.trim() !== ""));
    } catch (err: any) {
      setOutput([`Execution failed: ${err.message}`, "Could not reach the execution server."]);
    } finally {
      setIsRunning(false);
    }
  };

  const resetCode = () => {
    setCode(DEFAULT_CODES[language]);
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
              Code Sandbox
            </h1>
            <p className="text-slate-500 text-sm mt-1">Hone your algorithms in a secure, multi-language execution environment.</p>
          </div>
          <div className="flex items-center gap-3">
            
            <div className="relative">
              <select
                value={language}
                onChange={handleLanguageChange}
                disabled={isRunning}
                className="appearance-none bg-slate-100 border border-slate-200 text-slate-800 text-sm font-semibold rounded-lg pl-4 pr-10 py-2 hover:bg-slate-200 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              >
                <option value="python">Python 3</option>
                <option value="java">Java 15</option>
                <option value="c">C (GCC)</option>
                <option value="cpp">C++ (GCC)</option>
                <option value="javascript">JavaScript (Node)</option>
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500 pointer-events-none" />
            </div>

            <button
              onClick={resetCode}
              disabled={isRunning}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 transition-colors"
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
                <Code2 className="h-4 w-4 text-blue-400" /> main.{language === 'python' ? 'py' : language === 'javascript' ? 'js' : language === 'c' ? 'c' : language === 'cpp' ? 'cpp' : 'java'}
              </span>
              <span className="text-xs text-slate-500 font-mono">
                {language === 'python' && "Python (3.10.0)"}
                {language === 'java' && "Java (15.0.2)"}
                {language === 'c' && "C (GCC 10.2.0)"}
                {language === 'cpp' && "C++ (GCC 10.2.0)"}
                {language === 'javascript' && "JavaScript (Node 18.15.0)"}
              </span>
            </div>
            <div className="flex-1 relative">
              <Editor
                height="100%"
                language={language}
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
                    output.map((line, idx) => {
                      const isError = line.includes('Error') || line.includes('Exception');
                      return (
                        <div key={idx} className={`${isError ? 'text-red-400' : 'text-emerald-400'}`}>
                          <span className="text-slate-600 mr-2">›</span>
                          {line}
                        </div>
                      );
                    })
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
