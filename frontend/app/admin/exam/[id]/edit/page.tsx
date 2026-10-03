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

const calculateRecommendedEndWindow = (startStr: string, durationMins: number, lateMins: number): string => {
  if (!startStr) return "";
  const startDate = new Date(startStr);
  if (isNaN(startDate.getTime())) return "";
  const totalMinutes = (durationMins || 0) + (lateMins || 0);
  const endDate = new Date(startDate.getTime() + totalMinutes * 60000);
  const offset = endDate.getTimezoneOffset();
  return new Date(endDate.getTime() - offset * 60000).toISOString().slice(0, 16);
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
    const startMs = new Date(form.start_window).getTime();
    const endMs = new Date(form.end_window).getTime();
    const lateCutoffMs = startMs + (form.late_entry_minutes || 0) * 60000;

    if (endMs <= startMs) {
      setError("End window must be later than the start window.");
      return;
    }
    if (endMs < lateCutoffMs) {
      setError(`End window cannot be earlier than the Late Entry Cutoff (${new Date(lateCutoffMs).toLocaleTimeString()}). Candidates would not be able to enter!`);
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
        <div>
          <label htmlFor="title" className="block text-sm font-medium text-slate-700">Title</label>
          <input id="title" name="title" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 p-2.5" />
        </div>
        <div>
          <label htmlFor="description" className="block text-sm font-medium text-slate-700">Description</label>
          <textarea id="description" name="description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 p-2.5" rows={4} />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="duration_minutes" className="text-sm font-medium text-slate-700">Duration (minutes)</label>
            <input id="duration_minutes" name="duration_minutes" type="number" min={1} required value={form.duration_minutes} onChange={(e) => setForm({ ...form, duration_minutes: Number(e.target.value) })} className="mt-1 w-full rounded-lg border border-slate-300 p-2.5" />
          </div>
          <div>
            <label htmlFor="late_entry_minutes" className="text-sm font-medium text-slate-700">Late entry (minutes)</label>
            <input id="late_entry_minutes" name="late_entry_minutes" type="number" min={0} required value={form.late_entry_minutes} onChange={(e) => setForm({ ...form, late_entry_minutes: Number(e.target.value) })} className="mt-1 w-full rounded-lg border border-slate-300 p-2.5" />
          </div>
          <div>
            <label htmlFor="start_window" className="text-sm font-medium text-slate-700">Start window</label>
            <input id="start_window" name="start_window" type="datetime-local" required value={form.start_window} onChange={(e) => {
              const val = e.target.value;
              setForm((prev) => {
                const updated = { ...prev, start_window: val };
                if (val && (!prev.end_window || prev.end_window === calculateRecommendedEndWindow(prev.start_window, prev.duration_minutes, prev.late_entry_minutes))) {
                  updated.end_window = calculateRecommendedEndWindow(val, prev.duration_minutes, prev.late_entry_minutes);
                }
                return updated;
              });
            }} className="mt-1 w-full rounded-lg border border-slate-300 p-2.5" />
          </div>
          <div>
            <div className="flex items-center justify-between">
              <label htmlFor="end_window" className="text-sm font-medium text-slate-700">End window</label>
              {form.start_window && (
                <button
                  type="button"
                  onClick={() => {
                    const autoEnd = calculateRecommendedEndWindow(form.start_window, form.duration_minutes, form.late_entry_minutes);
                    if (autoEnd) setForm(prev => ({ ...prev, end_window: autoEnd }));
                  }}
                  className="text-[11px] font-bold text-blue-600 hover:underline"
                >
                  ⚡ Auto-Set (Start + Duration + Late Entry)
                </button>
              )}
            </div>
            <input id="end_window" name="end_window" type="datetime-local" required value={form.end_window} onChange={(e) => setForm({ ...form, end_window: e.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 p-2.5" />
          </div>
          {form.start_window && (
            <div className="sm:col-span-2 p-3.5 rounded-xl bg-blue-50/70 border border-blue-200 text-xs text-blue-900 space-y-1">
              <div className="font-bold">🗓️ Calculated Timing Breakdown:</div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-0.5">
                <div>Start Window: <strong>{new Date(form.start_window).toLocaleString()}</strong></div>
                <div>Late Entry Cutoff: <strong>{new Date(new Date(form.start_window).getTime() + (form.late_entry_minutes || 0) * 60000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong></div>
                <div>Recommended End Window: <strong>{new Date(new Date(form.start_window).getTime() + ((form.duration_minutes || 0) + (form.late_entry_minutes || 0)) * 60000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong></div>
              </div>
            </div>
          )}
        </div>
        <button disabled={saving} className="rounded-lg bg-blue-600 px-5 py-2.5 font-semibold text-white disabled:opacity-50">{saving ? "Saving..." : "Save Changes"}</button>
      </form>
    </main>
  );
}
