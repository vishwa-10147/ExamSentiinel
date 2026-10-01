"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/services/apiClient";

export default function CandidateResultDetailPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const router = useRouter();
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    apiClient.get(`/api/reports/my-results/detailed/${sessionId}`)
      .then(setResult)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load result."));
  }, [sessionId]);

  if (error) return <main className="mx-auto max-w-4xl p-6 text-red-600">{error}</main>;
  if (!result) return <main className="mx-auto max-w-4xl p-6 text-slate-500">Loading result...</main>;

  return (
    <main className="mx-auto w-full max-w-4xl space-y-6 p-4 sm:p-6 lg:p-8">
      <button onClick={() => router.push("/candidate/results")} className="text-sm font-medium text-blue-600 hover:text-blue-700">← Back to My Results</button>
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold text-slate-900">Result Details</h1>
        <p className="mt-2 text-slate-600">Score: <strong>{result.total_awarded}</strong> / {result.total_possible}</p>
      </section>
      <section className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50"><tr><th className="px-4 py-3 text-left text-xs uppercase text-slate-500">Question</th><th className="px-4 py-3 text-left text-xs uppercase text-slate-500">Marks</th><th className="px-4 py-3 text-left text-xs uppercase text-slate-500">Status</th></tr></thead>
          <tbody className="divide-y divide-slate-200">
            {result.responses.map((response: any) => (
              <tr key={response.question_id}><td className="px-4 py-3 text-sm text-slate-900">{response.question_title}</td><td className="px-4 py-3 text-sm text-slate-700">{response.marks_awarded ?? 0}</td><td className="px-4 py-3 text-sm">{response.is_correct === true ? "Correct" : response.is_correct === false ? "Incorrect" : "Pending review"}</td></tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
