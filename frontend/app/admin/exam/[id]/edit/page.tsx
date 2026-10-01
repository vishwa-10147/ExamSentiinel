"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/services/apiClient";

type FormData = { title: string; description: string; duration_minutes: number; start_window: string; end_window: string; late_entry_minutes: number };

const toInputDate = (value: string) => {
  const date = new Date(value);
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60000).toISOString().slice(0, 16);
};

export default function EditExamPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [form, setForm] = useState<FormData>({ title: "", description: "", duration_minutes: 60, start_window: "", end_window: "", late_entry_minutes: 15 });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    apiClient.get<any>(`/api/exams/${id}`).then((exam) => setForm({
      title: exam.title,
      description: exam.description || "",
      duration_minutes: exam.duration_minutes,
      start_window: toInputDate(exam.start_window),
      end_window: toInputDate(exam.end_window),
      late_entry_minutes: exam.late_entry_minutes,
    })).catch((err) => setError(err instanceof Error ? err.message : "Failed to load exam.")).finally(() => setLoading(false));
  }, [id]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    if (new Date(form.start_window) >= new Date(form.end_window)) {
      setError("End window must be later than the start window.");
      return;
    }
    setSaving(true);
    try {
      await apiClient.put(`/api/exams/${id}`, { ...form, start_window: new Date(form.start_window).toISOString(), end_window: new Date(form.end_window).toISOString() });
      router.push(`/admin/exam/${id}/manage`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update exam.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <main className="p-6 text-slate-500">Loading exam...</main>;

  return (
    <main className="mx-auto w-full max-w-3xl p-4 sm:p-6 lg:p-8">
      <button onClick={() => router.push(`/admin/exam/${id}/manage`)} className="mb-6 text-sm font-medium text-blue-600">← Back to exam</button>
      <form onSubmit={submit} className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold text-slate-900">Edit Exam Details</h1>
        {error && <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        <label className="block text-sm font-medium text-slate-700">Title<input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 p-2.5" /></label>
        <label className="block text-sm font-medium text-slate-700">Description<textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 p-2.5" rows={4} /></label>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="text-sm font-medium text-slate-700">Duration (minutes)<input type="number" min={1} required value={form.duration_minutes} onChange={(e) => setForm({ ...form, duration_minutes: Number(e.target.value) })} className="mt-1 w-full rounded-lg border border-slate-300 p-2.5" /></label>
          <label className="text-sm font-medium text-slate-700">Late entry (minutes)<input type="number" min={0} required value={form.late_entry_minutes} onChange={(e) => setForm({ ...form, late_entry_minutes: Number(e.target.value) })} className="mt-1 w-full rounded-lg border border-slate-300 p-2.5" /></label>
          <label className="text-sm font-medium text-slate-700">Start window<input type="datetime-local" required value={form.start_window} onChange={(e) => setForm({ ...form, start_window: e.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 p-2.5" /></label>
          <label className="text-sm font-medium text-slate-700">End window<input type="datetime-local" required value={form.end_window} onChange={(e) => setForm({ ...form, end_window: e.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 p-2.5" /></label>
        </div>
        <button disabled={saving} className="rounded-lg bg-blue-600 px-5 py-2.5 font-semibold text-white disabled:opacity-50">{saving ? "Saving..." : "Save Changes"}</button>
      </form>
    </main>
  );
}
