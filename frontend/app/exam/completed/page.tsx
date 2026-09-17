"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { CheckCircle, Shield, Award } from "lucide-react";

export default function ExamCompletedPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center p-6 text-center">
      <div className="w-20 h-20 bg-emerald-500/20 rounded-full flex items-center justify-center mb-6">
        <CheckCircle className="w-10 h-10 text-emerald-500" />
      </div>
      
      <h1 className="text-3xl font-bold text-white mb-3">Exam Submitted Successfully</h1>
      <p className="text-slate-400 max-w-md mx-auto mb-10">
        Your examination responses and proctoring telemetry have been securely transmitted to your institution's review center.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl w-full mb-10">
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 flex items-start gap-4 text-left">
          <div className="w-10 h-10 bg-indigo-500/20 rounded-lg flex items-center justify-center shrink-0">
            <Shield className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <h3 className="font-semibold text-white mb-1">Integrity Lock Disengaged</h3>
            <p className="text-sm text-slate-400">Webcam monitoring and browser lock have been successfully deactivated.</p>
          </div>
        </div>

        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 flex items-start gap-4 text-left">
          <div className="w-10 h-10 bg-amber-500/20 rounded-lg flex items-center justify-center shrink-0">
            <Award className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <h3 className="font-semibold text-white mb-1">Results Pending</h3>
            <p className="text-sm text-slate-400">Your final score will be available on your dashboard once the review period ends.</p>
          </div>
        </div>
      </div>

      <button 
        onClick={() => router.push("/admin/exam")}
        className="px-8 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-semibold transition-colors"
      >
        Return to Dashboard
      </button>
    </div>
  );
}
