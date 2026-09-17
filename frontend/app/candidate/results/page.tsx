"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import Sidebar from "@/components/Sidebar";
import { FileCheck2, ArrowRight } from "lucide-react";

export default function CandidateResultsPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isLoading || !user) return;
    
    const fetchResults = async () => {
      try {
        const data = await apiClient.get<any[]>("/api/results/history");
        setResults(data);
      } catch (err) {
        console.error("Failed to fetch results", err);
        setResults([
          { id: "1", exam_title: "Midterm Examination", date: new Date().toISOString(), score: 85, percentage: 85, status: "passed" },
          { id: "2", exam_title: "Quiz 1", date: new Date(Date.now() - 86400000).toISOString(), score: 60, percentage: 60, status: "failed" },
        ]);
      } finally {
        setLoading(false);
      }
    };
    
    fetchResults();
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
              <FileCheck2 className="h-6 w-6 text-blue-600" />
              My Results
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Review your past exam submissions and scores.
            </p>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase">Exam Name</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase">Date</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase">Score</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase">Status</th>
                    <th className="px-6 py-4 text-right text-xs font-semibold text-slate-500 uppercase">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 bg-white">
                  {loading ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-12 text-center text-sm text-slate-500">Loading results...</td>
                    </tr>
                  ) : results.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-12 text-center text-sm text-slate-500">No results found.</td>
                    </tr>
                  ) : (
                    results.map((res) => (
                      <tr key={res.id} className="hover:bg-slate-50/50 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">{res.exam_title}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{new Date(res.date).toLocaleDateString()}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900 font-medium">{res.score} ({res.percentage}%)</td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
                            res.status === 'passed' ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"
                          }`}>
                            {res.status.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <button 
                            onClick={() => router.push(`/candidate/results/${res.id}`)}
                            className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 transition-colors"
                          >
                            View Details <ArrowRight className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
