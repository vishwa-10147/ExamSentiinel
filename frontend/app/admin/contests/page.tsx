"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import { ArrowDown, ArrowUp, Eye, Loader2, Pencil, Plus, Timer, Trash2, Users, X } from "lucide-react";
import { DifficultyBadge } from "@/components/practice/badges";
import { PhaseBadge, formatWhen } from "@/components/contests/PhaseBadge";
import { ProblemAdminListItem, practiceService } from "@/services/practiceService";
import { ContestAdmin, ContestUpsert, contestService, formatDuration } from "@/services/contestService";

interface FormState {
  id: string | null;
  slug: string;
  title: string;
  description: string;
  startsLocal: string; // <input type="datetime-local"> value
  duration: number;
  penalty: number;
  published: boolean;
  problems: { problem_id: string; points: number }[];
}

const INPUT =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-900 dark:text-white";
const LABEL = "mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400";

function toLocalInput(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function blankForm(): FormState {
  const start = new Date(Date.now() + 24 * 3600 * 1000);
  start.setMinutes(0, 0, 0);
  return {
    id: null, slug: "", title: "", description: "", startsLocal: toLocalInput(start.toISOString()),
    duration: 90, penalty: 5, published: false, problems: [],
  };
}

function slugify(title: string): string {
  return title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 120);
}

