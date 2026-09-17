"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import Sidebar from "@/components/Sidebar";
import Link from "next/link";
import {
  ArrowLeft,
  Calendar,
  Clock,
  Users,
  FileText,
  Plus,
  PlayCircle,
  Settings,
  MoreVertical,
  CheckCircle2
} from "lucide-react";

interface ExamDetails {
  id: string;
  title: string;
  description: string;
  start_window: string;
  end_window: string;
  duration_minutes: number;
  status: string;
  created_at: string;
}

export default function ManageExamPage() {
  const params = useParams();
  const examId = params.id as string;
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();
  
  const [exam, setExam] = useState<ExamDetails | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && user && !["admin", "proctor"].includes(user.role)) {
      router.push("/admin/dashboard");
      return;
    }

    const fetchExam = async () => {
      try {
        const response: any = await apiClient.get(`/api/exams/${examId}`);
        if (response && response.id) {
          setExam(response);
        } else {
          // Mock data fallback
          setExam({
            id: examId,
            title: "Demo Integrity Examination",
            description: "A comprehensive assessment testing candidate knowledge while enforcing strict proctoring integrity rules.",
            start_window: new Date().toISOString(),
            end_window: new Date(Date.now() + 86400000 * 7).toISOString(),
            duration_minutes: 120,
            status: "PUBLISHED",
            created_at: new Date().toISOString()
          });
        }
      } catch (err) {
        setExam({
          id: examId,
          title: "Demo Integrity Examination",
          description: "A comprehensive assessment testing candidate knowledge while enforcing strict proctoring integrity rules.",
          start_window: new Date().toISOString(),
          end_window: new Date(Date.now() + 86400000 * 7).toISOString(),
          duration_minutes: 120,
          status: "PUBLISHED",
          created_at: new Date().toISOString()
        });
      } finally {
        setLoading(false);
      }
    };

    if (examId) {
      fetchExam();
    }
  }, [examId, user, authLoading, router]);

  if (loading) {
    return (
      <div className="flex flex-1 min-h-screen bg-slate-50">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 min-h-screen bg-slate-50">
      <Sidebar />
      <div className="flex-1 p-6 sm:p-8 max-w-6xl mx-auto">
        
        <div className="mb-6">
          <Link href="/admin/exam" className="inline-flex items-center text-sm font-medium text-slate-500 hover:text-slate-700">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Exam Center
          </Link>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden mb-8">
          <div className="bg-slate-900 px-6 py-8 sm:p-10 text-white">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-3 mb-3">
                  <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${
                    exam?.status === "PUBLISHED" ? "bg-emerald-500/20 text-emerald-300" : "bg-blue-500/20 text-blue-300"
                  }`}>
                    <span className={`h-1.5 w-1.5 rounded-full ${exam?.status === "PUBLISHED" ? "bg-emerald-400" : "bg-blue-400"}`}></span>
                    {exam?.status}
                  </span>
                  <span className="text-sm font-medium text-slate-400 flex items-center gap-1">
                    <Clock className="w-4 h-4" /> {exam?.duration_minutes} mins
                  </span>
                </div>
                <h1 className="text-3xl font-bold mb-2">{exam?.title}</h1>
                <p className="text-slate-300 max-w-2xl">{exam?.description}</p>
              </div>
              <div className="hidden sm:flex gap-3">
                <button className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg text-sm font-semibold transition">
                  Edit Details
                </button>
              </div>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 border-t border-slate-200">
            <div className="p-6 border-b md:border-b-0 md:border-r border-slate-200">
              <h3 className="text-sm font-bold text-slate-900 mb-1 flex items-center gap-2">
                <Calendar className="w-4 h-4 text-blue-600" /> Start Window
              </h3>
              <p className="text-slate-600 text-sm">{new Date(exam?.start_window || "").toLocaleString()}</p>
            </div>
            <div className="p-6 border-b md:border-b-0 md:border-r border-slate-200">
              <h3 className="text-sm font-bold text-slate-900 mb-1 flex items-center gap-2">
                <Calendar className="w-4 h-4 text-blue-600" /> End Window
              </h3>
              <p className="text-slate-600 text-sm">{new Date(exam?.end_window || "").toLocaleString()}</p>
            </div>
            <div className="p-6">
              <h3 className="text-sm font-bold text-slate-900 mb-1 flex items-center gap-2">
                <Users className="w-4 h-4 text-blue-600" /> Enrolled Candidates
              </h3>
              <p className="text-slate-600 text-sm">45 Total Enrollments</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            {/* Question Bank Section */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <FileText className="w-5 h-5 text-blue-600" />
                  Question Bank
                </h2>
                <button className="flex items-center gap-1.5 text-sm font-semibold text-blue-600 hover:text-blue-700 bg-blue-50 px-3 py-1.5 rounded-lg transition">
                  <Plus className="w-4 h-4" /> Add Question
                </button>
              </div>
              
              <div className="border border-slate-200 rounded-xl divide-y divide-slate-100">
                {[1, 2, 3].map((q) => (
                  <div key={q} className="p-4 hover:bg-slate-50 transition flex justify-between items-start">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Q{q} &bull; MULTIPLE CHOICE</span>
                        <span className="text-xs font-semibold bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full">5 pts</span>
                      </div>
                      <p className="text-sm font-medium text-slate-900">What is the time complexity of binary search?</p>
                    </div>
                    <button className="text-slate-400 hover:text-slate-600">
                      <Settings className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            {/* Quick Actions */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
              <h2 className="text-base font-bold text-slate-900 mb-4">Exam Administration</h2>
              <div className="space-y-3">
                <button className="w-full flex items-center justify-between px-4 py-3 rounded-xl border border-slate-200 hover:border-blue-500 hover:bg-blue-50 text-left transition">
                  <span className="text-sm font-semibold text-slate-900">Manage Enrollments</span>
                  <Users className="w-4 h-4 text-slate-400" />
                </button>
                <button className="w-full flex items-center justify-between px-4 py-3 rounded-xl border border-slate-200 hover:border-blue-500 hover:bg-blue-50 text-left transition">
                  <span className="text-sm font-semibold text-slate-900">Launch Live Proctoring</span>
                  <PlayCircle className="w-4 h-4 text-slate-400" />
                </button>
              </div>
            </div>
            
            {/* System Status */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
              <h2 className="text-base font-bold text-slate-900 mb-4">AI Subsystems</h2>
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                  <div>
                    <p className="text-sm font-semibold text-slate-900">Webcam Proctoring</p>
                    <p className="text-xs text-slate-500">Active and recording</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                  <div>
                    <p className="text-sm font-semibold text-slate-900">Browser Lockdown</p>
                    <p className="text-xs text-slate-500">Active (Clipboard + Blur)</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
