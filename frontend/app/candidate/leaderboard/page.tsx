"use client";
export const dynamic = "force-dynamic";

import React, { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import { Trophy, Medal, Star, Loader2, Award, Search, Sparkles, UserCheck } from "lucide-react";
import toast from "react-hot-toast";

interface LeaderboardEntry {
  rank: number;
  session_id: string;
  candidate_name: string;
  total_score: number;
  percentage: number;
  is_me: boolean;
}

export default function LeaderboardPage() {
  const { user } = useAuth();
  const [exams, setExams] = useState<any[]>([]);
  const [selectedExam, setSelectedExam] = useState<string>("");
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchExams();
  }, []);

  useEffect(() => {
    if (selectedExam) {
      fetchLeaderboard(selectedExam);
    }
  }, [selectedExam]);

  const fetchExams = async () => {
    try {
      const data = await apiClient.get<any>("/api/exams?limit=50");
      const examList = Array.isArray(data) ? data : data?.exams || data?.data || [];
      const publishedExams = examList.filter((e: any) => e.status === "PUBLISHED");
      setExams(publishedExams);
      if (publishedExams.length > 0) {
        setSelectedExam(publishedExams[0].id);
      } else {
        setLoading(false);
      }
    } catch (error) {
      console.error("Failed to load exams", error);
      setLoading(false);
    }
  };

  const fetchLeaderboard = async (examId: string) => {
    setLoading(true);
    try {
      const data = await apiClient.get<LeaderboardEntry[]>(`/api/results/exam/${examId}/leaderboard`);
      setLeaderboard(Array.isArray(data) ? data : []);
    } catch (error) {
      setLeaderboard([]);
      toast.error("Failed to load leaderboard.");
    } finally {
      setLoading(false);
    }
  };

  const filteredLeaderboard = leaderboard.filter((item) =>
    item.candidate_name?.toLowerCase().includes(search.toLowerCase())
  );

  const topThree = filteredLeaderboard.slice(0, 3);
  const myEntry = leaderboard.find((item) => item.is_me);

  return (
    <div className="flex-1 p-6 sm:p-8 overflow-auto pb-12">
      <div className="w-full max-w-7xl mx-auto space-y-6">
        
        {/* Header Bar */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-200 pb-5">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
              <Trophy className="h-7 w-7 text-amber-500" />
              Academic Leaderboard & Rankings
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Celebrate top academic achievements and view published examination rankings.
            </p>
          </div>

          {exams.length > 0 && (
            <div className="w-full sm:w-auto">
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Select Exam
              </label>
              <select
                value={selectedExam}
                onChange={(e) => setSelectedExam(e.target.value)}
                className="w-full sm:w-72 border border-slate-300 rounded-xl px-4 py-2 bg-white text-sm font-semibold text-slate-900 shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              >
                {exams.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.title}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Hero Podium Banner */}
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white rounded-3xl p-6 sm:p-8 shadow-xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-80 h-80 bg-amber-500/10 rounded-full blur-3xl" />
          
          <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="space-y-2 text-center md:text-left">
              <span className="px-3 py-1 bg-amber-500/20 text-amber-300 border border-amber-400/30 rounded-full text-xs font-bold uppercase tracking-wider">
                ExamSentinel Hall of Fame
              </span>
              <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Top Academic Performers</h2>
              <p className="text-slate-300 text-xs sm:text-sm max-w-md">
                Scores and percentiles are calculated based on official published grading outputs.
              </p>
            </div>

            {/* Candidate Quick Rank Highlight Card */}
            {myEntry && (
              <div className="bg-white/10 backdrop-blur border border-white/20 p-4 rounded-2xl flex items-center gap-4 shrink-0 shadow-inner">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-400 text-slate-900 font-extrabold text-lg shadow">
                  #{myEntry.rank}
                </div>
                <div>
                  <div className="text-xs text-amber-300 font-semibold uppercase">Your Current Rank</div>
                  <div className="text-base font-bold text-white">{myEntry.candidate_name} (You)</div>
                  <div className="text-xs text-slate-300">
                    {myEntry.total_score} pts ({myEntry.percentage.toFixed(1)}%)
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Search Bar */}
        <div className="flex items-center justify-between gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search candidate by name..."
              className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
          </div>
          <div className="text-xs text-slate-500 hidden sm:block">
            Showing {filteredLeaderboard.length} Ranked Candidate(s)
          </div>
        </div>

        {/* Leaderboard Table Container */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          {loading ? (
            <div className="p-16 flex justify-center items-center">
              <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
            </div>
          ) : filteredLeaderboard.length === 0 ? (
            <div className="p-16 text-center space-y-3">
              <div className="w-16 h-16 bg-amber-50 rounded-2xl flex items-center justify-center mx-auto border border-amber-200 text-amber-500">
                <Trophy className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">No Published Rankings Found</h3>
              <p className="text-slate-500 text-xs sm:text-sm max-w-sm mx-auto">
                The leaderboard for this exam is currently empty. Leaderboards update automatically once grades are published by the course administrator.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-xs uppercase tracking-wider text-slate-500 font-semibold">
                    <th className="px-6 py-4">Rank</th>
                    <th className="px-6 py-4">Candidate Name</th>
                    <th className="px-6 py-4 text-right">Final Score</th>
                    <th className="px-6 py-4 text-right">Percentile Grade</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredLeaderboard.map((entry) => (
                    <tr
                      key={entry.session_id || entry.rank}
                      className={`transition-colors ${
                        entry.is_me
                          ? "bg-blue-50/70 border-l-4 border-l-blue-600"
                          : "hover:bg-slate-50/70"
                      }`}
                    >
                      <td className="px-6 py-4">
                        {entry.rank === 1 ? (
                          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-amber-400 text-slate-900 font-bold shadow-sm">
                            🥇 1
                          </div>
                        ) : entry.rank === 2 ? (
                          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-slate-200 text-slate-800 font-bold shadow-sm">
                            🥈 2
                          </div>
                        ) : entry.rank === 3 ? (
                          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-amber-700 text-white font-bold shadow-sm">
                            🥉 3
                          </div>
                        ) : (
                          <div className="flex items-center justify-center w-8 h-8 font-bold text-slate-500">
                            #{entry.rank}
                          </div>
                        )}
                      </td>

                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-sm shadow-sm ${
                            entry.is_me ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-700"
                          }`}>
                            {entry.candidate_name?.charAt(0)?.toUpperCase() || "C"}
                          </div>
                          <div>
                            <span className={`font-semibold ${entry.is_me ? "text-blue-900 font-bold" : "text-slate-900"}`}>
                              {entry.candidate_name}
                            </span>
                            {entry.is_me && (
                              <span className="ml-2 px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 text-[10px] font-bold">
                                YOU
                              </span>
                            )}
                          </div>
                        </div>
                      </td>

                      <td className="px-6 py-4 text-right">
                        <span className="font-extrabold text-slate-900">{entry.total_score}</span>
                        <span className="text-slate-400 text-xs ml-1">pts</span>
                      </td>

                      <td className="px-6 py-4 text-right">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          {entry.percentage.toFixed(1)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
