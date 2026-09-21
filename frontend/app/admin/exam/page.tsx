"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import Sidebar from "@/components/Sidebar";
import {
  FileText,
  Calendar,
  Clock,
  Plus,
  ArrowRight,
  MoreVertical,
  Activity,
  PlayCircle
} from "lucide-react";
import Link from "next/link";

interface Exam {
  id: string;
  title: string;
  description: string;
  start_window: string;
  end_window: string;
  duration_minutes: number;
  status: string;
  created_at: string;
}

export default function ExamListPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && (!isAuthenticated || (user && user.role !== "admin"))) {
      router.push("/dashboard");
    }
  }, [isLoading, isAuthenticated, user, router]);

  useEffect(() => {
    if (isLoading || !user) return;
    
    // Admins and Proctors can see this list. (Maybe candidates see a different list, but let's allow it based on UI or redirect if unauthorized)
    
    const fetchExams = async () => {
      try {
        setLoading(true);
        const data = await apiClient.get<Exam[]>("/api/exams");
        setExams(Array.isArray(data) ? data : []);
      } catch (err: any) {
        console.error("Failed to fetch exams", err);
        setExams([]);
        setError("Failed to load exams. Please try again later.");
      } finally {
        setLoading(false);
      }
    };
    
    fetchExams();
  }, [isLoading, user]);

  if (isLoading || !user) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center text-slate-500 dark:text-slate-400 dark:text-slate-500">Loading Exam Center...</div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch(status.toLowerCase()) {
      case 'active': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'draft': return 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-700';
      case 'completed': return 'bg-blue-50 text-blue-700 border-blue-200';
      default: return 'bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-700';
    }
  };

  return (
    <div className="flex-1 w-full p-6 sm:p-8 max-w-7xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 dark:border-slate-700 pb-5">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              Exam Center
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 dark:text-slate-500 mt-1">
              Manage and monitor your institutional examinations.
            </p>
          </div>
          {["admin", "proctor"].includes(user.role) && (
            <div className="flex items-center gap-3">
              <Link
                href="/admin/exam/builder"
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 transition-colors shadow-sm"
              >
                <Plus className="h-4 w-4" />
                Create Exam
              </Link>
            </div>
          )}
        </div>

        <div className="mt-8">
          {loading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin h-6 w-6 text-blue-500 rounded-full border-b-2 border-current"></div>
            </div>
          ) : error ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-red-600">
              {error}
            </div>
          ) : exams.length === 0 ? (
            <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 dark:border-slate-700 p-12 text-center shadow-sm">
              <FileText className="mx-auto h-12 w-12 text-slate-300" />
              <h3 className="mt-4 text-lg font-semibold text-slate-900 dark:text-white">No exams found</h3>
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400 dark:text-slate-500">Get started by creating a new examination.</p>
              {["admin", "proctor"].includes(user.role) && (
                <div className="mt-6">
                  <Link
                    href="/admin/exam/builder"
                    className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 transition-colors shadow-sm"
                  >
                    <Plus className="h-4 w-4" />
                    Create Exam
                  </Link>
                </div>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {exams.map((exam) => (
                <div key={exam.id} className="flex flex-col rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 dark:border-slate-700 shadow-sm overflow-hidden hover:shadow-md transition-shadow">
                  <div className="p-6 flex-1">
                    <div className="flex justify-between items-start mb-4">
                      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border ${getStatusColor(exam.status)}`}>
                        {exam.status.charAt(0).toUpperCase() + exam.status.slice(1)}
                      </span>
                      <button className="text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:text-slate-300 transition-colors">
                        <MoreVertical className="h-5 w-5" />
                      </button>
                    </div>
                    <h3 className="text-lg font-bold text-slate-900 dark:text-white line-clamp-1 mb-2" title={exam.title}>
                      {exam.title}
                    </h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400 dark:text-slate-500 line-clamp-2 mb-6">
                      {exam.description || "No description provided."}
                    </p>
                    
                    <div className="space-y-3">
                      <div className="flex items-center text-sm text-slate-600 dark:text-slate-300">
                        <Clock className="h-4 w-4 mr-2 text-slate-400 dark:text-slate-500" />
                        <span>{exam.duration_minutes} minutes</span>
                      </div>
                      <div className="flex items-center text-sm text-slate-600 dark:text-slate-300">
                        <Calendar className="h-4 w-4 mr-2 text-slate-400 dark:text-slate-500" />
                        <span className="truncate">
                          {new Date(exam.start_window).toLocaleDateString()} - {new Date(exam.end_window).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-900 px-6 py-4 border-t border-slate-100">
                    <div className="flex items-center justify-between">
                      {user.role === "candidate" ? (
                        <Link
                          href={`/exam/${exam.id}`}
                          className="text-sm font-semibold text-blue-600 hover:text-blue-500 flex items-center gap-1"
                        >
                          Launch Exam <PlayCircle className="h-4 w-4" />
                        </Link>
                      ) : (
                        <Link
                          href={`/admin/exam/${exam.id}/manage`}
                          className="text-sm font-semibold text-slate-700 dark:text-slate-200 hover:text-slate-900 dark:text-white flex items-center gap-1"
                        >
                          Manage <ArrowRight className="h-4 w-4" />
                        </Link>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    
  );
}

