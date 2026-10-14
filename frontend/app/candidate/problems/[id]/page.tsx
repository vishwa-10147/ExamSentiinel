"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useTheme } from "next-themes";
import toast from "react-hot-toast";
import {
  ChevronDown,
  ChevronLeft,
  ChevronUp,
  BookOpen,
  Clock,
  FileText,
  Gauge,
  History,
  Lightbulb,
  Loader2,
  Lock,
  Play,
  RotateCcw,
  Send,
} from "lucide-react";
import {
  CaseResult,
  LANGUAGE_LABELS,
  MONACO_LANGUAGE,
  PracticeLanguage,
  ProblemDetail,
  RunResult,
  Submission,
  VERDICT_LABELS,
  formatCaseInput,
  practiceService,
} from "@/services/practiceService";
import Markdown from "@/components/practice/Markdown";
import { DifficultyBadge, StatusIcon, VerdictText, verdictColor } from "@/components/practice/badges";

const Editor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => <div className="flex h-full items-center justify-center text-sm text-slate-500">Loading editor…</div>,
});

type LeftTab = "description" | "editorial" | "submissions";
type ConsoleTab = "testcase" | "result";

interface ConsoleResult {
  kind: "run" | "submit";
  verdict: RunResult["verdict"];
  cases: CaseResult[];
  passed: number;
  total: number;
  runtime_ms: number | null;
  compile_output: string | null;
  error: string | null;
  hiddenFailure?: { case_number?: number; error?: string | null };
}

const storage = {
  get(key: string): string | null {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key: string, value: string) {
    try {
      window.localStorage.setItem(key, value);
    } catch {
      /* storage unavailable (private mode) — drafts just won't persist */
    }
  },
};

function Block({ label, value, mono = true, tone }: { label: string; value: string; mono?: boolean; tone?: "error" }) {
  return (
    <div>
      <div className="mb-1 text-xs font-medium text-slate-500 dark:text-slate-400">{label}</div>
      <pre
        className={`max-h-48 overflow-auto whitespace-pre-wrap break-all rounded-lg px-3 py-2 text-[13px] ${mono ? "font-mono" : ""} ${
          tone === "error"
            ? "bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300"
            : "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200"
        }`}
      >
        {value || " "}
      </pre>
    </div>
  );
}

