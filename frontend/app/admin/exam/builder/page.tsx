"use client";
export const dynamic = "force-dynamic";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import {
  ArrowLeft,
  Save,
  CheckCircle2,
  AlertCircle,
  Clock,
  Calendar,
  Layers,
  Sparkles
} from "lucide-react";
import Link from "next/link";
import toast from "react-hot-toast";

interface ExamFormData {
  title: string;
  description: string;
  duration_minutes: number;
  late_entry_minutes: number;
  start_window: string;
  end_window: string;
}

export default function ExamBuilderPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  
  const [formData, setFormData] = useState<ExamFormData>({
    title: "",
    description: "",
    duration_minutes: 60,
    late_entry_minutes: 15,
    start_window: "",
    end_window: "",
  });
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdExamId, setCreatedExamId] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isLoading, isAuthenticated, router]);

  // Protect route
  if (!isLoading && user && !["admin", "proctor"].includes(user.role)) {
    router.push("/dashboard");
    return null;
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: ["duration_minutes", "late_entry_minutes"].includes(name)
        ? parseInt(value) || 0
        : value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    
    if (!formData.title.trim()) {
      setError("Exam Title is required.");
      return;
    }
    if (formData.duration_minutes <= 0) {
      setError("Duration must be greater than 0 minutes.");
      return;
    }
    if (!formData.start_window || !formData.end_window) {
      setError("Both Start Window and End Window are required.");
      return;
    }
    if (new Date(formData.start_window) >= new Date(formData.end_window)) {
      setError("End Window deadline must be later than the Start Window.");
      return;
    }

    try {
      setIsSubmitting(true);
      
      const created = await apiClient.post<{ id: string; title: string }>("/api/exams", formData);
      toast.success("Exam created successfully!");
      setCreatedExamId(created.id);
      
      setTimeout(() => {
        router.push(`/admin/exam/${created.id}/manage`);
      }, 1200);
      
    } catch (err: any) {
      console.error("Exam creation error", err);
      setError(err?.message || "Failed to create examination.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading || !user) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center text-slate-500">Loading Exam Builder...</div>
      </div>
    );
  }

  return (
    <div className="flex-1 w-full p-6 sm:p-8 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-5 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <Link
            href="/admin/exam"
            className="p-2 rounded-lg hover:bg-slate-100 text-slate-500 transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
              <Layers className="h-6 w-6 text-blue-600" />
              New Exam Builder
            </h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Set up parameters, timing windows, and rules for a new examination.
            </p>
          </div>
        </div>
      </div>

      {/* Main Card Form */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <form onSubmit={handleSubmit} className="p-6 sm:p-8 space-y-6">
          {error && (
            <div className="p-4 rounded-xl bg-red-50 border border-red-200 flex items-start gap-3 text-red-700 text-xs sm:text-sm">
              <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
              <p>{error}</p>
            </div>
          )}
          
          {createdExamId && (
            <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex items-start gap-3 text-emerald-700 text-xs sm:text-sm">
              <CheckCircle2 className="h-5 w-5 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-bold">Exam created successfully!</p>
                <p className="text-xs mt-0.5 text-emerald-600">Redirecting to Question & Candidate Management portal...</p>
              </div>
            </div>
          )}

          {/* Title */}
          <div>
            <label htmlFor="title" className="block text-sm font-semibold text-slate-900 mb-1">
              Exam Title <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="title"
              name="title"
              value={formData.title}
              onChange={handleChange}
              placeholder="e.g. Midterm Assessment - Data Structures & Algorithms"
              className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all text-sm"
              required
            />
          </div>

          {/* Description */}
          <div>
            <label htmlFor="description" className="block text-sm font-semibold text-slate-900 mb-1">
              Instructions & Syllabus Overview
            </label>
            <textarea
              id="description"
              name="description"
              value={formData.description}
              onChange={handleChange}
              rows={4}
              placeholder="Provide test instructions, prohibited items, or syllabus coverage for candidates..."
              className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all text-sm resize-y"
            />
          </div>

          {/* Durations */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div>
              <label htmlFor="duration_minutes" className="block text-sm font-semibold text-slate-900 mb-1">
                Duration (Minutes) <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <Clock className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
                <input
                  type="number"
                  id="duration_minutes"
                  name="duration_minutes"
                  value={formData.duration_minutes}
                  onChange={handleChange}
                  min="1"
                  className="w-full pl-9 pr-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                  required
                />
              </div>
              <p className="text-xs text-slate-500 mt-1">Total time allotted to candidate once session begins.</p>
            </div>

            <div>
              <label htmlFor="late_entry_minutes" className="block text-sm font-semibold text-slate-900 mb-1">
                Late Entry Allowance (Minutes)
              </label>
              <input
                type="number"
                id="late_entry_minutes"
                name="late_entry_minutes"
                value={formData.late_entry_minutes}
                onChange={handleChange}
                min="0"
                className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
              />
              <p className="text-xs text-slate-500 mt-1">Grace period after start window opens to enter exam.</p>
            </div>
          </div>

          {/* Windows */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-2">
            <div>
              <label htmlFor="start_window" className="block text-sm font-semibold text-slate-900 mb-1">
                Start Window <span className="text-red-500">*</span>
              </label>
              <input
                type="datetime-local"
                id="start_window"
                name="start_window"
                value={formData.start_window}
                onChange={handleChange}
                className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                required
              />
              <p className="text-xs text-slate-500 mt-1">When exam becomes available for candidates to start.</p>
            </div>

            <div>
              <label htmlFor="end_window" className="block text-sm font-semibold text-slate-900 mb-1">
                End Window Deadline <span className="text-red-500">*</span>
              </label>
              <input
                type="datetime-local"
                id="end_window"
                name="end_window"
                value={formData.end_window}
                onChange={handleChange}
                className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                required
              />
              <p className="text-xs text-slate-500 mt-1">Final cutoff after which no submissions are accepted.</p>
            </div>
          </div>

          {/* Form Actions */}
          <div className="mt-8 pt-6 border-t border-slate-200 flex items-center justify-between">
            <Link
              href="/admin/exam"
              className="px-5 py-2.5 border border-slate-300 text-slate-700 rounded-lg text-sm font-semibold hover:bg-slate-50 transition"
            >
              Cancel
            </Link>

            <button
              type="submit"
              disabled={isSubmitting || !!createdExamId}
              className="inline-flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition disabled:opacity-50 shadow-sm"
            >
              {isSubmitting ? (
                <div className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              {isSubmitting ? "Creating Exam..." : "Create Exam & Add Questions"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
