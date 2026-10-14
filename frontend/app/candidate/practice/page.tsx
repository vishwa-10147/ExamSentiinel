"use client";

import React, { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useTheme } from "next-themes";
import toast from "react-hot-toast";
import { Code2, Loader2, Play, RotateCcw } from "lucide-react";
import { apiClient } from "@/services/apiClient";
import { LANGUAGE_LABELS, MONACO_LANGUAGE, PracticeLanguage } from "@/services/practiceService";

const Editor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => <div className="flex h-full items-center justify-center text-sm text-slate-500">Loading editor…</div>,
});

const LANGUAGES: PracticeLanguage[] = ["python", "javascript", "java", "cpp", "c", "sql"];

const TEMPLATES: Record<PracticeLanguage, string> = {
  python: 'name = input().strip()\nprint(f"Hello, {name}!")\n',
  javascript: 'const input = require("fs").readFileSync(0, "utf8").trim();\nconsole.log(`Hello, ${input}!`);\n',
  java:
    'import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner in = new Scanner(System.in);\n        String name = in.nextLine().trim();\n        System.out.println("Hello, " + name + "!");\n    }\n}\n',
  cpp:
    '#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    string name;\n    getline(cin, name);\n    cout << "Hello, " << name << "!" << endl;\n    return 0;\n}\n',
  sql:
    "-- SQLite: create tables, add rows, then query them.\nCREATE TABLE scores (name TEXT, score INTEGER);\nINSERT INTO scores VALUES ('Asha', 91), ('Ben', 78), ('Chen', 85);\n\nSELECT name, score FROM scores ORDER BY score DESC;\n",
  c: '#include <stdio.h>\n#include <string.h>\n\nint main(void) {\n    char name[256];\n    if (fgets(name, sizeof name, stdin)) {\n        name[strcspn(name, "\\n")] = 0;\n        printf("Hello, %s!\\n", name);\n    }\n    return 0;\n}\n',
};

interface ExecResult {
  status: string;
  stdout: string;
  stderr: string;
  compile_output?: string;
  exit_code?: number | null;
  wall_time_ms?: number | null;
}

const STATUS_LABEL: Record<string, { text: string; tone: string }> = {
  success: { text: "Finished", tone: "text-emerald-600 dark:text-emerald-400" },
  error: { text: "Runtime Error", tone: "text-rose-600 dark:text-rose-400" },
  compile_error: { text: "Compile Error", tone: "text-amber-600 dark:text-amber-400" },
  timeout: { text: "Time Limit Exceeded", tone: "text-rose-600 dark:text-rose-400" },
  memory_limit: { text: "Memory Limit Exceeded", tone: "text-rose-600 dark:text-rose-400" },
  output_limit: { text: "Output Limit Exceeded", tone: "text-rose-600 dark:text-rose-400" },
  system_error: { text: "Execution engine unavailable", tone: "text-slate-500" },
};

function readDraft(lang: PracticeLanguage): string {
  try {
    return window.localStorage.getItem(`playground:${lang}`) ?? TEMPLATES[lang];
  } catch {
    return TEMPLATES[lang];
  }
}

