"use client";

import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import toast from "react-hot-toast";
import { ChevronLeft, Loader2, Plus, Save, ShieldCheck, Trash2 } from "lucide-react";
import {
  Difficulty,
  FunctionSpec,
  LANGUAGE_LABELS,
  MONACO_LANGUAGE,
  PracticeLanguage,
  ProblemUpsert,
  TestCaseInput,
  ValidationReport,
  practiceService,
} from "@/services/practiceService";
import Markdown from "@/components/practice/Markdown";

const Editor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

const TYPES = ["int", "long", "double", "bool", "string", "int[]", "long[]", "double[]", "bool[]", "string[]", "int[][]", "string[][]"];
const REF_LANGUAGES: PracticeLanguage[] = ["python", "javascript", "java", "cpp"];
const STDIO_LANGUAGES: PracticeLanguage[] = ["python", "javascript", "java", "cpp", "c"];

const EMPTY: ProblemUpsert = {
  slug: "",
  title: "",
  difficulty: "EASY",
  tags: [],
  statement: "",
  constraints: "",
  hints: [],
  judge_mode: "FUNCTION",
  function_spec: { name: "solve", params: [{ name: "nums", type: "int[]" }], return_type: "int" },
  compare_mode: "exact",
  starter_code: {},
  reference_solution: { language: "python", code: "class Solution:\n    def solve(self, nums):\n        return sum(nums)\n" },
  time_limit_ms: 2000,
  memory_limit_mb: 256,
  is_published: false,
  test_cases: [{ input_data: "[1,2,3]", expected_output: "6", is_sample: true, explanation: "" }],
};

const input =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-900 dark:text-white";
const label = "mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500";
const card = "space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800";

function slugify(s: string) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 120);
}