export default function AdminContestsPage() {
  const [contests, setContests] = useState<ContestAdmin[] | null>(null);
  const [bank, setBank] = useState<ProblemAdminListItem[]>([]);
  const [form, setForm] = useState<FormState | null>(null);
  const [saving, setSaving] = useState(false);
  const [pick, setPick] = useState("");

  const load = useCallback(async () => {
    try {
      setContests(await contestService.adminList());
    } catch (e: any) {
      toast.error(e?.message || "Failed to load contests.");
      setContests([]);
    }
  }, []);

  useEffect(() => {
    void load();
    practiceService.adminList().then(setBank).catch(() => undefined);
  }, [load]);

  const byId = useMemo(() => new Map(bank.map((p) => [p.id, p])), [bank]);
  const started = form?.id ? contests?.find((c) => c.id === form.id)?.phase !== "upcoming" : false;

  const edit = (c: ContestAdmin) =>
    setForm({
      id: c.id, slug: c.slug, title: c.title, description: c.description, startsLocal: toLocalInput(c.starts_at),
      duration: c.duration_minutes, penalty: c.penalty_minutes, published: c.is_published,
      problems: c.problems.map((p) => ({ problem_id: p.problem_id, points: p.points })),
    });

  const update = (patch: Partial<FormState>) => setForm((f) => (f ? { ...f, ...patch } : f));
  const move = (i: number, delta: number) => {
    if (!form) return;
    const next = [...form.problems];
    const [row] = next.splice(i, 1);
    next.splice(i + delta, 0, row);
    update({ problems: next });
  };

  const save = async () => {
    if (!form) return;
    const payload: ContestUpsert = {
      slug: form.slug, title: form.title, description: form.description,
      starts_at: new Date(form.startsLocal).toISOString(), duration_minutes: form.duration,
      penalty_minutes: form.penalty, is_published: form.published, problems: form.problems,
    };
    setSaving(true);
    try {
      if (form.id) await contestService.update(form.id, payload);
      else await contestService.create(payload);
      toast.success(form.id ? "Contest updated." : "Contest created.");
      setForm(null);
      await load();
    } catch (e: any) {
      toast.error(e?.message || "Could not save the contest.");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (c: ContestAdmin) => {
    if (!window.confirm(`Delete "${c.title}"? Its registrations are removed; submissions stay in practice history.`)) return;
    try {
      await contestService.remove(c.id);
      toast.success("Contest deleted.");
      await load();
    } catch (e: any) {
      toast.error(e?.message || "Could not delete the contest.");
    }
  };

  return (
    <div className="flex-1 overflow-auto p-6 pb-12 sm:p-8">
      <div className="mx-auto w-full max-w-6xl space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-4 border-b border-slate-200 pb-5 dark:border-slate-700">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-900 dark:text-white">
              <Timer className="h-7 w-7 text-blue-600 dark:text-blue-400" /> Contests
            </h1>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Schedule timed contests from the practice bank. While a published contest has not ended, its problems are hidden from practice.
            </p>
          </div>
          {!form && (
            <button
              onClick={() => setForm(blankForm())}
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" /> New contest
            </button>
          )}
        </div>

        {form && (
          <div className="space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-800">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">{form.id ? "Edit contest" : "New contest"}</h2>
              <button onClick={() => setForm(null)} aria-label="Close" className="rounded-lg p-1 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700">
                <X className="h-5 w-5" />
              </button>
            </div>
            {started && (
              <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
                This contest has started: problems, points, timing and penalty are fixed. You can still edit the title, description and visibility.
              </p>
            )}
            <div className="grid gap-4 sm:grid-cols-2">
              <label>
                <span className={LABEL}>Title</span>
                <input
                  className={INPUT}
                  value={form.title}
                  onChange={(e) => update({ title: e.target.value, ...(form.id ? {} : { slug: slugify(e.target.value) }) })}
                  placeholder="Weekly Contest 1"
                />
              </label>
              <label>
                <span className={LABEL}>Slug</span>
                <input className={INPUT} value={form.slug} onChange={(e) => update({ slug: e.target.value })} placeholder="weekly-contest-1" />
              </label>
              <label>
                <span className={LABEL}>Starts at (your local time)</span>
                <input type="datetime-local" className={INPUT} value={form.startsLocal} disabled={started} onChange={(e) => update({ startsLocal: e.target.value })} />
              </label>
              <div className="grid grid-cols-2 gap-4">
                <label>
                  <span className={LABEL}>Duration (min)</span>
                  <input type="number" min={5} className={INPUT} value={form.duration} disabled={started} onChange={(e) => update({ duration: Number(e.target.value) })} />
                </label>
                <label>
                  <span className={LABEL}>Penalty (min)</span>
                  <input type="number" min={0} max={60} className={INPUT} value={form.penalty} disabled={started} onChange={(e) => update({ penalty: Number(e.target.value) })} />
                </label>
              </div>
            </div>
            <label className="block">
              <span className={LABEL}>Description (Markdown)</span>
              <textarea className={`${INPUT} min-h-[90px]`} value={form.description} onChange={(e) => update({ description: e.target.value })} />
            </label>

            <div className="space-y-2">
              <span className={LABEL}>Problems</span>
              {form.problems.length === 0 && <p className="text-sm text-slate-500 dark:text-slate-400">Add at least one problem.</p>}
              <ol className="space-y-2">
                {form.problems.map((row, i) => {
                  const p = byId.get(row.problem_id);
                  return (
                    <li key={row.problem_id} className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700">
                      <span className="w-6 font-semibold text-slate-700 dark:text-slate-200">{String.fromCharCode(65 + i)}</span>
                      <span className="min-w-0 flex-1 truncate text-sm text-slate-900 dark:text-white">
                        {p ? `${p.number != null ? `#${p.number} ` : ""}${p.title}` : row.problem_id}
                      </span>
                      {p && <DifficultyBadge difficulty={p.difficulty} />}
                      {p && !p.is_published && <span className="text-xs text-slate-500 dark:text-slate-400">contest-only</span>}
                      <label className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                        Points
                        <input
                          type="number"
                          min={1}
                          className={`${INPUT} w-24 py-1`}
                          value={row.points}
                          disabled={started}
                          onChange={(e) => update({ problems: form.problems.map((r, j) => (j === i ? { ...r, points: Number(e.target.value) } : r)) })}
                        />
                      </label>
                      <div className="flex gap-1">
                        <button disabled={started || i === 0} onClick={() => move(i, -1)} aria-label="Move up" className="rounded p-1 text-slate-500 hover:bg-slate-100 disabled:opacity-30 dark:text-slate-400 dark:hover:bg-slate-700"><ArrowUp className="h-4 w-4" /></button>
                        <button disabled={started || i === form.problems.length - 1} onClick={() => move(i, 1)} aria-label="Move down" className="rounded p-1 text-slate-500 hover:bg-slate-100 disabled:opacity-30 dark:text-slate-400 dark:hover:bg-slate-700"><ArrowDown className="h-4 w-4" /></button>
                        <button disabled={started} onClick={() => update({ problems: form.problems.filter((_, j) => j !== i) })} aria-label="Remove" className="rounded p-1 text-rose-500 hover:bg-rose-50 disabled:opacity-30 dark:hover:bg-rose-500/10"><Trash2 className="h-4 w-4" /></button>
                      </div>
                    </li>
                  );
                })}
              </ol>
              {!started && form.problems.length < 26 && (
                <div className="flex flex-wrap gap-2">
                  <select className={`${INPUT} max-w-md flex-1`} value={pick} onChange={(e) => setPick(e.target.value)} aria-label="Problem to add">
                    <option value="">Choose a problem…</option>
                    {bank
                      .filter((p) => !form.problems.some((r) => r.problem_id === p.id))
                      .map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.number != null ? `#${p.number} ` : ""}{p.title} ({p.difficulty.toLowerCase()}{p.is_published ? "" : ", unpublished"})
                        </option>
                      ))}
                  </select>
                  <button
                    disabled={!pick}
                    onClick={() => {
                      const p = byId.get(pick);
                      const points = p?.difficulty === "HARD" ? 300 : p?.difficulty === "MEDIUM" ? 200 : 100;
                      update({ problems: [...form.problems, { problem_id: pick, points }] });
                      setPick("");
                    }}
                    className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
                  >
                    <Plus className="h-4 w-4" /> Add
                  </button>
                </div>
              )}
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4 dark:border-slate-700">
              <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
                <input type="checkbox" checked={form.published} onChange={(e) => update({ published: e.target.checked })} />
                Published (visible to students)
              </label>
              <div className="flex gap-2">
                <button onClick={() => setForm(null)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700">
                  Cancel
                </button>
                <button
                  onClick={() => void save()}
                  disabled={saving || !form.title || !form.slug || form.problems.length === 0}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
                >
                  {saving && <Loader2 className="h-4 w-4 animate-spin" />} Save contest
                </button>
              </div>
            </div>
          </div>
        )}

        {!contests ? (
          <div className="flex items-center justify-center py-16 text-slate-500 dark:text-slate-400">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading…
          </div>
        ) : contests.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 p-10 text-center text-slate-500 dark:border-slate-600 dark:text-slate-400">
            No contests yet. Create one from problems in the practice bank.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
            <table className="w-full text-sm" aria-label="Contests">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900/40 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-3">Contest</th>
                  <th className="px-4 py-3">Starts</th>
                  <th className="px-4 py-3">Length</th>
                  <th className="px-4 py-3">Problems</th>
                  <th className="px-4 py-3">Participants</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                {contests.map((c) => (
                  <tr key={c.id}>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium text-slate-900 dark:text-white">{c.title}</span>
                        <PhaseBadge phase={c.phase} />
                        {!c.is_published && <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">Draft</span>}
                      </div>
                      <div className="text-xs text-slate-500 dark:text-slate-400">{c.slug}</div>
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{formatWhen(c.starts_at)}</td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{formatDuration(c.duration_minutes)}</td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{c.problems.length}</td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                      <span className="inline-flex items-center gap-1"><Users className="h-4 w-4" /> {c.participants}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-1">
                        <Link href={`/candidate/contests/${c.slug}`} title="Open as a participant" className="rounded p-1.5 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700"><Eye className="h-4 w-4" /></Link>
                        <button onClick={() => edit(c)} title="Edit" className="rounded p-1.5 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700"><Pencil className="h-4 w-4" /></button>
                        <button onClick={() => void remove(c)} title="Delete" className="rounded p-1.5 text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10"><Trash2 className="h-4 w-4" /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