export default function PracticePlaygroundPage() {
  const { resolvedTheme } = useTheme();
  const [language, setLanguage] = useState<PracticeLanguage>("python");
  const [code, setCode] = useState(TEMPLATES.python);
  const [stdin, setStdin] = useState("ExamSentinel");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ExecResult | null>(null);
  const runRef = useRef<() => void>(() => undefined);

  useEffect(() => {
    setCode(readDraft("python"));
  }, []);

  useEffect(() => {
    const t = setTimeout(() => {
      try {
        window.localStorage.setItem(`playground:${language}`, code);
      } catch {
        /* drafts are a convenience only */
      }
    }, 400);
    return () => clearTimeout(t);
  }, [code, language]);

  const changeLanguage = (lang: PracticeLanguage) => {
    setLanguage(lang);
    setCode(readDraft(lang));
    setResult(null);
  };

  const run = async () => {
    if (running) return;
    setRunning(true);
    try {
      const r = await apiClient.post<ExecResult>("/api/sandbox/execute", { language, code, stdin });
      setResult(r);
    } catch (e: any) {
      toast.error(e?.message || "Execution failed.");
    } finally {
      setRunning(false);
    }
  };
  runRef.current = run;

  const status = result ? STATUS_LABEL[result.status] ?? { text: result.status, tone: "text-slate-600" } : null;

  return (
    <div className="flex h-full flex-col bg-slate-50 dark:bg-slate-900">
      <div className="flex flex-wrap items-center gap-3 border-b border-slate-200 bg-white px-4 py-2.5 dark:border-slate-700 dark:bg-slate-800">
        <h1 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
          <Code2 className="h-5 w-5 text-blue-600" /> Code Playground
        </h1>
        <select
          value={language}
          onChange={(e) => changeLanguage(e.target.value as PracticeLanguage)}
          aria-label="Language"
          className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm text-slate-800 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
        >
          {LANGUAGES.map((l) => (
            <option key={l} value={l}>{LANGUAGE_LABELS[l]}</option>
          ))}
        </select>
        <button
          onClick={() => setCode(TEMPLATES[language])}
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-700 dark:hover:text-white"
        >
          <RotateCcw className="h-3.5 w-3.5" /> Template
        </button>
        <Link href="/candidate/problems" className="text-xs font-medium text-blue-600 hover:underline">
          Browse problems →
        </Link>
        <button
          onClick={() => void run()}
          disabled={running}
          title="Run (Ctrl+Enter)"
          className="ml-auto inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60"
        >
          {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />} Run
        </button>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[1fr_380px]">
        <div className="min-h-[420px] lg:min-h-0">
          <Editor
            height="100%"
            language={MONACO_LANGUAGE[language]}
            theme={resolvedTheme === "dark" ? "vs-dark" : "light"}
            value={code}
            onChange={(v) => setCode(v ?? "")}
            onMount={(editor: any, monaco: any) =>
              editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => runRef.current())
            }
            options={{ fontSize: 14, minimap: { enabled: false }, scrollBeyondLastLine: false, automaticLayout: true, padding: { top: 12 } }}
          />
        </div>
        <div className="flex min-h-0 flex-col gap-3 border-l border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
          <div>
            <label htmlFor="stdin" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
              Standard input
            </label>
            <textarea
              id="stdin"
              value={stdin}
              onChange={(e) => setStdin(e.target.value)}
              rows={6}
              spellCheck={false}
              className="w-full rounded-lg border border-slate-300 bg-slate-50 p-2 font-mono text-[13px] text-slate-800 outline-none focus:border-blue-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
            />
          </div>
          <div className="flex min-h-0 flex-1 flex-col">
            <div className="mb-1 flex items-baseline justify-between">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Output</span>
              {status && (
                <span className={`text-xs font-semibold ${status.tone}`}>
                  {status.text}
                  {result?.exit_code != null && result.status !== "compile_error" && result.status !== "system_error" ? ` · exit ${result.exit_code}` : ""}
                  {result?.wall_time_ms != null && result.status !== "system_error" ? ` · ${result.wall_time_ms} ms` : ""}
                </span>
              )}
            </div>
            <pre className="min-h-[160px] flex-1 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-slate-900 p-3 font-mono text-[13px] text-slate-100">
              {running ? "Running…" : result ? result.stdout || (result.stderr ? "" : "(no output)") : "Press Run to execute your code."}
              {!running && result?.stderr && <span className="text-rose-300">{(result.stdout ? "\n" : "") + result.stderr}</span>}
            </pre>
          </div>
          <p className="text-xs text-slate-500">
            Runs in an isolated sandbox with a 5 s time limit, 256 MB memory and no network access. Java code must define <code>public class Main</code>.
          </p>
        </div>
      </div>
    </div>
  );
}
