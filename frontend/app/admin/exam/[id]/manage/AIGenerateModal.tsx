"use client";

import React, { useState } from "react";
import { X, Sparkles, Loader2, AlertCircle } from "lucide-react";
import { apiClient } from "@/services/apiClient";

export default function AIGenerateModal({
  examId,
  onClose,
  onSuccess
}: {
  examId: string;
  onClose: () => void;
  onSuccess: (count: number) => void;
}) {
  const [syllabus, setSyllabus] = useState("");
  const [questionCount, setQuestionCount] = useState(5);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!syllabus.trim()) {
      setError("Please provide a syllabus or topic list.");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    
    try {
      const payload = {
        syllabus_text: syllabus,
        question_count: questionCount
      };
      const res = await apiClient.post<{ count: number }>(`/api/exams/${examId}/generate-ai`, payload);
      onSuccess(res?.count || questionCount);
    } catch (err: any) {
      setError(err?.message || "Failed to generate questions. Ensure OpenAI API Key is configured on the backend.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-0">
      <div className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm" onClick={!isSubmitting ? onClose : undefined} />
      
      <div className="relative bg-white dark:bg-slate-800 dark:border-slate-700 rounded-2xl shadow-xl w-full max-w-xl max-h-[90vh] overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50 dark:bg-slate-900/50">
          <div className="flex items-center gap-2 text-slate-800 dark:text-slate-100">
            <Sparkles className="w-5 h-5 text-indigo-500" />
            <h2 className="text-lg font-bold">Generate with AI</h2>
          </div>
          <button 
            onClick={onClose}
            disabled={isSubmitting}
            className="text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:text-slate-300 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 flex flex-col gap-6 overflow-y-auto">
          {error && (
            <div className="bg-red-50 text-red-600 p-3 rounded-lg flex items-start text-sm border border-red-100">
              <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2">
              Syllabus / Source Text
            </label>
            <p className="text-xs text-slate-500 dark:text-slate-400 dark:text-slate-500 mb-2">Paste lecture notes, syllabus, or raw text to generate questions from.</p>
            <textarea
              value={syllabus}
              onChange={(e) => setSyllabus(e.target.value)}
              rows={8}
              className="w-full px-3 py-2 bg-white dark:bg-slate-800 dark:border-slate-700 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-shadow resize-y"
              placeholder="e.g. Introduction to Data Structures: Arrays, Linked Lists, Trees..."
              disabled={isSubmitting}
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2">
              Number of Questions
            </label>
            <input
              type="number"
              min={1}
              max={20}
              value={questionCount}
              onChange={(e) => setQuestionCount(parseInt(e.target.value) || 1)}
              className="w-full sm:w-1/3 px-3 py-2 bg-white dark:bg-slate-800 dark:border-slate-700 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-shadow"
              disabled={isSubmitting}
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:text-white hover:bg-slate-50 dark:bg-slate-900 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center gap-2 px-6 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 rounded-lg transition-colors disabled:opacity-70"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Generate AI Questions
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