export default function ProblemEditorPage() {
  const params = useParams();
  const router = useRouter();
  const { resolvedTheme } = useTheme();
  const id = String(params?.id || "");
  const isNew = id === "new";

  const [form, setForm] = useState<ProblemUpsert>(EMPTY);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [slugTouched, setSlugTouched] = useState(!isNew);
  const [preview, setPreview] = useState(false);

  useEffect(() => {
    if (isNew) return;
    practiceService
      .adminGet(id)
      .then((p) => {
        setForm({
          slug: p.slug,
          title: p.title,
          difficulty: p.difficulty,
          tags: p.tags,
          statement: p.statement,
          constraints: p.constraints ?? "",
          hints: p.hints,
          judge_mode: p.judge_mode,
          function_spec: p.function_spec,
          compare_mode: p.compare_mode,
          starter_code: p.starter_code ?? {},
          reference_solution: p.reference_solution,
          time_limit_ms: p.time_limit_ms,
          memory_limit_mb: p.memory_limit_mb,
          is_published: p.is_published,
          test_cases: p.test_cases.map(({ input_data, expected_output, is_sample, explanation }) => ({
            input_data,
            expected_output,
            is_sample,
            explanation: explanation ?? "",
          })),
        });
      })
      .catch((e) => toast.error(e?.message || "Failed to load problem."))
      .finally(() => setLoading(false));
  }, [id, isNew]);

  const set = <K extends keyof ProblemUpsert>(key: K, value: ProblemUpsert[K]) => setForm((f) => ({ ...f, [key]: value }));
  const setSpec = (spec: FunctionSpec) => set("function_spec", spec);
  const setCase = (i: number, patch: Partial<TestCaseInput>) =>
    set("test_cases", form.test_cases.map((c, j) => (j === i ? { ...c, ...patch } : c)));

  const save = async (): Promise<string | null> => {
    setSaving(true);
    try {
      const payload: ProblemUpsert = {
        ...form,
        constraints: form.constraints?.trim() ? form.constraints : null,
        function_spec: form.judge_mode === "FUNCTION" ? form.function_spec : null,
        hints: form.hints.filter((h) => h.trim()),
        tags: form.tags.map((t) => t.trim().toLowerCase()).filter(Boolean),
        reference_solution: form.reference_solution?.code.trim() ? form.reference_solution : null,
        starter_code: Object.fromEntries(Object.entries(form.starter_code).filter(([, v]) => v.trim())),
      };
      const saved = isNew ? await practiceService.adminCreate(payload) : await practiceService.adminUpdate(id, payload);
      toast.success("Problem saved.");
      if (isNew) router.replace(`/admin/problems/${saved.id}`);
      return saved.id;
    } catch (e: any) {
      toast.error(e?.message || "Save failed.", { duration: 8000 });
      return null;
    } finally {
      setSaving(false);
    }
  };

  const validate = async () => {
    const savedId = await save();
    if (!savedId) return;
    setValidating(true);
    setReport(null);
    try {
      setReport(await practiceService.adminValidate(savedId));
    } catch (e: any) {
      toast.error(e?.message || "Validation failed.");
    } finally {
      setValidating(false);
    }
  };

  const remove = async () => {
    if (!window.confirm(`Delete "${form.title}" and all of its submissions? This cannot be undone.`)) return;
    try {
      await practiceService.adminDelete(id);
      toast.success("Problem deleted.");
      router.push("/admin/problems");
    } catch (e: any) {
      toast.error(e?.message || "Delete failed.");
    }
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-slate-500">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading…
      </div>
    );
  }

  const spec = form.function_spec;
  const fnMode = form.judge_mode === "FUNCTION";

  return (
    <div className="flex-1 overflow-auto p-6 pb-16 sm:p-8">
      <div className="mx-auto w-full max-w-5xl space-y-6">
        <div className="flex flex-wrap items-center gap-3">
          <Link href="/admin/problems" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900 dark:hover:text-white">
            <ChevronLeft className="h-4 w-4" /> All problems
          </Link>
          <h1 className="flex-1 text-xl font-bold text-slate-900 dark:text-white">{isNew ? "New Problem" : form.title || "Edit Problem"}</h1>
          {!isNew && (
            <button onClick={() => void remove()} className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10">
              <Trash2 className="h-4 w-4" /> Delete
            </button>
          )}
          <button
            onClick={() => void validate()}
            disabled={saving || validating || !form.reference_solution?.code.trim()}
            title={form.reference_solution?.code.trim() ? "Save, then run the reference solution against every test" : "Add a reference solution first"}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
          >
            {validating ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />} Save & Validate
          </button>
          <button
            onClick={() => void save()}
            disabled={saving}
            className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save
          </button>
        </div>

        {report && (
          <div
            className={`rounded-xl border p-4 text-sm ${
              report.ok
                ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200"
                : "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200"
            }`}
          >
            <p className="font-semibold">{report.message}</p>
            {report.failures.map((f) => (
              <div key={f.index} className="mt-2 font-mono text-xs">
                Test {f.index + 1}: expected {f.expected} — reference produced {f.output ?? f.error}
              </div>
            ))}
          </div>
        )}

        {/* Basics */}
        <section className={card}>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={label} htmlFor="title">Title</label>
              <input
                id="title"
                className={input}
                value={form.title}
                onChange={(e) => {
                  set("title", e.target.value);
                  if (!slugTouched) set("slug", slugify(e.target.value));
                }}
              />
            </div>
            <div>
              <label className={label} htmlFor="slug">URL slug</label>
              <input
                id="slug"
                className={`${input} font-mono`}
                value={form.slug}
                onChange={(e) => {
                  setSlugTouched(true);
                  set("slug", slugify(e.target.value));
                }}
              />
            </div>
            <div>
              <label className={label} htmlFor="difficulty">Difficulty</label>
              <select id="difficulty" className={input} value={form.difficulty} onChange={(e) => set("difficulty", e.target.value as Difficulty)}>
                <option value="EASY">Easy</option>
                <option value="MEDIUM">Medium</option>
                <option value="HARD">Hard</option>
              </select>
            </div>
            <div>
              <label className={label} htmlFor="tags">Tags (comma separated)</label>
              <input
                id="tags"
                className={input}
                value={form.tags.join(", ")}
                onChange={(e) => set("tags", e.target.value.split(","))}
                placeholder="array, hash-table"
              />
            </div>
          </div>
          <label className="inline-flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
            <input type="checkbox" checked={form.is_published} onChange={(e) => set("is_published", e.target.checked)} className="h-4 w-4 rounded" />
            Published (visible to students)
          </label>
        </section>

        {/* Statement */}
        <section className={card}>
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-slate-900 dark:text-white">Statement</h2>
            <button onClick={() => setPreview((p) => !p)} className="text-xs font-semibold text-blue-600 hover:underline">
              {preview ? "Edit" : "Preview"}
            </button>
          </div>
          {preview ? (
            <div className="space-y-4 rounded-lg border border-slate-200 p-4 text-sm text-slate-700 dark:border-slate-700 dark:text-slate-300">
              <Markdown source={form.statement || "_Nothing yet_"} />
              {form.constraints && <Markdown source={form.constraints} />}
            </div>
          ) : (
            <>
              <div>
                <label className={label} htmlFor="statement">Description (Markdown: **bold**, `code`, - lists)</label>
                <textarea id="statement" rows={8} className={`${input} font-mono`} value={form.statement} onChange={(e) => set("statement", e.target.value)} />
              </div>
              <div>
                <label className={label} htmlFor="constraints">Constraints</label>
                <textarea id="constraints" rows={3} className={`${input} font-mono`} value={form.constraints ?? ""} onChange={(e) => set("constraints", e.target.value)} />
              </div>
            </>
          )}
          <div>
            <label className={label}>Hints (revealed one at a time)</label>
            <div className="space-y-2">
              {form.hints.map((h, i) => (
                <div key={i} className="flex gap-2">
                  <input className={input} value={h} onChange={(e) => set("hints", form.hints.map((x, j) => (j === i ? e.target.value : x)))} />
                  <button onClick={() => set("hints", form.hints.filter((_, j) => j !== i))} className="rounded-lg p-2 text-slate-400 hover:text-rose-600" aria-label="Remove hint">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
              <button onClick={() => set("hints", [...form.hints, ""])} className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:underline">
                <Plus className="h-4 w-4" /> Add hint
              </button>
            </div>
          </div>
        </section>

        {/* Judging */}
        <section className={card}>
          <h2 className="font-semibold text-slate-900 dark:text-white">Judging</h2>
          <div className="grid gap-4 sm:grid-cols-4">
            <div className="sm:col-span-2">
              <label className={label} htmlFor="mode">Answer style</label>
              <select id="mode" className={input} value={form.judge_mode} onChange={(e) => set("judge_mode", e.target.value as ProblemUpsert["judge_mode"])}>
                <option value="FUNCTION">LeetCode style — implement a method on class Solution</option>
                <option value="STDIO">Input/output — read stdin, print to stdout</option>
              </select>
            </div>
            <div>
              <label className={label} htmlFor="tl">Time limit / test (ms)</label>
              <input id="tl" type="number" min={100} max={10000} className={input} value={form.time_limit_ms} onChange={(e) => set("time_limit_ms", Number(e.target.value))} />
            </div>
            <div>
              <label className={label} htmlFor="ml">Memory (MB)</label>
              <input id="ml" type="number" min={32} max={512} className={input} value={form.memory_limit_mb} onChange={(e) => set("memory_limit_mb", Number(e.target.value))} />
            </div>
          </div>

          {fnMode && spec && (
            <div className="space-y-3 rounded-xl bg-slate-50 p-4 dark:bg-slate-900/50">
              <div className="grid gap-3 sm:grid-cols-3">
                <div>
                  <label className={label} htmlFor="fname">Method name</label>
                  <input id="fname" className={`${input} font-mono`} value={spec.name} onChange={(e) => setSpec({ ...spec, name: e.target.value })} />
                </div>
                <div>
                  <label className={label} htmlFor="ret">Return type</label>
                  <select id="ret" className={input} value={spec.return_type} onChange={(e) => setSpec({ ...spec, return_type: e.target.value })}>
                    {TYPES.map((t) => <option key={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className={label} htmlFor="cmp">Compare output</label>
                  <select id="cmp" className={input} value={form.compare_mode} onChange={(e) => set("compare_mode", e.target.value as ProblemUpsert["compare_mode"])}>
                    <option value="exact">Exactly</option>
                    <option value="unordered">List in any order</option>
                    <option value="float">Numbers within 1e-5</option>
                  </select>
                </div>
              </div>
              <div>
                <label className={label}>Parameters</label>
                <div className="space-y-2">
                  {spec.params.map((p, i) => (
                    <div key={i} className="flex gap-2">
                      <input
                        className={`${input} font-mono`}
                        value={p.name}
                        aria-label={`Parameter ${i + 1} name`}
                        onChange={(e) => setSpec({ ...spec, params: spec.params.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)) })}
                      />
                      <select
                        className={input}
                        value={p.type}
                        aria-label={`Parameter ${i + 1} type`}
                        onChange={(e) => setSpec({ ...spec, params: spec.params.map((x, j) => (j === i ? { ...x, type: e.target.value } : x)) })}
                      >
                        {TYPES.map((t) => <option key={t}>{t}</option>)}
                      </select>
                      <button
                        onClick={() => setSpec({ ...spec, params: spec.params.filter((_, j) => j !== i) })}
                        disabled={spec.params.length === 1}
                        className="rounded-lg p-2 text-slate-400 hover:text-rose-600 disabled:opacity-30"
                        aria-label="Remove parameter"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                  <button
                    onClick={() => setSpec({ ...spec, params: [...spec.params, { name: `arg${spec.params.length + 1}`, type: "int" }] })}
                    className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:underline"
                  >
                    <Plus className="h-4 w-4" /> Add parameter
                  </button>
                </div>
              </div>
              <p className="text-xs text-slate-500">Starter code for Python, JavaScript, Java and C++ is generated from this signature.</p>
            </div>
          )}

          {!fnMode && (
            <div className="space-y-3">
              <p className="text-xs text-slate-500">Optional starter code per language (stdin inputs are limited to 128 KB per test).</p>
              {STDIO_LANGUAGES.map((l) => (
                <div key={l}>
                  <label className={label}>{LANGUAGE_LABELS[l]} starter</label>
                  <textarea
                    rows={4}
                    className={`${input} font-mono`}
                    value={form.starter_code[l] ?? ""}
                    onChange={(e) => set("starter_code", { ...form.starter_code, [l]: e.target.value })}
                  />
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Reference solution */}
        <section className={card}>
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="font-semibold text-slate-900 dark:text-white">Reference solution</h2>
              <p className="text-xs text-slate-500">Never shown to students. Used by “Validate” and to compute expected output for students’ custom inputs.</p>
            </div>
            <select
              aria-label="Reference language"
              className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white"
              value={form.reference_solution?.language ?? "python"}
              onChange={(e) => set("reference_solution", { language: e.target.value, code: form.reference_solution?.code ?? "" })}
            >
              {(fnMode ? REF_LANGUAGES : STDIO_LANGUAGES).map((l) => <option key={l} value={l}>{LANGUAGE_LABELS[l]}</option>)}
            </select>
          </div>
          <div className="h-64 overflow-hidden rounded-lg border border-slate-200 dark:border-slate-700">
            <Editor
              height="100%"
              language={MONACO_LANGUAGE[(form.reference_solution?.language as PracticeLanguage) ?? "python"]}
              theme={resolvedTheme === "dark" ? "vs-dark" : "light"}
              value={form.reference_solution?.code ?? ""}
              onChange={(v) => set("reference_solution", { language: form.reference_solution?.language ?? "python", code: v ?? "" })}
              options={{ fontSize: 13, minimap: { enabled: false }, scrollBeyondLastLine: false, automaticLayout: true }}
            />
          </div>
        </section>

        {/* Test cases */}
        <section className={card}>
          <div>
            <h2 className="font-semibold text-slate-900 dark:text-white">Test cases ({form.test_cases.length})</h2>
            <p className="text-xs text-slate-500">
              {fnMode
                ? `Input: one JSON value per line, in parameter order (${spec?.params.map((p) => p.name).join(", ")}). Expected output: one JSON value.`
                : "Input: exact stdin. Expected output: exact stdout (trailing whitespace ignored)."}{" "}
              Sample cases are shown to students as examples; the rest are hidden.
            </p>
          </div>
          {form.test_cases.map((tc, i) => (
            <div key={i} className="space-y-2 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">Test {i + 1}</span>
                <div className="flex items-center gap-3">
                  <label className="inline-flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300">
                    <input type="checkbox" checked={tc.is_sample} onChange={(e) => setCase(i, { is_sample: e.target.checked })} /> Sample (visible)
                  </label>
                  <button onClick={() => set("test_cases", form.test_cases.filter((_, j) => j !== i))} className="text-slate-400 hover:text-rose-600" aria-label={`Remove test ${i + 1}`}>
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <textarea rows={3} aria-label={`Test ${i + 1} input`} placeholder="Input" className={`${input} font-mono text-xs`} value={tc.input_data} onChange={(e) => setCase(i, { input_data: e.target.value })} />
                <textarea rows={3} aria-label={`Test ${i + 1} expected output`} placeholder="Expected output" className={`${input} font-mono text-xs`} value={tc.expected_output} onChange={(e) => setCase(i, { expected_output: e.target.value })} />
              </div>
              {tc.is_sample && (
                <input placeholder="Explanation shown with the example (optional)" className={input} value={tc.explanation ?? ""} onChange={(e) => setCase(i, { explanation: e.target.value })} />
              )}
            </div>
          ))}
          <button
            onClick={() => set("test_cases", [...form.test_cases, { input_data: "", expected_output: "", is_sample: false, explanation: "" }])}
            className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:underline"
          >
            <Plus className="h-4 w-4" /> Add test case
          </button>
        </section>
      </div>
    </div>
  );
}
