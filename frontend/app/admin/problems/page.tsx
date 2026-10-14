"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import { Code2, Eye, Loader2, Pencil, Plus, Search, ShieldCheck } from "lucide-react";
import { ProblemAdminListItem, practiceService } from "@/services/practiceService";
import { DifficultyBadge } from "@/components/practice/badges";

export default function AdminProblemsPage() {
  const [items, setItems] = useState<ProblemAdminListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [validating, setValidating] = useState<string | null>(null);

  const load = async () => {
    try {
      setItems(await practiceService.adminList());
    } catch (e: any) {
      toast.error(e?.message || "Failed to load problems.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return items.filter((p) => !q || p.title.toLowerCase().includes(q) || p.slug.includes(q) || p.tags.some((t) => t.includes(q)));
  }, [items, search]);

  const validate = async (p: ProblemAdminListItem) => {
    setValidating(p.id);
    try {
      const r = await practiceService.adminValidate(p.id);
      if (r.ok) toast.success(`${p.title}: ${r.message}`);
      else toast.error(`${p.title}: ${r.message}`, { duration: 8000 });
    } catch (e: any) {
      toast.error(e?.message || "Validation failed.");
    } finally {
      setValidating(null);
    }
  };

  const published = items.filter((p) => p.is_published).length;

  return (
    <div className="flex-1 overflow-auto p-6 pb-12 sm:p-8">
      <div className="mx-auto w-full max-w-7xl space-y-6">
        <div className="flex flex-col justify-between gap-4 border-b border-slate-200 pb-5 dark:border-slate-700 sm:flex-row sm:items-end">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-900 dark:text-white">
              <Code2 className="h-7 w-7 text-blue-600" /> Practice Problems
            </h1>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {items.length} problems · {published} published. Students practise these in the Problem Set; practice never affects exam results.
            </p>
          </div>
          <Link
            href="/admin/problems/new"
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" /> New Problem
          </Link>
        </div>

        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by title, slug or tag"
            aria-label="Search problems"
            className="w-full rounded-xl border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
          />
        </div>

        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-800">
          <table className="w-full min-w-[760px] text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900/50">
              <tr>
                <th className="px-4 py-3">Problem</th>
                <th className="px-4 py-3">Difficulty</th>
                <th className="px-4 py-3">Tests</th>
                <th className="px-4 py-3 text-right">Submissions</th>
                <th className="px-4 py-3 text-right">Acceptance</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
              {loading && (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-slate-500">
                    <Loader2 className="mx-auto h-5 w-5 animate-spin" />
                  </td>
                </tr>
              )}
              {!loading && filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-slate-500">No problems found.</td>
                </tr>
              )}
              {filtered.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/40">
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900 dark:text-white">{p.title}</div>
                    <div className="font-mono text-xs text-slate-400">{p.slug}</div>
                  </td>
                  <td className="px-4 py-3"><DifficultyBadge difficulty={p.difficulty} /></td>
                  <td className="px-4 py-3 tabular-nums text-slate-600 dark:text-slate-300">
                    {p.test_case_count} <span className="text-xs text-slate-400">({p.sample_count} sample)</span>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">{p.submissions}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{p.acceptance_rate != null ? `${p.acceptance_rate}%` : "—"}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                        p.is_published
                          ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300"
                          : "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300"
                      }`}
                    >
                      {p.is_published ? "Published" : "Draft"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-1">
                      <button
                        onClick={() => void validate(p)}
                        disabled={validating === p.id}
                        title="Run the reference solution against every test"
                        className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-emerald-600 disabled:opacity-50 dark:hover:bg-slate-700"
                      >
                        {validating === p.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
                      </button>
                      <Link
                        href={`/candidate/problems/${p.slug}`}
                        title="Open as a student"
                        className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-blue-600 dark:hover:bg-slate-700"
                      >
                        <Eye className="h-4 w-4" />
                      </Link>
                      <Link
                        href={`/admin/problems/${p.id}`}
                        title="Edit"
                        className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-blue-600 dark:hover:bg-slate-700"
                      >
                        <Pencil className="h-4 w-4" />
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
