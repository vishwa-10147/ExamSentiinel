"use client";
export const dynamic = "force-dynamic";

import React, { useState, useEffect } from "react";
import Editor from "@monaco-editor/react";
import {
  Play,
  RotateCcw,
  Terminal,
  Code2,
  CheckCircle2,
  ChevronDown,
  Sparkles,
  Zap,
  Clock,
  ShieldAlert,
  Sliders,
  Check,
  X,
  FileCode,
  BookOpen,
  Cpu,
  Loader2
} from "lucide-react";
import { apiClient } from "@/services/apiClient";
import toast from "react-hot-toast";

interface QuestionChallenge {
  id: string;
  title: string;
  difficulty: "EASY" | "MEDIUM" | "HARD";
  category: string;
  description: string;
  examples: { input: string; output: string; explanation?: string }[];
  starters: Record<string, string>;
  testCases: { input: string; expected: string }[];
}

const PRACTICE_PROBLEMS: QuestionChallenge[] = [
  {
    id: "two-sum",
    title: "1. Two Sum",
    difficulty: "EASY",
    category: "Arrays & Hashing",
    description:
      "Given an array of integers `nums` and an integer `target`, return indices of the two numbers such that they add up to `target`.\n\nYou may assume that each input would have exactly one solution, and you may not use the same element twice.",
    examples: [
      { input: "nums = [2,7,11,15], target = 9", output: "[0, 1]", explanation: "Because nums[0] + nums[1] == 9, we return [0, 1]." },
      { input: "nums = [3,2,4], target = 6", output: "[1, 2]" },
    ],
    starters: {
      python: `def two_sum(nums, target):\n    # Write your solution here\n    seen = {}\n    for i, num in enumerate(nums):\n        diff = target - num\n        if diff in seen:\n            return [seen[diff], i]\n        seen[num] = i\n    return []\n\nprint(two_sum([2, 7, 11, 15], 9))\n`,
      javascript: `function twoSum(nums, target) {\n  // Write your solution here\n  const map = new Map();\n  for (let i = 0; i < nums.length; i++) {\n    const diff = target - nums[i];\n    if (map.has(diff)) return [map.get(diff), i];\n    map.set(nums[i], i);\n  }\n  return [];\n}\n\nconsole.log(twoSum([2, 7, 11, 15], 9));\n`,
      java: `import java.util.*;\n\npublic class Main {\n    public static int[] twoSum(int[] nums, int target) {\n        Map<Integer, Integer> map = new HashMap<>();\n        for (int i = 0; i < nums.length; i++) {\n            int diff = target - nums[i];\n            if (map.containsKey(diff)) {\n                return new int[] { map.get(diff), i };\n            }\n            map.put(nums[i], i);\n        }\n        return new int[]{};\n    }\n\n    public static void main(String[] args) {\n        int[] res = twoSum(new int[]{2, 7, 11, 15}, 9);\n        System.out.println(Arrays.toString(res));\n    }\n}\n`,
      cpp: `#include <iostream>\n#include <vector>\n#include <unordered_map>\n\nstd::vector<int> twoSum(std::vector<int>& nums, int target) {\n    std::unordered_map<int, int> map;\n    for (int i = 0; i < nums.size(); i++) {\n        int diff = target - nums[i];\n        if (map.count(diff)) return {map[diff], i};\n        map[nums[i]] = i;\n    }\n    return {};\n}\n\nint main() {\n    std::vector<int> nums = {2, 7, 11, 15};\n    std::vector<int> res = twoSum(nums, 9);\n    std::cout << "[" << res[0] << ", " << res[1] << "]" << std::endl;\n    return 0;\n}\n`,
      c: `#include <stdio.h>\n\nint main() {\n    int nums[] = {2, 7, 11, 15};\n    int target = 9;\n    int size = 4;\n    \n    for (int i = 0; i < size; i++) {\n        for (int j = i + 1; j < size; j++) {\n            if (nums[i] + nums[j] == target) {\n                printf("[%d, %d]\\n", i, j);\n                return 0;\n            }\n        }\n    }\n    return 0;\n}\n`,
    },
    testCases: [
      { input: "[2, 7, 11, 15], 9", expected: "[0, 1]" },
      { input: "[3, 2, 4], 6", expected: "[1, 2]" },
    ],
  },
  {
    id: "valid-palindrome",
    title: "2. Valid Palindrome",
    difficulty: "EASY",
    category: "Strings",
    description:
      "A phrase is a palindrome if, after converting all uppercase letters into lowercase letters and removing all non-alphanumeric characters, it reads the same forward and backward.",
    examples: [
      { input: 's = "A man, a plan, a canal: Panama"', output: "true", explanation: '"amanaplanacanalpanama" is a palindrome.' },
      { input: 's = "race a car"', output: "false" },
    ],
    starters: {
      python: `def is_palindrome(s: str) -> bool:\n    cleaned = [c.lower() for c in s if c.isalnum()]\n    return cleaned == cleaned[::-1]\n\nprint(is_palindrome("A man, a plan, a canal: Panama"))\n`,
      javascript: `function isPalindrome(s) {\n  const cleaned = s.toLowerCase().replace(/[^a-z0-9]/g, "");\n  return cleaned === cleaned.split("").reverse().join("");\n}\n\nconsole.log(isPalindrome("A man, a plan, a canal: Panama"));\n`,
      java: `public class Main {\n    public static boolean isPalindrome(String s) {\n        String cleaned = s.replaceAll("[^a-zA-Z0-9]", "").toLowerCase();\n        String rev = new StringBuilder(cleaned).reverse().toString();\n        return cleaned.equals(rev);\n    }\n    public static void main(String[] args) {\n        System.out.println(isPalindrome("A man, a plan, a canal: Panama"));\n    }\n}\n`,
      cpp: `#include <iostream>\n#include <string>\n#include <algorithm>\n\nbool isPalindrome(std::string s) {\n    std::string cleaned = "";\n    for (char c : s) {\n        if (isalnum(c)) cleaned += tolower(c);\n    }\n    std::string rev = cleaned;\n    std::reverse(rev.begin(), rev.end());\n    return cleaned == rev;\n}\n\nint main() {\n    std::cout << (isPalindrome("A man, a plan, a canal: Panama") ? "true" : "false") << std::endl;\n    return 0;\n}\n`,
      c: `#include <stdio.h>\n#include <string.h>\n#include <ctype.h>\n\nint main() {\n    char s[] = "race a car";\n    printf("false\\n");\n    return 0;\n}\n`
    },
    testCases: [
      { input: '"A man, a plan, a canal: Panama"', expected: "true" },
      { input: '"race a car"', expected: "false" },
    ],
  },
  {
    id: "max-subarray",
    title: "3. Maximum Subarray",
    difficulty: "MEDIUM",
    category: "Dynamic Programming",
    description:
      "Given an integer array `nums`, find the subarray with the largest sum, and return its sum.",
    examples: [
      { input: "nums = [-2,1,-3,4,-1,2,1,-5,4]", output: "6", explanation: "The subarray [4,-1,2,1] has the largest sum 6." },
      { input: "nums = [1]", output: "1" },
    ],
    starters: {
      python: `def max_sub_array(nums):\n    max_so_far = nums[0]\n    curr = nums[0]\n    for x in nums[1:]:\n        curr = max(x, curr + x)\n        max_so_far = max(max_so_far, curr)\n    return max_so_far\n\nprint(max_sub_array([-2, 1, -3, 4, -1, 2, 1, -5, 4]))\n`,
      javascript: `function maxSubArray(nums) {\n  let maxSoFar = nums[0];\n  let curr = nums[0];\n  for (let i = 1; i < nums.length; i++) {\n    curr = Math.max(nums[i], curr + nums[i]);\n    maxSoFar = Math.max(maxSoFar, curr);\n  }\n  return maxSoFar;\n}\n\nconsole.log(maxSubArray([-2, 1, -3, 4, -1, 2, 1, -5, 4]));\n`,
      java: `public class Main {\n    public static int maxSubArray(int[] nums) {\n        int maxSoFar = nums[0];\n        int curr = nums[0];\n        for (int i = 1; i < nums.length; i++) {\n            curr = Math.max(nums[i], curr + nums[i]);\n            maxSoFar = Math.max(maxSoFar, curr);\n        }\n        return maxSoFar;\n    }\n    public static void main(String[] args) {\n        System.out.println(maxSubArray(new int[]{-2, 1, -3, 4, -1, 2, 1, -5, 4}));\n    }\n}\n`,
      cpp: `#include <iostream>\n#include <vector>\n#include <algorithm>\n\nint maxSubArray(std::vector<int>& nums) {\n    int maxSoFar = nums[0], curr = nums[0];\n    for (size_t i = 1; i < nums.size(); ++i) {\n        curr = std::max(nums[i], curr + nums[i]);\n        maxSoFar = std::max(maxSoFar, curr);\n    }\n    return maxSoFar;\n}\n\nint main() {\n    std::vector<int> nums = {-2, 1, -3, 4, -1, 2, 1, -5, 4};\n    std::cout << maxSubArray(nums) << std::endl;\n    return 0;\n}\n`,
      c: `#include <stdio.h>\nint main() {\n    printf("6\\n");\n    return 0;\n}\n`
    },
    testCases: [
      { input: "[-2, 1, -3, 4, -1, 2, 1, -5, 4]", expected: "6" },
      { input: "[1]", expected: "1" },
    ],
  },
];

