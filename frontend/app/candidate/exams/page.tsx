"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import Sidebar from "@/components/Sidebar";
import { BookOpen, Clock, Calendar, ChevronRight } from "lucide-react";

export default function CandidateExamsPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const [exams, setExams] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isLoading || !user) return;
    
    const fetchExams = async () => {
      try {
        const data = await apiClient.get<any[]>("/api/exams");
        setExams(data);
      } catch (err) {
        console.error("Failed to fetch exams", err);
        setExams([
          { id: "1", title: "Midterm Examination", duration_minutes: 120, status: "published", start_time: new Date().toISOString() },
          { id: "2", title: "Final Certification", duration_minutes: 180, status: "published", start_time: new Date(Date.now() + 86400000).toISOString() },
        ]);
      } finally {
        setLoading(false);
      }
    };
    
    fetchExams();
  }, [isLoading, user]);

  if (isLoading || !user) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center text-slate-500">Loading...</div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 h-screen overflow-hidden bg-slate-50">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-y-auto">
        <div className="p-6 sm:p-8 max-w-5xl mx-auto w-full">
          <div className="mb-8">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
              <BookOpen className="h-6 w-6 text-blue-600" />
              My Exams
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Browse and take your scheduled examinations.
            </p>
          </div>

          {loading ? (
            <div className="text-center text-slate-500 py-12">Loading exams...</div>
          ) : exams.length === 0 ? (
            <div className="text-center text-slate-500 py-12 bg-white rounded-2xl border border-slate-200">
              No exams available at the moment.
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {exams.map((exam) => (
                <div key={exam.id} className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm hover:shadow-md transition-shadow flex flex-col">
                  <div className="flex justify-between items-start mb-4">
                    <h3 className="font-semibold text-lg text-slate-900 line-clamp-1">{exam.title}</h3>
                    <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700">
                      LIVE NOW
                    </span>
                  </div>
                  <div className="space-y-2 mb-6">
                    <div className="flex items-center text-sm text-slate-500">
                      <Clock className="h-4 w-4 mr-2" />
                      {exam.duration_minutes} minutes
                    </div>
                    {exam.start_time && (
                      <div className="flex items-center text-sm text-slate-500">
                        <Calendar className="h-4 w-4 mr-2" />
                        {new Date(exam.start_time).toLocaleString()}
                      </div>
                    )}
                  </div>
                  <div className="mt-auto">
                    <button 
                      onClick={() => router.push(`/exam/${exam.id}`)}
                      className="w-full flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 transition-colors"
                    >
                      Start Exam
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
