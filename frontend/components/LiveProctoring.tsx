"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import Sidebar from "@/components/Sidebar";
import { Video, AlertTriangle, ShieldCheck, AlertCircle } from "lucide-react";

interface ActiveSession {
  id: string;
  candidate_name: string;
  exam_name: string;
  risk_level: "low" | "medium" | "high";
  status: string;
  started_at: string;
}

export default function LiveProctoringDashboard() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loadingSessions, setLoadingSessions] = useState(true);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isLoading || !user || !["admin", "proctor"].includes(user.role)) return;

    let socket: WebSocket | null = null;

    const loadSessions = async () => {
      try {
        const data = await apiClient.get<ActiveSession[]>("/api/dashboard/active-sessions");
        setSessions(data || []);
      } catch (err) {
        console.error("Could not fetch active sessions", err);
        setSessions([]);
        setError("Failed to load active sessions. Please try again later.");
      } finally {
        setLoadingSessions(false);
      }
    };

    void loadSessions();

    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const wsBase = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

    if (token && typeof window !== "undefined") {
      socket = new WebSocket(`${wsBase}/api/ws/dashboard?token=${encodeURIComponent(token)}`);
      socket.onmessage = () => {
        // Refetch sessions when a message is received
        void loadSessions();
      };
    }

    return () => {
      if (socket) {
        if (socket.readyState === WebSocket.CONNECTING) {
          socket.addEventListener("open", () => socket?.close());
        } else {
          socket.close();
        }
      }
    };
  }, [isLoading, user]);

  if (isLoading || !user) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center text-slate-500">Loading dashboard...</div>
      </div>
    );
  }

  if (!["admin", "proctor"].includes(user.role)) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center text-red-500">Access Denied</div>
      </div>
    );
  }

  const getRiskColor = (level: string) => {
    switch (level.toLowerCase()) {
      case "low":
        return "bg-emerald-100 text-emerald-800 border-emerald-200";
      case "medium":
        return "bg-amber-100 text-amber-800 border-amber-200";
      case "high":
        return "bg-red-100 text-red-800 border-red-200";
      default:
        return "bg-slate-100 text-slate-800 border-slate-200";
    }
  };

  const getRiskIcon = (level: string) => {
    switch (level.toLowerCase()) {
      case "low":
        return <ShieldCheck className="h-4 w-4 text-emerald-600 mr-1.5" />;
      case "medium":
        return <AlertTriangle className="h-4 w-4 text-amber-600 mr-1.5" />;
      case "high":
        return <AlertCircle className="h-4 w-4 text-red-600 mr-1.5" />;
      default:
        return null;
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />

      <main className="flex-1 p-6 sm:p-8 max-w-7xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5 mb-6">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">Live Proctoring</h1>
            <p className="text-sm text-slate-500 mt-1">Real-time monitoring of active examination sessions</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700 border border-blue-200">
              <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse"></span>
              Live Connection Active
            </span>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-50 text-red-700 border border-red-200 text-sm">
            {error}
          </div>
        )}

        {loadingSessions ? (
          <div className="flex justify-center items-center h-64">
            <div className="text-slate-500">Loading active sessions...</div>
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center p-12 bg-white rounded-xl border border-slate-200 shadow-sm">
            <Video className="mx-auto h-12 w-12 text-slate-300 mb-3" />
            <h3 className="text-lg font-medium text-slate-900">No active sessions</h3>
            <p className="text-slate-500 mt-1">There are currently no candidates taking an exam.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {sessions.map((session) => (
              <div key={session.id} className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col hover:shadow-md transition-shadow">
                {/* Simulated Video Feed */}
                <div className="bg-slate-900 aspect-video relative flex items-center justify-center">
                  <Video className="h-10 w-10 text-slate-700" />
                  <div className="absolute top-3 left-3 flex items-center gap-2">
                    <span className="flex items-center rounded-md bg-black/60 px-2 py-1 text-xs font-medium text-white backdrop-blur-sm">
                      <span className="mr-1.5 h-2 w-2 rounded-full bg-red-500 animate-pulse"></span>
                      REC
                    </span>
                  </div>
                  <div className="absolute bottom-3 right-3">
                     <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-semibold border backdrop-blur-sm ${getRiskColor(session.risk_level)} bg-opacity-90`}>
                        {getRiskIcon(session.risk_level)}
                        {session.risk_level.charAt(0).toUpperCase() + session.risk_level.slice(1)} Risk
                     </span>
                  </div>
                </div>

                {/* Session Details */}
                <div className="p-4 flex-1 flex flex-col">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h3 className="font-semibold text-slate-900 truncate" title={session.candidate_name}>
                        {session.candidate_name}
                      </h3>
                      <p className="text-xs text-slate-500 truncate" title={session.exam_name}>
                        {session.exam_name}
                      </p>
                    </div>
                  </div>
                  
                  <div className="mt-auto pt-3 flex justify-between items-center border-t border-slate-100">
                    <span className="text-xs text-slate-500">
                      Started: {new Date(session.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    <button className="text-xs font-medium text-blue-600 hover:text-blue-700">
                      View Details
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
