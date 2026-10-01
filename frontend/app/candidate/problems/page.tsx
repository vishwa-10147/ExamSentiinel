"use client";
export const dynamic = "force-dynamic";

import React, { useEffect, useState } from "react";
import { apiClient } from "@/services/apiClient";
import Link from "next/link";
import { Loader2, AlertCircle, Search, Code2, ArrowRight, BookOpen } from "lucide-react";

interface Question {
  id: string;
  title: string;
  difficulty: "Easy" | "Medium" | "Hard" | string;
  type?: string;
  points?: number;
}

export default function ProblemsPage() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [difficultyFilter, setDifficultyFilter] = useState<"ALL" | "EASY" | "MEDIUM" | "HARD">("ALL");

  useEffect(() => {
    const fetchQuestions = async () => {
      try {
        const response = await apiClient.get('/api/questions');
        const data = (response as any).data?.questions || (response as any).data || (response as any) || [];
        setQuestions(Array.isArray(data) ? data : []);
      } catch (err: any) {
        console.error("Failed to fetch questions", err);
        setError(err?.message || "Failed to load practice problems");
      } finally {
        setLoading(false);
      }
    };
    fetchQuestions();
  }, []);

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty.toLowerCase()) {
      case "easy":
        return "text-emerald-700 bg-emerald-50 border-emerald-200";
      case "medium":
        return "text-amber-700 bg-amber-50 border-amber-200";
      case "hard":
        return "text-red-700 bg-red-50 border-red-200";
      default:
        return "text-slate-700 bg-slate-100 border-slate-200";
    }
  };

  const filteredQuestions = questions.filter((q) => {
    const matchesSearch = q.title.toLowerCase().includes(search.toLowerCase());
    if (!matchesSearch) return false;

    if (difficultyFilter !== "ALL" && q.difficulty.toUpperCase() !== difficultyFilter) {
      return false;
    }
    return true;
  });

  return (
    <div className="w-full max-w-7xl mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Code2 className="h-6 w-6 text-blue-600" />
            Coding Practice Problems
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Solve algorithmic challenges, submit solutions, and pass test suites.
          </p>
        </div>
      </div>

      {/* Filter and Search */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search problems by title..."
            className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
        </div>

        <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-lg w-full sm:w-auto overflow-x-auto">
          {(["ALL", "EASY", "MEDIUM", "HARD"] as const).map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setDifficultyFilter(d)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                difficultyFilter === d
                  ? "bg-white text-blue-600 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {d === "ALL" ? "All Levels" : d}
            </button>
          ))}
        </div>
      </div>

      {/* Content Container */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-400">
            <Loader2 className="w-8 h-8 animate-spin mb-3 text-blue-600" />
            <p className="text-sm">Loading practice problem set...</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-16 text-red-500 space-y-2">
            <AlertCircle className="w-8 h-8" />
            <p className="text-sm">{error}</p>
          </div>
        ) : filteredQuestions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-400 space-y-2">
            <BookOpen className="w-10 h-10 text-slate-300" />
            <p className="text-sm font-semibold text-slate-700">No problems match criteria</p>
            <p className="text-xs text-slate-400">Try clearing your search or difficulty filter.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left text-slate-600">
              <thead className="text-xs text-slate-500 uppercase bg-slate-50 border-b border-slate-200 font-semibold">
                <tr>
                  <th scope="col" className="px-6 py-4">Problem Title</th>
                  <th scope="col" className="px-6 py-4">Difficulty Level</th>
                  <th scope="col" className="px-6 py-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredQuestions.map((q) => (
                  <tr key={q.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-6 py-4 font-semibold text-slate-900 whitespace-nowrap">
                      {q.title}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold border ${getDifficultyColor(q.difficulty)}`}>
                        {q.difficulty}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link 
                        href={`/candidate/problems/${q.id}`}
                        className="inline-flex items-center justify-center rounded-xl text-xs font-bold transition-all bg-blue-600 text-white hover:bg-blue-700 h-9 px-4 py-2 shadow-sm gap-1"
                      >
                        Solve Challenge <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
