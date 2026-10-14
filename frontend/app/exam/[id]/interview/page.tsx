"use client";
export const dynamic = "force-dynamic";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { examService } from "@/services/examService";
import { interviewService } from "@/services/interviewService";

/** Candidate entry point: find (or create) the interview for this exam, then open its room. */
export default function ExamInterviewEntry() {
  const params = useParams();
  const router = useRouter();
  const examId = String(params?.id || "");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!examId) return;
    (async () => {
      try {
        const session = await examService.startSession(examId);
        const interview = await interviewService.create(session.session_id);
        router.replace(`/interview/${interview.id}`);
      } catch (e: any) {
        setError(e?.message || "Could not open the interview.");
      }
    })();
  }, [examId, router]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-slate-950 p-6 text-center text-slate-300">
      {error ? (
        <>
          <p className="text-rose-300">{error}</p>
          <button onClick={() => router.push("/candidate/exams")} className="text-sm font-semibold text-indigo-300 hover:underline">
            Back to my exams
          </button>
        </>
      ) : (
        <>
          <Loader2 className="h-6 w-6 animate-spin" /> Preparing your interview room…
        </>
      )}
    </div>
  );
}