export default function ProblemWorkspacePage() {
  const params = useParams();
  const slug = String(params?.id || "");
  const { resolvedTheme } = useTheme();

  const [problem, setProblem] = useState<ProblemDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [language, setLanguage] = useState<PracticeLanguage>("python");
  const [code, setCode] = useState("");
  const [leftTab, setLeftTab] = useState<LeftTab>("description");
  const [consoleTab, setConsoleTab] = useState<ConsoleTab>("testcase");
  const [consoleOpen, setConsoleOpen] = useState(true);
  const [selectedCase, setSelectedCase] = useState(0);
  const [useCustom, setUseCustom] = useState(false);
  const [customInput, setCustomInput] = useState("");
  const [busy, setBusy] = useState<"run" | "submit" | null>(null);
  const [result, setResult] = useState<ConsoleResult | null>(null);
  const [selectedResultCase, setSelectedResultCase] = useState(0);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [shownHints, setShownHints] = useState<number>(0);

  const draftKey = (lang: string) => `practice:code:${slug}:${lang}`;

  // ---- Load problem -------------------------------------------------------
  useEffect(() => {
    if (!slug) return;
    let cancelled = false;
    (async () => {
      try {
        const p = await practiceService.getProblem(slug);
        if (cancelled) return;
        setProblem(p);
        const savedLang = storage.get("practice:language") as PracticeLanguage | null;
        const lang = savedLang && p.languages.includes(savedLang) ? savedLang : p.languages[0];
        setLanguage(lang);
        setCode(storage.get(draftKey(lang)) ?? p.starter_code[lang] ?? "");
        setCustomInput(p.examples[0]?.input ?? "");
        setLoadError(null);
      } catch (e: any) {
        if (!cancelled) setLoadError(e?.message || "Problem not found.");
      }
    })();
    practiceService.submissions(slug).then(setSubmissions).catch(() => undefined);
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug]);

  // ---- Draft persistence ------------------------------------------------
  useEffect(() => {
    if (!problem) return;
    const t = setTimeout(() => storage.set(draftKey(language), code), 400);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code, language, problem]);

  const changeLanguage = (lang: PracticeLanguage) => {
    if (!problem) return;
    storage.set(draftKey(language), code);
    storage.set("practice:language", lang);
    setLanguage(lang);
    setCode(storage.get(draftKey(lang)) ?? problem.starter_code[lang] ?? "");
  };

  const resetCode = () => {
    if (!problem) return;
    if (!window.confirm("Reset your code to the starter template? Your current draft for this language will be lost.")) return;
    setCode(problem.starter_code[language] ?? "");
  };

  // ---- Run / submit -------------------------------------------------------
  const run = useCallback(async () => {
    if (!problem || busy) return;
    setBusy("run");
    setConsoleOpen(true);
    setConsoleTab("result");
    try {
      const r = await practiceService.run(problem.slug, language, code, useCustom ? customInput : undefined);
      setResult({
        kind: "run",
        verdict: r.verdict,
        cases: r.cases,
        passed: r.passed_count,
        total: r.total_count,
        runtime_ms: r.runtime_ms,
        compile_output: r.compile_output,
        error: r.error,
      });
      const firstFail = r.cases.findIndex((c) => c.passed === false);
      setSelectedResultCase(firstFail >= 0 ? firstFail : 0);
    } catch (e: any) {
      toast.error(e?.message || "Run failed.");
    } finally {
      setBusy(null);
    }
  }, [problem, busy, language, code, useCustom, customInput]);

  const submit = useCallback(async () => {
    if (!problem || busy) return;
    setBusy("submit");
    setConsoleOpen(true);
    setConsoleTab("result");
    try {
      const s = await practiceService.submit(problem.slug, language, code);
      const f = s.failure;
      const cases: CaseResult[] =
        f && f.is_sample !== undefined && f.case_number
          ? [
              {
                index: f.case_number - 1,
                passed: false,
                input: f.input ?? null,
                expected: f.expected ?? null,
                output: f.output ?? null,
                stdout: f.stdout ?? "",
                runtime_ms: f.runtime_ms ?? null,
                error: f.error ?? null,
                is_custom: false,
              },
            ]
          : [];
      setResult({
        kind: "submit",
        verdict: s.verdict,
        cases: f?.is_sample ? cases : [],
        passed: s.passed_count,
        total: s.total_count,
        runtime_ms: s.runtime_ms,
        compile_output: s.compile_output ?? (s.verdict === "COMPILE_ERROR" ? f?.error ?? null : null),
        error: s.verdict === "SYSTEM_ERROR" ? f?.error ?? null : null,
        hiddenFailure: f && f.is_sample === false ? { case_number: f.case_number, error: f.error } : undefined,
      });
      setSelectedResultCase(0);
      if (s.verdict === "ACCEPTED") {
        toast.success(`Accepted! ${s.passed_count}/${s.total_count} tests passed.`);
        setProblem((p) => (p ? { ...p, status: "solved" } : p));
        // Solving unlocks the editorial; refetch to receive it.
        practiceService.getProblem(problem.slug).then((fresh) => setProblem((p) => (p ? { ...p, editorial: fresh.editorial } : p))).catch(() => undefined);
      } else if (s.verdict !== "SYSTEM_ERROR") {
        setProblem((p) => (p && p.status === "todo" ? { ...p, status: "attempted" } : p));
      }
      practiceService.submissions(problem.slug).then(setSubmissions).catch(() => undefined);
    } catch (e: any) {
      toast.error(e?.message || "Submission failed.");
    } finally {
      setBusy(null);
    }
  }, [problem, busy, language, code]);

  // Keyboard shortcuts — refs keep Monaco's registered commands pointing at the latest handlers.
  const runRef = useRef(run);
  const submitRef = useRef(submit);
  useEffect(() => {
    runRef.current = run;
    submitRef.current = submit;
  }, [run, submit]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        if (e.shiftKey) void submitRef.current();
        else void runRef.current();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const handleEditorMount = (editor: any, monaco: any) => {
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => void runRef.current());
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.Enter, () => void submitRef.current());
  };

  const spec = problem?.function_spec ?? null;
  const resultCase = result?.cases[selectedResultCase];
  const exampleCount = problem?.examples.length ?? 0;

  const acceptedRuntime = useMemo(
    () => submissions.filter((s) => s.verdict === "ACCEPTED" && s.runtime_ms != null).map((s) => s.runtime_ms as number),
    [submissions]
  );

  if (loadError) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
        <p className="text-slate-600 dark:text-slate-300">{loadError}</p>
        <Link href="/candidate/problems" className="text-sm font-semibold text-blue-600 hover:underline">
          Back to problems
        </Link>
      </div>
    );
  }

  if (!problem) {
    return (
      <div className="flex h-full items-center justify-center text-slate-500">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading problem…
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-slate-50 dark:bg-slate-900">
      {/* Top bar */}
      <div className="flex flex-wrap items-center gap-3 border-b border-slate-200 bg-white px-4 py-2 dark:border-slate-700 dark:bg-slate-800">
        <Link
          href="/candidate/problems"
          className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"
        >
          <ChevronLeft className="h-4 w-4" /> Problems
        </Link>
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <StatusIcon status={problem.status} />
          <h1 className="truncate text-sm font-semibold text-slate-900 dark:text-white">{problem.number != null ? `${problem.number}. ` : ""}{problem.title}</h1>
          <DifficultyBadge difficulty={problem.difficulty} />
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => void run()}
            disabled={!!busy}
            title="Run sample tests (Ctrl+Enter)"
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 dark:hover:bg-slate-600"
          >
            {busy === "run" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />} Run
          </button>
          <button
            onClick={() => void submit()}
            disabled={!!busy}
            title="Submit against all tests (Ctrl+Shift+Enter)"
            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60"
          >
            {busy === "submit" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />} Submit
          </button>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-2">
        {/* Left: description / submissions */}
        <section className="flex min-h-0 flex-col border-r border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
          <div className="flex gap-1 border-b border-slate-200 px-3 pt-2 dark:border-slate-700" role="tablist">
            {([
              ["description", "Description", FileText],
              ["editorial", "Editorial", BookOpen],
              ["submissions", `Submissions${submissions.length ? ` (${submissions.length})` : ""}`, History],
            ] as const).map(([key, label, Icon]) => (
              <button
                key={key}
                role="tab"
                aria-selected={leftTab === key}
                onClick={() => setLeftTab(key)}
                className={`inline-flex items-center gap-1.5 rounded-t-lg px-3 py-2 text-sm font-medium ${
                  leftTab === key
                    ? "border-b-2 border-blue-600 text-blue-700 dark:text-blue-400"
                    : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                <Icon className="h-4 w-4" /> {label}
              </button>
            ))}
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto p-5 text-sm text-slate-700 dark:text-slate-300">
            {leftTab === "description" ? (
              <div className="space-y-6">
                <div className="flex flex-wrap gap-1.5">
                  {problem.topic && (
                    <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-500/10 dark:text-blue-300">
                      {problem.topic}
                    </span>
                  )}
                  {problem.tags.map((t) => (
                    <span key={t} className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                      {t}
                    </span>
                  ))}
                </div>

                <Markdown source={problem.statement} />

                {problem.input_format && (
                  <div>
                    <h3 className="mb-2 font-semibold text-slate-900 dark:text-white">Input format</h3>
                    <Markdown source={problem.input_format} />
                  </div>
                )}
                {problem.output_format && (
                  <div>
                    <h3 className="mb-2 font-semibold text-slate-900 dark:text-white">Output format</h3>
                    <Markdown source={problem.output_format} />
                  </div>
                )}

                {problem.sql_schema && (
                  <div>
                    <h3 className="mb-2 font-semibold text-slate-900 dark:text-white">Tables</h3>
                    <pre className="overflow-x-auto rounded-lg bg-slate-100 p-3 font-mono text-[12px] leading-relaxed text-slate-800 dark:bg-slate-900 dark:text-slate-200">
                      {problem.sql_schema}
                    </pre>
                    <p className="mt-1 text-xs text-slate-500">
                      Rows may be returned in {problem.compare_mode === "exact" ? "the order the statement asks for" : "any order"}.
                    </p>
                  </div>
                )}

                {problem.examples.map((ex, i) => (
                  <div key={i}>
                    <h3 className="mb-2 font-semibold text-slate-900 dark:text-white">Example {i + 1}</h3>
                    <div className="space-y-1 border-l-2 border-slate-200 pl-4 font-mono text-[13px] dark:border-slate-600">
                      {problem.judge_mode === "SQL" ? (
                        <div>
                          <span className="font-sans font-semibold text-slate-900 dark:text-white">Data:</span>
                          <pre className="mt-1 max-h-56 overflow-auto whitespace-pre text-[12px]">{ex.input || "(all tables empty)"}</pre>
                        </div>
                      ) : (
                        <div className="whitespace-pre-wrap break-all">
                          <span className="font-sans font-semibold text-slate-900 dark:text-white">Input: </span>
                          {spec ? formatCaseInput(ex.input, spec).split("\n").join(", ") : ex.input}
                        </div>
                      )}
                      <div className="whitespace-pre-wrap break-all">
                        <span className="font-sans font-semibold text-slate-900 dark:text-white">Output: </span>
                        {ex.expected_output}
                      </div>
                      {ex.explanation && (
                        <div className="font-sans">
                          <span className="font-semibold text-slate-900 dark:text-white">Explanation: </span>
                          {ex.explanation}
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {problem.constraints && (
                  <div>
                    <h3 className="mb-2 font-semibold text-slate-900 dark:text-white">Constraints</h3>
                    <Markdown source={problem.constraints} />
                  </div>
                )}

                <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500">
                  <span className="inline-flex items-center gap-1"><Clock className="h-3.5 w-3.5" /> {problem.time_limit_ms} ms per test</span>
                  <span>{problem.memory_limit_mb} MB memory</span>
                  {problem.complexity && (
                    <span className="inline-flex items-center gap-1"><Gauge className="h-3.5 w-3.5" /> Target: {problem.complexity}</span>
                  )}
                </div>

                {problem.hints.length > 0 && (
                  <div className="space-y-2">
                    {problem.hints.slice(0, shownHints).map((h, i) => (
                      <div key={i} className="flex gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
                        <Lightbulb className="mt-0.5 h-4 w-4 shrink-0" />
                        <Markdown source={h} />
                      </div>
                    ))}
                    {shownHints < problem.hints.length && (
                      <button
                        onClick={() => setShownHints((n) => n + 1)}
                        className="inline-flex items-center gap-1.5 text-sm font-medium text-amber-700 hover:underline dark:text-amber-400"
                      >
                        <Lightbulb className="h-4 w-4" /> Show hint {shownHints + 1} of {problem.hints.length}
                      </button>
                    )}
                  </div>
                )}
              </div>
            ) : leftTab === "editorial" ? (
              problem.editorial ? (
                <div className="space-y-4">
                  <h3 className="font-semibold text-slate-900 dark:text-white">Approach</h3>
                  <Markdown source={problem.editorial} />
                  {problem.complexity && <p className="text-xs text-slate-500">Complexity: {problem.complexity}</p>}
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2 py-10 text-center text-slate-500">
                  <Lock className="h-6 w-6" />
                  <p>{problem.has_editorial ? "Solve this problem to unlock the editorial." : "No editorial has been written for this problem yet."}</p>
                </div>
              )
            ) : submissions.length === 0 ? (
              <p className="py-10 text-center text-slate-500">No submissions yet. Submit your solution to see it here.</p>
            ) : (
              <div className="space-y-3">
                {acceptedRuntime.length > 0 && (
                  <p className="text-xs text-slate-500">Best accepted runtime: {Math.min(...acceptedRuntime)} ms</p>
                )}
                <table className="w-full text-sm">
                  <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="py-2 pr-3">Status</th>
                      <th className="py-2 pr-3">Language</th>
                      <th className="py-2 pr-3">Tests</th>
                      <th className="py-2 pr-3">Runtime</th>
                      <th className="py-2" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                    {submissions.map((s) => (
                      <tr key={s.id}>
                        <td className="py-2 pr-3">
                          <VerdictText verdict={s.verdict} />
                          <div className="text-xs text-slate-400">{new Date(s.created_at).toLocaleString()}</div>
                        </td>
                        <td className="py-2 pr-3">{LANGUAGE_LABELS[s.language as PracticeLanguage] ?? s.language}</td>
                        <td className="py-2 tabular-nums">{s.passed_count}/{s.total_count}</td>
                        <td className="py-2 tabular-nums">{s.runtime_ms != null ? `${s.runtime_ms} ms` : "—"}</td>
                        <td className="py-2 text-right">
                          {s.source_code && (
                            <button
                              onClick={() => {
                                const lang = s.language as PracticeLanguage;
                                if (problem.languages.includes(lang)) {
                                  storage.set(draftKey(language), code);
                                  setLanguage(lang);
                                }
                                setCode(s.source_code || "");
                                toast.success("Loaded submission into the editor.");
                              }}
                              className="text-xs font-semibold text-blue-600 hover:underline"
                            >
                              Load code
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>

        {/* Right: editor + console */}
        <section className="flex min-h-[600px] flex-col lg:min-h-0">
          <div className="flex items-center gap-2 border-b border-slate-200 bg-white px-3 py-1.5 dark:border-slate-700 dark:bg-slate-800">
            <select
              value={language}
              onChange={(e) => changeLanguage(e.target.value as PracticeLanguage)}
              aria-label="Language"
              className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm text-slate-800 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
            >
              {problem.languages.map((l) => (
                <option key={l} value={l}>{LANGUAGE_LABELS[l]}</option>
              ))}
            </select>
            <span className="text-xs text-slate-400">Auto-saved</span>
            <button
              onClick={resetCode}
              title="Reset to starter code"
              className="ml-auto inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-700 dark:hover:text-white"
            >
              <RotateCcw className="h-3.5 w-3.5" /> Reset
            </button>
          </div>

          <div className="min-h-0 flex-1">
            <Editor
              height="100%"
              language={MONACO_LANGUAGE[language]}
              theme={resolvedTheme === "dark" ? "vs-dark" : "light"}
              value={code}
              onChange={(v) => setCode(v ?? "")}
              onMount={handleEditorMount}
              options={{
                fontSize: 14,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                tabSize: 4,
                automaticLayout: true,
                padding: { top: 12 },
              }}
            />
          </div>

          {/* Console */}
          <div className={`flex flex-col border-t border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800 ${consoleOpen ? "h-[42%] min-h-[220px]" : ""}`}>
            <div className="flex items-center gap-1 px-3 pt-1.5">
              {(["testcase", "result"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => {
                    setConsoleTab(t);
                    setConsoleOpen(true);
                  }}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                    consoleOpen && consoleTab === t
                      ? "bg-slate-100 text-slate-900 dark:bg-slate-700 dark:text-white"
                      : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                  }`}
                >
                  {t === "testcase" ? "Testcase" : "Test Result"}
                </button>
              ))}
              <button
                onClick={() => setConsoleOpen((o) => !o)}
                aria-label={consoleOpen ? "Collapse console" : "Expand console"}
                className="ml-auto rounded-md p-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700"
              >
                {consoleOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
              </button>
            </div>

            {consoleOpen && (
              <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-4 pt-2 text-sm">
                {consoleTab === "testcase" ? (
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-1.5">
                      {problem.examples.map((_, i) => (
                        <button
                          key={i}
                          onClick={() => {
                            setSelectedCase(i);
                            setUseCustom(false);
                          }}
                          className={`rounded-md px-3 py-1 text-xs font-semibold ${
                            !useCustom && selectedCase === i
                              ? "bg-slate-200 text-slate-900 dark:bg-slate-600 dark:text-white"
                              : "bg-slate-100 text-slate-600 dark:bg-slate-700/50 dark:text-slate-300"
                          }`}
                        >
                          Case {i + 1}
                        </button>
                      ))}
                      <button
                        onClick={() => setUseCustom(true)}
                        className={`rounded-md px-3 py-1 text-xs font-semibold ${
                          useCustom ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-600 dark:bg-slate-700/50 dark:text-slate-300"
                        }`}
                      >
                        + Custom
                      </button>
                    </div>
                    {useCustom ? (
                      <div className="space-y-1.5">
                        <label className="text-xs text-slate-500" htmlFor="custom-input">
                          {spec
                            ? `One JSON value per line, in order: ${spec.params.map((p) => `${p.name} (${p.type})`).join(", ")}`
                            : problem.judge_mode === "SQL"
                              ? "INSERT statements that fill the tables for your own dataset"
                              : "Standard input for your program"}
                        </label>
                        <textarea
                          id="custom-input"
                          value={customInput}
                          onChange={(e) => setCustomInput(e.target.value)}
                          rows={Math.max(3, (spec?.params.length ?? 3) + 1)}
                          spellCheck={false}
                          className="w-full rounded-lg border border-slate-300 bg-slate-50 p-2 font-mono text-[13px] text-slate-800 outline-none focus:border-blue-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
                        />
                        <p className="text-xs text-slate-500">
                          Custom input runs alongside the examples.
                          {problem.has_reference_solution ? " The expected answer is computed for you." : ""}
                        </p>
                      </div>
                    ) : exampleCount > 0 ? (
                      <Block
                        label="Input"
                        value={formatCaseInput(problem.examples[selectedCase]?.input ?? "", spec)}
                      />
                    ) : (
                      <p className="text-slate-500">This problem has no example cases.</p>
                    )}
                  </div>
                ) : !result && !busy ? (
                  <p className="py-6 text-center text-slate-500">Run or submit your code to see results here.</p>
                ) : busy ? (
                  <div className="flex items-center justify-center gap-2 py-8 text-slate-500">
                    <Loader2 className="h-5 w-5 animate-spin" /> {busy === "run" ? "Running sample tests…" : "Judging against all tests…"}
                  </div>
                ) : result ? (
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
                      <span className={`text-lg font-bold ${verdictColor(result.verdict)}`}>{VERDICT_LABELS[result.verdict]}</span>
                      {result.verdict !== "COMPILE_ERROR" && result.verdict !== "SYSTEM_ERROR" && (
                        <span className="text-xs text-slate-500">
                          {result.passed}/{result.total} {result.kind === "run" ? "sample" : ""} tests passed
                          {result.runtime_ms != null && ` · ${result.runtime_ms} ms`}
                        </span>
                      )}
                      {result.kind === "submit" && result.verdict === "ACCEPTED" && (
                        <span className="text-xs text-emerald-600 dark:text-emerald-400">Solution recorded in your submissions.</span>
                      )}
                    </div>

                    {result.compile_output && <Block label="Compiler output" value={result.compile_output} tone="error" />}
                    {result.error && !result.cases.length && result.verdict === "SYSTEM_ERROR" && (
                      <Block label="Details" value={result.error} tone="error" mono={false} />
                    )}
                    {result.hiddenFailure && (
                      <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                        Failed on hidden test case #{result.hiddenFailure.case_number}. Hidden test inputs are not shown — think about edge cases and constraints.
                        {result.hiddenFailure.error && <div className="mt-1 font-mono text-xs text-rose-600 dark:text-rose-400">{result.hiddenFailure.error}</div>}
                      </div>
                    )}

                    {result.cases.length > 0 && (
                      <>
                        <div className="flex flex-wrap gap-1.5">
                          {result.cases.map((c, i) => (
                            <button
                              key={i}
                              onClick={() => setSelectedResultCase(i)}
                              className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-semibold ${
                                selectedResultCase === i ? "bg-slate-200 dark:bg-slate-600" : "bg-slate-100 dark:bg-slate-700/50"
                              }`}
                            >
                              <span
                                className={`h-1.5 w-1.5 rounded-full ${
                                  c.passed === true ? "bg-emerald-500" : c.passed === false ? "bg-rose-500" : "bg-slate-400"
                                }`}
                              />
                              <span className="text-slate-700 dark:text-slate-200">
                                {c.is_custom ? "Custom" : result.kind === "submit" ? `Test ${c.index + 1}` : `Case ${c.index + 1}`}
                              </span>
                            </button>
                          ))}
                        </div>
                        {resultCase && (
                          <div className="space-y-2.5">
                            {resultCase.input != null && <Block label="Input" value={formatCaseInput(resultCase.input, spec)} />}
                            {resultCase.error ? (
                              <Block label="Error" value={resultCase.error} tone="error" />
                            ) : (
                              <Block label="Output" value={resultCase.output ?? ""} />
                            )}
                            {resultCase.expected != null && <Block label="Expected" value={resultCase.expected} />}
                            {resultCase.is_custom && resultCase.expected == null && (
                              <p className="text-xs text-slate-500">No reference answer available for custom input.</p>
                            )}
                            {resultCase.stdout && <Block label="Stdout" value={resultCase.stdout} />}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                ) : null}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
