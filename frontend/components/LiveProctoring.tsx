"use client";

import React, { useEffect, useState, useMemo } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import { Video, AlertTriangle, ShieldCheck, AlertCircle, Search, X, Send, OctagonAlert, Eye } from "lucide-react";
import toast, { Toaster } from "react-hot-toast";

interface ActiveSession {
  id: string;
  candidate_name: string;
  exam_name: string;
  risk_level: "low" | "medium" | "high" | "critical";
  status: string;
  started_at: string;
}

interface EventLogItem {
  event_type: string;
  category?: string;
  severity?: string;
  created_at?: string;
  details?: { image_url?: string; message?: string; reason?: string };
}

interface SessionSignals {
  warningCount: number;
  lastWarning?: string;
  cameraState: "tracking" | "attention" | "waiting";
  latestFrame?: string;
  rawEvents?: EventLogItem[];
}

export default function LiveProctoringDashboard() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [signals, setSignals] = useState<Record<string, SessionSignals>>({});
  const [error, setError] = useState<string | null>(null);
  const [loadingSessions, setLoadingSessions] = useState(true);

  // Search & Filter
  const [searchQuery, setSearchQuery] = useState("");
  const [riskFilter, setRiskFilter] = useState<string>("All");

  // Inspection Modal
  const [selectedSession, setSelectedSession] = useState<ActiveSession | null>(null);
  const [warningInput, setWarningInput] = useState("");
  const [isIntervening, setIsIntervening] = useState(false);

  const loadSessions = async () => {
    try {
      const data = await apiClient.get<any[]>("/api/dashboard/active-sessions");
      const activeSessions = (data || []).map((s: any) => ({
        ...s,
        id: s.session_id || s.id,
        candidate_name: s.candidate_name || "Candidate",
        exam_name: s.exam_title || s.exam_name || "Examination",
        risk_level: s.risk_level || "low",
        status: s.status || "IN_PROGRESS",
        started_at: s.started_at || new Date().toISOString(),
      }));
      setSessions(activeSessions);

      const signalEntries = await Promise.all(
        activeSessions.map(async (session) => {
          try {
            const eventData = await apiClient.get<{ items: EventLogItem[] }>(
              `/api/proctoring/events/${session.id}?page_size=200`
            );
            const events = eventData.items || [];
            const warnings = events.filter((event) =>
              [
                "FULLSCREEN_EXIT",
                "TAB_BLUR",
                "FACE_NOT_DETECTED",
                "MULTIPLE_FACES",
                "CAMERA_DENIED",
                "LARGE_PASTE",
              ].includes(event.event_type)
            );
            const cameraEvents = events.filter((event) =>
              [
                "FACE_DETECTED_OK",
                "FACE_NOT_DETECTED",
                "MULTIPLE_FACES",
                "CAMERA_DENIED",
              ].includes(event.event_type)
            );
            const lastCameraEvent = cameraEvents.at(-1)?.event_type;
            const latestFrame = [...events].reverse().find((event) => event.details?.image_url)?.details?.image_url;

            return [
              session.id,
              {
                warningCount: warnings.length,
                lastWarning: warnings.at(-1)?.event_type,
                cameraState:
                  lastCameraEvent === "FACE_DETECTED_OK"
                    ? "tracking"
                    : ["FACE_NOT_DETECTED", "MULTIPLE_FACES", "CAMERA_DENIED"].includes(lastCameraEvent || "")
                    ? "attention"
                    : "waiting",
                latestFrame,
                rawEvents: events,
              } satisfies SessionSignals,
            ] as const;
          } catch {
            return [session.id, { warningCount: 0, cameraState: "waiting", rawEvents: [] } satisfies SessionSignals] as const;
          }
        })
      );
      setSignals(Object.fromEntries(signalEntries));
    } catch (err) {
      console.error("Could not fetch active sessions", err);
      setSessions([]);
      setError("Failed to load active sessions. Please try again later.");
    } finally {
      setLoadingSessions(false);
    }
  };

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isLoading || !user || !["admin", "proctor"].includes(user.role)) return;

    let socket: WebSocket | null = null;
    void loadSessions();

    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    
    if (token && typeof window !== "undefined") {
      const isHttps = window.location.protocol === "https:";
      const wsProtocol = isHttps ? "wss:" : "ws:";
      const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || "https://examsentinel-backend.onrender.com";
      const cleanHost = rawApiUrl.replace(/^https?:\/\//, "").replace(/\/$/, "");
      const wsUrl = `${wsProtocol}//${cleanHost}/api/ws/dashboard?token=${encodeURIComponent(token)}`;

      try {
        socket = new WebSocket(wsUrl);
        socket.onopen = () => {
          console.log("Live Proctoring WebSocket connected.");
        };
        socket.onmessage = () => {
          void loadSessions();
        };
        socket.onerror = () => {
          // Quiet fallback to 10s polling interval
        };
      } catch (err) {
        console.warn("WebSocket connection fallback to polling");
      }
    }

    // Interval polling backup every 10 seconds
    const interval = setInterval(() => {
      void loadSessions();
    }, 10000);

    return () => {
      clearInterval(interval);
      if (socket) {
        if (socket.readyState === WebSocket.CONNECTING) {
          socket.addEventListener("open", () => socket?.close());
        } else {
          socket.close();
        }
      }
    };
  }, [isLoading, user]);

  const filteredSessions = useMemo(() => {
    return sessions.filter((s) => {
      const matchesSearch =
        !searchQuery.trim() ||
        s.candidate_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.exam_name.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesRisk =
        riskFilter === "All" ||
        s.risk_level.toLowerCase() === riskFilter.toLowerCase();

      return matchesSearch && matchesRisk;
    });
  }, [sessions, searchQuery, riskFilter]);

  const handleIssueWarning = async (sessionId: string) => {
    const msg = warningInput.trim() || "Warning: Suspected unauthorized activity detected during exam session.";
    setIsIntervening(true);
    try {
      await apiClient.post(`/api/proctoring/sessions/${sessionId}/warning`, { message: msg });
      toast.success("Live warning sent to candidate.");
      setWarningInput("");
      void loadSessions();
    } catch (err: any) {
      console.error("Failed to issue warning", err);
      toast.error(err?.message || "Failed to send warning");
    } finally {
      setIsIntervening(false);
    }
  };

  const handleTerminateSession = async (sessionId: string, candidateName: string) => {
    if (!window.confirm(`Are you sure you want to TERMINATE exam session for candidate "${candidateName}"?`)) {
      return;
    }
    const reason = warningInput.trim() || "Session terminated due to integrity policy violation.";
    setIsIntervening(true);
    try {
      await apiClient.post(`/api/proctoring/sessions/${sessionId}/terminate`, { message: reason });
      toast.success("Exam session terminated successfully.");
      setSelectedSession(null);
      void loadSessions();
    } catch (err: any) {
      console.error("Failed to terminate session", err);
      toast.error(err?.message || "Failed to terminate session");
    } finally {
      setIsIntervening(false);
    }
  };

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
        <div className="text-center text-red-500 font-semibold">Access Denied</div>
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
      case "critical":
        return "bg-purple-100 text-purple-900 border-purple-300 animate-pulse";
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
      case "critical":
        return <AlertCircle className="h-4 w-4 text-red-600 mr-1.5" />;
      default:
        return null;
    }
  };

  return (
    <div className="w-full p-6 sm:p-8 max-w-7xl mx-auto">
      <Toaster position="top-right" />
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5 mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <Video className="h-6 w-6 text-blue-600" />
            Live Proctoring
          </h1>
          <p className="text-sm text-slate-500 mt-1">Real-time AI telemetry monitoring & proctor intervention console</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 border border-emerald-200">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
            WebSocket Feed Active
          </span>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-lg bg-red-50 text-red-700 border border-red-200 text-sm">
          {error}
        </div>
      )}

      {/* Toolbar Search & Risk Filter */}
      <div className="mb-6 flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:max-w-md">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-4 w-4 text-slate-400" />
          </div>
          <input
            type="text"
            placeholder="Search active candidate or exam title..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="block w-full pl-9 pr-8 py-2 border border-slate-300 rounded-lg text-sm bg-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <label className="text-xs font-medium text-slate-500">Filter Risk:</label>
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm bg-white text-slate-700 outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="All">All Risk Levels</option>
            <option value="high">High & Critical Risk</option>
            <option value="medium">Medium Risk</option>
            <option value="low">Low Risk</option>
          </select>
        </div>
      </div>

      {loadingSessions ? (
        <div className="flex justify-center items-center h-64">
          <div className="text-slate-500">Loading active sessions...</div>
        </div>
      ) : filteredSessions.length === 0 ? (
        <div className="text-center p-12 bg-white rounded-2xl border border-slate-200 shadow-sm">
          <Video className="mx-auto h-12 w-12 text-slate-300 mb-3" />
          <h3 className="text-lg font-medium text-slate-900">No active candidate sessions match filter</h3>
          <p className="text-slate-500 mt-1">Waiting for candidates to start their live exam session...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredSessions.map((session) => {
            const sessionSignals = signals[session.id] || { warningCount: 0, cameraState: "waiting" as const };
            return (
              <div key={session.id} className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col hover:shadow-md transition-shadow">
                {/* Video Frame Feed */}
                <div className="bg-slate-900 aspect-video relative flex items-center justify-center">
                  {sessionSignals.latestFrame ? (
                    <Image
                      src={sessionSignals.latestFrame}
                      alt="Candidate camera frame"
                      fill
                      sizes="(max-width: 768px) 100vw, 33vw"
                      unoptimized
                      className="object-cover"
                    />
                  ) : (
                    <div className="text-center text-slate-600">
                      <Video className="h-10 w-10 mx-auto mb-1 opacity-50" />
                      <span className="text-xs">Consented Camera Feed</span>
                    </div>
                  )}
                  <div className="absolute top-3 left-3 flex items-center gap-2">
                    <span className="flex items-center rounded-md bg-black/60 px-2 py-1 text-xs font-medium text-white backdrop-blur-sm">
                      <span className="mr-1.5 h-2 w-2 rounded-full bg-red-500 animate-pulse"></span>
                      LIVE
                    </span>
                  </div>
                  <div className="absolute bottom-3 right-3">
                    <span className={`inline-flex items-center rounded-md px-2.5 py-1 text-xs font-semibold border backdrop-blur-sm ${getRiskColor(session.risk_level)} bg-opacity-90`}>
                      {getRiskIcon(session.risk_level)}
                      {session.risk_level.toUpperCase()} Risk
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
                      <p className="text-xs text-slate-500 truncate mt-0.5" title={session.exam_name}>
                        {session.exam_name}
                      </p>
                    </div>
                  </div>
                  
                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                    <div className={`rounded-md border px-2 py-1 flex items-center gap-1 ${
                      sessionSignals.cameraState === "tracking" ? "border-emerald-200 bg-emerald-50 text-emerald-700" :
                      sessionSignals.cameraState === "attention" ? "border-red-200 bg-red-50 text-red-700" :
                      "border-slate-200 bg-slate-50 text-slate-600"
                    }`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${sessionSignals.cameraState === "tracking" ? "bg-emerald-500" : "bg-red-500"}`}></span>
                      AI: {sessionSignals.cameraState === "tracking" ? "Tracking OK" : "Attention Flag"}
                    </div>
                    <div className={`rounded-md border px-2 py-1 ${sessionSignals.warningCount ? "border-red-200 bg-red-50 text-red-700 font-semibold" : "border-slate-200 bg-slate-50 text-slate-600"}`}>
                      Warnings: {sessionSignals.warningCount}
                    </div>
                  </div>

                  <div className="mt-4 pt-3 flex justify-between items-center border-t border-slate-100 text-xs">
                    <span className="text-slate-500">
                      Started: {new Date(session.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    <button
                      onClick={() => setSelectedSession(session)}
                      className="inline-flex items-center gap-1 font-semibold text-blue-600 hover:text-blue-700 cursor-pointer"
                    >
                      <Eye className="h-3.5 w-3.5" /> Inspect Session
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Detailed Live Inspection Modal */}
      {selectedSession && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div>
                <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <Video className="h-5 w-5 text-blue-600" />
                  Live Proctoring Inspection: {selectedSession.candidate_name}
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">{selectedSession.exam_name} • Session ID: {selectedSession.id.slice(0, 8)}...</p>
              </div>
              <button onClick={() => setSelectedSession(null)} className="text-slate-400 hover:text-slate-600 text-xl font-bold">
                &times;
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-6">
              {/* Snapshot Display */}
              <div className="bg-slate-900 aspect-video rounded-xl relative overflow-hidden flex items-center justify-center">
                {signals[selectedSession.id]?.latestFrame ? (
                  <Image
                    src={signals[selectedSession.id]?.latestFrame!}
                    alt="High res candidate webcam feed"
                    fill
                    unoptimized
                    className="object-contain"
                  />
                ) : (
                  <div className="text-center text-slate-500">
                    <Video className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <span>Live feed active. Awaiting camera snapshot...</span>
                  </div>
                )}
                <div className="absolute top-3 right-3">
                  <span className={`inline-flex items-center rounded-md px-3 py-1 text-xs font-bold border ${getRiskColor(selectedSession.risk_level)} bg-opacity-90`}>
                    {selectedSession.risk_level.toUpperCase()} RISK
                  </span>
                </div>
              </div>

              {/* Intervention Controls */}
              <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 space-y-3">
                <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <OctagonAlert className="h-4 w-4 text-amber-600" /> Live Proctor Interventions
                </h4>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Enter proctor warning or reason..."
                    value={warningInput}
                    onChange={(e) => setWarningInput(e.target.value)}
                    className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm bg-white outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={() => handleIssueWarning(selectedSession.id)}
                    disabled={isIntervening}
                    className="inline-flex items-center gap-1.5 px-3 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold transition disabled:opacity-50"
                  >
                    <Send className="h-3.5 w-3.5" /> Send Warning
                  </button>
                  <button
                    onClick={() => handleTerminateSession(selectedSession.id, selectedSession.candidate_name)}
                    disabled={isIntervening}
                    className="inline-flex items-center gap-1.5 px-3 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-xs font-semibold transition disabled:opacity-50"
                  >
                    <OctagonAlert className="h-3.5 w-3.5" /> Terminate Session
                  </button>
                </div>
              </div>

              {/* Event Logs Timeline */}
              <div>
                <h4 className="text-sm font-bold text-slate-900 mb-3">Live Telemetry Event Timeline</h4>
                <div className="border border-slate-200 rounded-xl divide-y divide-slate-100 max-h-56 overflow-y-auto bg-white">
                  {!signals[selectedSession.id]?.rawEvents || signals[selectedSession.id].rawEvents?.length === 0 ? (
                    <div className="p-4 text-center text-xs text-slate-400">No telemetry events logged for this session yet.</div>
                  ) : (
                    signals[selectedSession.id].rawEvents?.map((evt, idx) => (
                      <div key={idx} className="p-3 flex items-center justify-between text-xs hover:bg-slate-50">
                        <div>
                          <span className="font-mono font-bold text-slate-800">{evt.event_type}</span>
                          {evt.details?.message && <p className="text-slate-500 text-[11px] mt-0.5">{evt.details.message}</p>}
                        </div>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                          evt.severity === "CRITICAL" || evt.severity === "HIGH" ? "bg-red-100 text-red-700" :
                          evt.severity === "MEDIUM" ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-600"
                        }`}>
                          {evt.severity || "INFO"}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>

            <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex justify-end">
              <button
                onClick={() => setSelectedSession(null)}
                className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200 rounded-lg transition"
              >
                Close Inspection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
