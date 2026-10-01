"use client";
export const dynamic = "force-dynamic";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { BarChart3, Download, RefreshCw, ShieldAlert, Award, FileText, Activity } from "lucide-react";

interface AnalyticsOverview {
  total_exams: number;
  active_sessions: number;
  completed_sessions: number;
  average_risk_score: number;
  risk_breakdown: {
    LOW: number;
    MEDIUM: number;
    HIGH: number;
    CRITICAL: number;
  };
}

interface BatchPerformance {
  batch_name: string;
  total_students: number;
  avg_risk: number;
}

export default function AnalyticsDashboard() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();

  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [batchData, setBatchData] = useState<BatchPerformance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const overviewRes = await apiClient.get<AnalyticsOverview>("/api/analytics/overview");
      const batchRes = await apiClient.get<BatchPerformance[]>("/api/analytics/batch-performance");
      setOverview(overviewRes);
      setBatchData(batchRes || []);
    } catch (err: any) {
      console.error("Failed to fetch analytics", err);
      setError(err?.message || "Failed to load analytics metrics.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/auth/login");
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (authLoading || !user || user.role !== "admin") return;
    void fetchData();
  }, [authLoading, user, fetchData]);

  const handleExportCSV = () => {
    if (!overview) return;
    const rows = [
      ["Metric", "Value"],
      ["Total Exams Created", overview.total_exams],
      ["Active Live Sessions", overview.active_sessions],
      ["Completed Sessions", overview.completed_sessions],
      ["Average Risk Score", overview.average_risk_score],
      ["Low Risk Sessions", overview.risk_breakdown?.LOW || 0],
      ["Medium Risk Sessions", overview.risk_breakdown?.MEDIUM || 0],
      ["High Risk Sessions", overview.risk_breakdown?.HIGH || 0],
      ["Critical Risk Sessions", overview.risk_breakdown?.CRITICAL || 0],
    ];

    const csvContent = "data:text/csv;charset=utf-8," + rows.map((e) => e.join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `university_analytics_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (authLoading || !user) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <div className="text-center text-slate-500">Loading analytics dashboard...</div>
      </div>
    );
  }

  if (user.role !== "admin") {
    return (
      <div className="flex-1 w-full">
        <div className="flex-1 p-8 text-center text-red-500 font-semibold mt-10">
          Access Denied. Admins only.
        </div>
      </div>
    );
  }

  const pieColors = ["#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];
  const pieData = [
    { name: "Low Risk", value: overview?.risk_breakdown?.LOW || 0 },
    { name: "Medium Risk", value: overview?.risk_breakdown?.MEDIUM || 0 },
    { name: "High Risk", value: overview?.risk_breakdown?.HIGH || 0 },
    { name: "Critical Risk", value: overview?.risk_breakdown?.CRITICAL || 0 },
  ].filter((item) => item.value > 0 || (overview && Object.values(overview.risk_breakdown || {}).every((v) => v === 0)));

  return (
    <div className="flex-1 w-full">
      <main className="flex-1 flex flex-col overflow-y-auto">
        <div className="p-6 sm:p-8 max-w-7xl mx-auto w-full space-y-8">
          
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
                <BarChart3 className="h-6 w-6 text-blue-600" />
                University Analytics
              </h1>
              <p className="text-sm text-slate-500 mt-1">
                Global examination metrics, academic integrity distribution, and batch performance.
              </p>
            </div>
            
            <div className="flex gap-2">
              <button
                onClick={() => fetchData()}
                disabled={loading}
                className="inline-flex items-center gap-2 rounded-lg bg-white border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                Refresh
              </button>
              
              <button
                onClick={handleExportCSV}
                disabled={!overview}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 transition-colors disabled:opacity-50"
              >
                <Download className="h-4 w-4" />
                Export CSV
              </button>
            </div>
          </div>

          {error && (
            <div className="rounded-xl bg-amber-50 p-4 border border-amber-200 text-sm text-amber-800">
              {error}
            </div>
          )}

          {/* KPI Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between text-slate-500">
                <span className="text-xs font-semibold uppercase tracking-wider">Total Exams</span>
                <FileText className="h-5 w-5 text-blue-600" />
              </div>
              <p className="text-3xl font-extrabold text-slate-900 mt-3">{overview?.total_exams || 0}</p>
              <span className="text-xs text-slate-400 mt-1 block">Created in system</span>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between text-slate-500">
                <span className="text-xs font-semibold uppercase tracking-wider">Active Live Sessions</span>
                <Activity className="h-5 w-5 text-emerald-600" />
              </div>
              <div className="flex items-baseline gap-2 mt-3">
                <p className="text-3xl font-extrabold text-slate-900">{overview?.active_sessions || 0}</p>
                {overview?.active_sessions ? (
                  <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                ) : null}
              </div>
              <span className="text-xs text-slate-400 mt-1 block">In progress right now</span>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between text-slate-500">
                <span className="text-xs font-semibold uppercase tracking-wider">Completed Sessions</span>
                <Award className="h-5 w-5 text-purple-600" />
              </div>
              <p className="text-3xl font-extrabold text-slate-900 mt-3">{overview?.completed_sessions || 0}</p>
              <span className="text-xs text-slate-400 mt-1 block">Submitted & graded</span>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between text-slate-500">
                <span className="text-xs font-semibold uppercase tracking-wider">Avg AI Risk Score</span>
                <ShieldAlert className="h-5 w-5 text-indigo-600" />
              </div>
              <p className="text-3xl font-extrabold text-indigo-600 mt-3">
                {(overview?.average_risk_score || 0).toFixed(1)} <span className="text-xs text-slate-400 font-normal">/ 100</span>
              </p>
              <span className="text-xs text-slate-400 mt-1 block">Cumulative risk index</span>
            </div>
          </div>

          {/* Charts Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            
            {/* Bar Chart: Batch Performance */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col">
              <h2 className="text-base font-bold text-slate-900 mb-1">Batch Performance Comparison</h2>
              <p className="text-xs text-slate-500 mb-6">Student counts and average risk scores per academic batch</p>
              <div className="h-80 flex-1">
                {batchData.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-slate-400 text-sm">
                    No batch performance data recorded yet.
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={batchData} margin={{ top: 10, right: 30, left: 0, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis dataKey="batch_name" stroke="#64748b" fontSize={12} />
                      <YAxis stroke="#64748b" fontSize={12} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: "#0f172a", borderRadius: "12px", color: "#fff", border: "none" }} 
                      />
                      <Legend />
                      <Bar dataKey="total_students" fill="#3b82f6" radius={[6, 6, 0, 0]} name="Total Sessions" />
                      <Bar dataKey="avg_risk" fill="#ef4444" radius={[6, 6, 0, 0]} name="Avg Risk Score" />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>

            {/* Pie Chart: Integrity Distribution */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col">
              <h2 className="text-base font-bold text-slate-900 mb-1">Academic Integrity Distribution</h2>
              <p className="text-xs text-slate-500 mb-6">Session categorization by AI risk level breakdown</p>
              <div className="h-80 flex-1">
                {pieData.every((d) => d.value === 0) ? (
                  <div className="h-full flex items-center justify-center text-slate-400 text-sm">
                    No session risk distribution data available yet.
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={4}
                        dataKey="value"
                        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={pieColors[index % pieColors.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderRadius: "12px", color: "#fff", border: "none" }} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>

          </div>
        </div>
      </main>
    </div>
  );
}