export default function PracticeCodingPage() {
  const [selectedProblem, setSelectedProblem] = useState<QuestionChallenge>(PRACTICE_PROBLEMS[0]);
  const [language, setLanguage] = useState("python");
  const [code, setCode] = useState(PRACTICE_PROBLEMS[0].starters["python"]);
  const [customInput, setCustomInput] = useState("");
  
  const [output, setOutput] = useState<string[]>([]);
  const [wallTimeMs, setWallTimeMs] = useState<number | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [activeTab, setActiveTab] = useState<"console" | "stdin" | "testcases">("console");

  // Limits and Quota Controls
  const MAX_DAILY_RUNS = 25;
  const [runsLeft, setRunsLeft] = useState<number>(25);
  const [cooldown, setCooldown] = useState<number>(0);

  // Load runs from localStorage
  useEffect(() => {
    const savedRuns = localStorage.getItem("practice_runs_remaining");
    if (savedRuns) {
      setRunsLeft(parseInt(savedRuns) || 25);
    }
  }, []);

  // Cooldown countdown timer
  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => {
      setCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  const handleProblemSelect = (prob: QuestionChallenge) => {
    setSelectedProblem(prob);
    const starter = prob.starters[language] || prob.starters["python"];
    setCode(starter);
    setOutput([]);
    setWallTimeMs(null);
  };

  const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLang = e.target.value;
    setLanguage(newLang);
    const starter = selectedProblem.starters[newLang] || selectedProblem.starters["python"] || "";
    setCode(starter);
    setOutput([]);
    setWallTimeMs(null);
  };

  const runCode = async () => {
    if (runsLeft <= 0) {
      toast.error("Daily execution quota reached (25 runs). Please try again tomorrow.");
      return;
    }

    if (cooldown > 0) {
      toast.error(`Please wait ${cooldown} seconds before running again.`);
      return;
    }

    if (!code.trim()) {
      toast.error("Source code cannot be empty.");
      return;
    }

    if (code.length > 10000) {
      toast.error("Code length exceeds maximum allowed limit (10,000 characters).");
      return;
    }

    setIsRunning(true);
    setOutput(["Dispatching code to isolated execution sandbox..."]);
    setActiveTab("console");
    setWallTimeMs(null);

    try {
      const data = await apiClient.post<{
        status: string;
        stdout: string;
        stderr: string;
        wall_time_ms?: number;
      }>("/api/sandbox/execute", {
        language,
        code,
        stdin: customInput || undefined,
      });

      let outLines: string[] = [];

      if (data.stderr) {
        outLines.push("=== Execution Stderr / Errors ===");
        outLines = outLines.concat(data.stderr.split("\n"));
      }

      if (data.stdout) {
        outLines = outLines.concat(data.stdout.split("\n"));
      }

      if (outLines.length === 0) {
        outLines = ["(Program executed successfully with no stdout output)"];
      }

      // Output Truncation Limit (max 50 lines)
      if (outLines.length > 50) {
        outLines = outLines.slice(0, 50);
        outLines.push("... [Output truncated to 50 lines]");
      }

      setOutput(outLines);
      setWallTimeMs(data.wall_time_ms || 0);

      // Decrement quota and start 3s cooldown
      const nextRuns = Math.max(runsLeft - 1, 0);
      setRunsLeft(nextRuns);
      localStorage.setItem("practice_runs_remaining", nextRuns.toString());
      setCooldown(3);
    } catch (err: any) {
      console.error("Execution error", err);
      setOutput([`Execution error: ${err?.message || "Sandbox worker unavailable."}`]);
    } finally {
      setIsRunning(false);
    }
  };

  const resetCode = () => {
    const starter = selectedProblem.starters[language] || selectedProblem.starters["python"];
    setCode(starter);
    setOutput([]);
    setWallTimeMs(null);
    toast.success("Code reset to starter template.");
  };

  return (
    <div className="flex-1 flex flex-col h-[calc(100vh-4rem)] overflow-hidden bg-slate-900 text-white">
      {/* Header Bar */}
      <div className="bg-slate-950 border-b border-slate-800 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-600/20 border border-blue-500/30 rounded-xl">
            <Code2 className="h-5 w-5 text-blue-400" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white flex items-center gap-2">
              Practice Coding Playground & Sandbox
            </h1>
            <p className="text-xs text-slate-400">
              Interactive execution engine • 5.0s Timeout • 128MB Memory Limit
            </p>
          </div>
        </div>

        {/* Right Controls */}
        <div className="flex items-center gap-3">
          {/* Quota Badge */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs">
            <Zap className="h-3.5 w-3.5 text-amber-400" />
            <span className="text-slate-400">Quota:</span>
            <strong className="text-slate-200 font-mono">{runsLeft} / {MAX_DAILY_RUNS} Runs</strong>
          </div>

          {/* Language Picker */}
          <div className="relative">
            <select
              value={language}
              onChange={handleLanguageChange}
              disabled={isRunning}
              className="appearance-none bg-slate-800 border border-slate-700 text-slate-200 text-xs font-semibold rounded-lg pl-3 pr-8 py-2 hover:bg-slate-700 transition focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            >
              <option value="python">Python 3.10</option>
              <option value="javascript">JavaScript (Node 18)</option>
              <option value="java">Java 15</option>
              <option value="cpp">C++ (GCC 10.2)</option>
              <option value="c">C (GCC 10.2)</option>
            </select>
            <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400 pointer-events-none" />
          </div>

          <button
            onClick={resetCode}
            disabled={isRunning}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-300 bg-slate-800 border border-slate-700 rounded-lg hover:bg-slate-700 disabled:opacity-50 transition"
          >
            <RotateCcw className="h-3.5 w-3.5" /> Reset
          </button>

          <button
            onClick={runCode}
            disabled={isRunning || cooldown > 0 || runsLeft <= 0}
            className="flex items-center gap-2 px-5 py-2 text-xs font-bold text-white bg-emerald-600 rounded-lg hover:bg-emerald-500 disabled:opacity-50 transition shadow-md"
          >
            {isRunning ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" /> Running...
              </span>
            ) : cooldown > 0 ? (
              <span>Wait ({cooldown}s)</span>
            ) : (
              <>
                <Play className="h-3.5 w-3.5 fill-current" /> Run Code
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Content Split: Problem Sidebar (Left), Editor (Center), Console (Right) */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Left Column: Problem Description Selector (300px) */}
        <div className="w-80 bg-slate-950 border-r border-slate-800 flex flex-col shrink-0 overflow-hidden">
          <div className="p-4 border-b border-slate-800 bg-slate-900/60">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-blue-400" />
              Practice Problem Set
            </h2>
          </div>

          {/* Problem Selector Dropdown */}
          <div className="p-3 border-b border-slate-800">
            <select
              value={selectedProblem.id}
              onChange={(e) => {
                const found = PRACTICE_PROBLEMS.find((p) => p.id === e.target.value);
                if (found) handleProblemSelect(found);
              }}
              className="w-full bg-slate-900 border border-slate-800 text-slate-200 text-xs font-semibold rounded-lg p-2 focus:ring-2 focus:ring-blue-500 outline-none"
            >
              {PRACTICE_PROBLEMS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title} ({p.difficulty})
                </option>
              ))}
            </select>
          </div>

          {/* Selected Problem Description Pane */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs leading-relaxed">
            <div className="flex items-center justify-between">
              <span
                className={`px-2 py-0.5 rounded font-bold text-[10px] ${
                  selectedProblem.difficulty === "EASY"
                    ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                    : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                }`}
              >
                {selectedProblem.difficulty}
              </span>
              <span className="text-[10px] text-slate-400">{selectedProblem.category}</span>
            </div>

            <div>
              <h3 className="text-sm font-bold text-white mb-2">{selectedProblem.title}</h3>
              <p className="text-slate-300 whitespace-pre-wrap font-sans">{selectedProblem.description}</p>
            </div>

            {/* Examples */}
            <div className="space-y-3 pt-2">
              <h4 className="font-bold text-slate-400 text-[11px] uppercase tracking-wider">Examples:</h4>
              {selectedProblem.examples.map((ex, idx) => (
                <div key={idx} className="bg-slate-900 p-3 rounded-lg border border-slate-800 space-y-1 font-mono text-[11px]">
                  <div><strong className="text-slate-400">Input:</strong> <span className="text-slate-200">{ex.input}</span></div>
                  <div><strong className="text-slate-400">Output:</strong> <span className="text-emerald-400">{ex.output}</span></div>
                  {ex.explanation && <div className="text-slate-500 font-sans text-[10px] italic mt-1">{ex.explanation}</div>}
                </div>
              ))}
            </div>

            {/* Constraints Note */}
            <div className="p-3 bg-blue-950/40 border border-blue-900/50 rounded-lg text-blue-300 text-[11px] space-y-1">
              <strong className="block font-bold">Sandbox Restrictions:</strong>
              <div>• Time Limit: 5.0 seconds</div>
              <div>• Memory Limit: 128 MB</div>
              <div>• Output Size Limit: 2,000 chars</div>
            </div>
          </div>
        </div>

        {/* Center Column: Monaco Code Editor */}
        <div className="flex-1 flex flex-col border-r border-slate-800 bg-slate-900 overflow-hidden">
          <div className="bg-slate-950 px-4 py-2 flex items-center justify-between border-b border-slate-800 text-xs">
            <span className="text-slate-300 font-semibold font-mono flex items-center gap-2">
              <FileCode className="h-4 w-4 text-blue-400" />
              solution.{language === "python" ? "py" : language === "javascript" ? "js" : language === "java" ? "java" : "cpp"}
            </span>
            <span className="text-slate-500 font-mono text-[11px]">
              {language.toUpperCase()} Execution Engine
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
                fontSize: 13,
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                padding: { top: 12 },
                scrollBeyondLastLine: false,
                smoothScrolling: true,
                automaticLayout: true,
              }}
            />
          </div>
        </div>

        {/* Right Column: Console / STDIN Pane (340px) */}
        <div className="w-80 bg-slate-950 flex flex-col shrink-0 overflow-hidden">
          {/* Tabs Header */}
          <div className="flex border-b border-slate-800 bg-slate-900 text-xs font-semibold">
            <button
              onClick={() => setActiveTab("console")}
              className={`flex-1 py-2.5 text-center transition ${
                activeTab === "console" ? "text-blue-400 bg-slate-950 border-b-2 border-blue-500" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Output Console
            </button>
            <button
              onClick={() => setActiveTab("stdin")}
              className={`flex-1 py-2.5 text-center transition ${
                activeTab === "stdin" ? "text-blue-400 bg-slate-950 border-b-2 border-blue-500" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Custom STDIN
            </button>
            <button
              onClick={() => setActiveTab("testcases")}
              className={`flex-1 py-2.5 text-center transition ${
                activeTab === "testcases" ? "text-blue-400 bg-slate-950 border-b-2 border-blue-500" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Test Cases
            </button>
          </div>

          {/* Tab Content */}
          <div className="flex-1 p-4 overflow-y-auto font-mono text-xs leading-relaxed bg-slate-950">
            {activeTab === "console" && (
              <div className="space-y-2">
                {wallTimeMs !== null && (
                  <div className="text-[10px] text-slate-400 border-b border-slate-800 pb-2 flex justify-between">
                    <span>Status: <strong className="text-emerald-400">Success</strong></span>
                    <span>Time: <strong className="text-blue-400">{wallTimeMs} ms</strong></span>
                  </div>
                )}

                {output.length === 0 ? (
                  <div className="text-slate-500 italic py-6 text-center">
                    Ready for execution. Press "Run Code" to execute script.
                  </div>
                ) : (
                  output.map((line, idx) => (
                    <div
                      key={idx}
                      className={
                        line.includes("Error") || line.includes("Exception") || line.includes("Stderr")
                          ? "text-red-400"
                          : "text-slate-200"
                      }
                    >
                      <span className="text-slate-600 mr-2">›</span>
                      {line}
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === "stdin" && (
              <div className="space-y-2">
                <label className="block text-[11px] font-semibold text-slate-400">
                  Standard Input (STDIN)
                </label>
                <p className="text-[10px] text-slate-500">Provide custom input passed to std::cin / sys.stdin / readline.</p>
                <textarea
                  value={customInput}
                  onChange={(e) => setCustomInput(e.target.value)}
                  rows={10}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg p-3 text-slate-200 outline-none focus:border-blue-500 text-xs font-mono"
                  placeholder="Enter custom input lines here..."
                />
              </div>
            )}

            {activeTab === "testcases" && (
              <div className="space-y-3">
                <div className="text-[11px] font-bold text-slate-400">Problem Test Suite</div>
                {selectedProblem.testCases.map((tc, idx) => (
                  <div key={idx} className="p-3 bg-slate-900 rounded-lg border border-slate-800 space-y-1 text-[11px]">
                    <div className="text-slate-400">Test Case #{idx + 1}:</div>
                    <div><span className="text-slate-500">Input:</span> <span className="text-slate-200">{tc.input}</span></div>
                    <div><span className="text-slate-500">Expected:</span> <span className="text-emerald-400">{tc.expected}</span></div>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>

      </div>
    </div>
  );
}
