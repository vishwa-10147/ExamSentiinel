"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import Sidebar from "@/components/Sidebar";
import { Trophy, Medal, Star, Loader2, Award } from "lucide-react";
import toast from "react-hot-toast";

interface LeaderboardEntry {
  rank: number;
  candidate_name: string;
  avatar_url: string | null;
  total_score: number;
  percentage: number;
}

export default function LeaderboardPage() {
  const { user } = useAuth();
  const [exams, setExams] = useState<any[]>([]);
  const [selectedExam, setSelectedExam] = useState<string>("");
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);

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
      // Only show published exams
      const publishedExams = examList.filter((e: any) => e.status === "PUBLISHED");
      setExams(publishedExams);
      if (publishedExams.length > 0) {
        setSelectedExam(publishedExams[0].id);
      } else {
        setLoading(false);
      }
    } catch (error) {
      setLoading(false);
    }
  };

  const fetchLeaderboard = async (examId: string) => {
    setLoading(true);
    try {
      const data = await apiClient.get<any>(`/api/results/exam/${examId}/leaderboard`);
      setLeaderboard(Array.isArray(data) ? data : data?.data || []);
    } catch (error) {
      setLeaderboard([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <div className="flex-1 p-8 overflow-auto">
        
        <div className="max-w-4xl mx-auto space-y-6">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
                <Trophy className="h-7 w-7 text-yellow-500" />
                Global Leaderboard
              </h1>
              <p className="text-slate-500 mt-1">See how you rank against your peers in published exams.</p>
            </div>
            
            {exams.length > 0 && (
              <select 
                value={selectedExam}
                onChange={(e) => setSelectedExam(e.target.value)}
                className="border border-slate-300 rounded-lg px-4 py-2 bg-white text-sm font-medium outline-none focus:ring-2 focus:ring-blue-500"
              >
                {exams.map(e => (
                  <option key={e.id} value={e.id}>{e.title}</option>
                ))}
              </select>
            )}
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="bg-slate-900 text-white p-6 pb-24 text-center relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-full opacity-10 pointer-events-none" style={{ backgroundImage: "radial-gradient(circle at center, #ffffff 1px, transparent 1px)", backgroundSize: "20px 20px" }}></div>
              <h2 className="text-3xl font-extrabold tracking-tight mb-2 relative z-10">Hall of Fame</h2>
              <p className="text-blue-200 text-sm relative z-10">Top performers are celebrated here.</p>
            </div>

            <div className="px-6 pb-6 -mt-16 relative z-20">
              {loading ? (
                <div className="bg-white rounded-xl shadow-lg border border-slate-100 p-12 flex justify-center">
                  <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
                </div>
              ) : leaderboard.length === 0 ? (
                <div className="bg-white rounded-xl shadow-lg border border-slate-100 p-12 flex flex-col items-center text-center">
                  <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
                    <Trophy className="w-8 h-8 text-slate-400" />
                  </div>
                  <h3 className="text-lg font-bold text-slate-900">No results published</h3>
                  <p className="text-slate-500 mt-1 text-sm max-w-sm">The leaderboard for this exam is currently empty. Check back once scores are published by the administrator.</p>
                </div>
              ) : (
                <div className="bg-white rounded-xl shadow-lg border border-slate-100 overflow-hidden">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-100 text-xs uppercase tracking-wider text-slate-500 font-semibold">
                        <th className="px-6 py-4">Rank</th>
                        <th className="px-6 py-4">Candidate</th>
                        <th className="px-6 py-4 text-right">Score</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {leaderboard.map((entry, idx) => (
                        <tr key={idx} className={`transition-colors ${entry.candidate_name === user?.full_name ? 'bg-blue-50/50' : 'hover:bg-slate-50'}`}>
                          <td className="px-6 py-4">
                            {entry.rank === 1 ? (
                              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-yellow-100 text-yellow-700 font-bold">1</div>
                            ) : entry.rank === 2 ? (
                              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-slate-100 text-slate-700 font-bold">2</div>
                            ) : entry.rank === 3 ? (
                              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-orange-100 text-orange-800 font-bold">3</div>
                            ) : (
                              <div className="flex items-center justify-center w-8 h-8 font-medium text-slate-500">{entry.rank}</div>
                            )}
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-sm">
                                {entry.candidate_name.charAt(0).toUpperCase()}
                              </div>
                              <span className={`font-medium ${entry.candidate_name === user?.full_name ? 'text-blue-700 font-bold' : 'text-slate-900'}`}>
                                {entry.candidate_name} {entry.candidate_name === user?.full_name && "(You)"}
                              </span>
                            </div>
                          </td>
                          <td className="px-6 py-4 text-right">
                            <span className="font-bold text-slate-900">{entry.total_score}</span>
                            <span className="text-slate-400 text-sm ml-1">pts</span>
                            <div className="text-xs font-medium text-emerald-600 mt-0.5">{entry.percentage.toFixed(1)}%</div>
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
      </div>
    </div>
  );
}
