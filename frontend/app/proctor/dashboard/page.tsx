"use client";
export const dynamic = "force-dynamic";

import React, { useEffect, useState, useMemo, useCallback } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import {
  Video,
  ShieldAlert,
  AlertTriangle,
  ShieldCheck,
  Search,
  RefreshCw,
  Eye,
  Send,
  OctagonAlert,
  Users,
  Activity,
  Radio,
  RadioTower,
  MessageSquare,
  Sparkles,
  ArrowUpRight
} from "lucide-react";
import toast, { Toaster } from "react-hot-toast";

interface ActiveSession {
  session_id?: string;
  id?: string;
  candidate_name: string;
  candidate_email?: string;
  exam_title?: string;
  exam_name?: string;
  risk_level: string;
  current_risk_score?: number;
  violation_count?: number;
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

export default function ProctorDashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [signals, setSignals] = useState<Record<string, SessionSignals>>({});
  const [loading, setLoading] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [riskFilter, setRiskFilter] = useState<string>("ALL");

  // Inspection Modal State
  const [selectedSession, setSelectedSession] = useState<ActiveSession | null>(null);
  const [warningInput, setWarningInput] = useState("");
  const [isIntervening, setIsIntervening] = useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/auth/login");
    }
  }, [isLoading, isAuthenticated, router]);

  const loadActiveSessions = useCallback(async () => {
    try {
      const data = await apiClient.get<ActiveSession[]>("/api/dashboard/active-sessions");
      const activeList = Array.isArray(data) ? data : [];
      setSessions(activeList);
      setLastRefreshed(new Date());

      // Fetch signals for each session
      const signalEntries = await Promise.all(
        activeList.map(async (sess) => {
          const sId = sess.session_id || sess.id || "";
          if (!sId) return [sId, { warningCount: 0, cameraState: "waiting" as const, rawEvents: [] }] as const;

          try {
            const eventData = await apiClient.get<{ items: EventLogItem[] }>(
              `/api/proctoring/events/${sId}?page_size=100`
            );
            const events = eventData.items || [];
            const warnings = events.filter((e) =>
              ["FULLSCREEN_EXIT", "TAB_BLUR", "FACE_NOT_DETECTED", "MULTIPLE_FACES", "CAMERA_DENIED", "LARGE_PASTE"].includes(e.event_type)
            );
            const cameraEvents = events.filter((e) =>
              ["FACE_DETECTED_OK", "FACE_NOT_DETECTED", "MULTIPLE_FACES", "CAMERA_DENIED"].includes(e.event_type)
            );
            const lastCam = cameraEvents.at(-1)?.event_type;
            const latestFrame = [...events].reverse().find((e) => e.details?.image_url)?.details?.image_url;

            return [
              sId,
              {
                warningCount: warnings.length,
                lastWarning: warnings.at(-1)?.event_type,
                cameraState:
                  lastCam === "FACE_DETECTED_OK"
                    ? "tracking"
                    : ["FACE_NOT_DETECTED", "MULTIPLE_FACES", "CAMERA_DENIED"].includes(lastCam || "")
                    ? "attention"
                    : "waiting",
                latestFrame,
                rawEvents: events,
              } satisfies SessionSignals,
            ] as const;
          } catch {
            return [sId, { warningCount: 0, cameraState: "waiting" as const, rawEvents: [] }] as const;
          }
        })
      );
      setSignals(Object.fromEntries(signalEntries));
    } catch (err) {
      console.error("Failed to load active sessions for proctor dashboard", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isLoading && user && ["admin", "proctor"].includes(user.role)) {
      void loadActiveSessions();
      const interval = setInterval(loadActiveSessions, 20000);
      return () => clearInterval(interval);
    }
  }, [isLoading, user, loadActiveSessions]);

  const filteredSessions = useMemo(() => {
    return sessions.filter((s) => {
      const name = s.candidate_name || "";
      const exam = s.exam_title || s.exam_name || "";
      const email = s.candidate_email || "";

      const matchesSearch =
        !searchQuery.trim() ||
        name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        exam.toLowerCase().includes(searchQuery.toLowerCase()) ||
        email.toLowerCase().includes(searchQuery.toLowerCase());

      const level = (s.risk_level || "LOW").toUpperCase();
      let matchesRisk = true;
      if (riskFilter === "CRITICAL") matchesRisk = level === "HIGH" || level === "CRITICAL";
      if (riskFilter === "MEDIUM") matchesRisk = level === "MEDIUM";
      if (riskFilter === "LOW") matchesRisk = level === "LOW";

      return matchesSearch && matchesRisk;
    });
  }, [sessions, searchQuery, riskFilter]);

  const handleIssueWarning = async (sId: string) => {
    const message = warningInput.trim() || "Warning: Suspected unauthorized activity detected. Please return focus to your exam screen.";
    setIsIntervening(true);
    try {
      await apiClient.post(`/api/proctoring/sessions/${sId}/warning`, { message });
      toast.success("Live warning notification issued to candidate!");
      setWarningInput("");
      void loadActiveSessions();
    } catch (err: any) {
      toast.error(err?.message || "Failed to issue live warning.");
    } finally {
      setIsIntervening(false);
    }
  };

  const handleTerminateSession = async (sId: string, candidateName: string) => {
    if (!window.confirm(`Are you sure you want to TERMINATE the exam session for candidate "${candidateName}"?`)) {
      return;
    }
    const message = warningInput.trim() || "Session terminated by live proctor due to integrity policy violations.";
    setIsIntervening(true);
    try {
      await apiClient.post(`/api/proctoring/sessions/${sId}/terminate`, { message });
      toast.success(`Session for ${candidateName} has been terminated.`);
      setSelectedSession(null);
      void loadActiveSessions();
    } catch (err: any) {
      toast.error(err?.message || "Failed to terminate candidate session.");
    } finally {
      setIsIntervening(false);
    }
  };

  if (isLoading || !user) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-900 text-slate-300">
        <div className="flex items-center gap-3">
          <RefreshCw className="h-6 w-6 animate-spin text-blue-500" />
          <span>Loading Proctor Command Center...</span>
        </div>
      </div>
    );
  }

  // Summary Metrics
  const totalActive = sessions.length;
  const highRiskCount = sessions.filter((s) => ["HIGH", "CRITICAL"].includes((s.risk_level || "").toUpperCase())).length;
  const mediumRiskCount = sessions.filter((s) => (s.risk_level || "").toUpperCase() === "MEDIUM").length;
  const lowRiskCount = sessions.filter((s) => (s.risk_level || "").toUpperCase() === "LOW").length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 sm:p-6 lg:p-8 space-y-6">
      <Toaster position="top-right" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider bg-blue-500/10 text-blue-400 border border-blue-500/20">
              Live Operations
            </span>
            <span className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-0.5 rounded-full font-medium">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" /> Live Telemetry Feed
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white flex items-center gap-3">
            <RadioTower className="h-7 w-7 text-blue-500" />
            Proctor Control Center
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Monitor candidate video feeds, review AI risk telemetry, and issue real-time interventions.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-2 text-xs text-slate-400 bg-slate-900 border border-slate-800 px-3 py-2 rounded-xl">
            <Radio className="h-3.5 w-3.5 text-blue-400 animate-pulse" />
            <span>Updated: {lastRefreshed.toLocaleTimeString()}</span>
          </div>
          <button
            onClick={() => void loadActiveSessions()}
            className="inline-flex items-center gap-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 rounded-xl text-xs font-semibold transition-colors shadow-sm"
          >
            <RefreshCw className="h-3.5 w-3.5 text-blue-400" /> Refresh Grid
          </button>
          <Link
            href="/proctor/live"
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-blue-600/30"
          >
            Full Video Grid <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>

      {/* Metrics Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Active Candidates</span>
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400">
              <Users className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-white mt-3">{totalActive}</p>
          <p className="text-xs text-slate-500 mt-1">Currently taking exams</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">High Risk Alerts</span>
            <div className="p-2 rounded-xl bg-red-500/10 text-red-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-red-400 mt-3">{highRiskCount}</p>
          <p className="text-xs text-slate-500 mt-1">Requires immediate review</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Medium Risk Signals</span>
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-amber-400 mt-3">{mediumRiskCount}</p>
          <p className="text-xs text-slate-500 mt-1">Tab-switches / head movement</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Normal / Low Risk</span>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-emerald-400 mt-3">{lowRiskCount}</p>
          <p className="text-xs text-slate-500 mt-1">Compliant behavior stream</p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3.5 top-3 h-4 w-4 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search student or exam title..."
            className="w-full pl-10 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto overflow-x-auto">
          {(["ALL", "CRITICAL", "MEDIUM", "LOW"] as const).map((risk) => (
            <button
              key={risk}
              type="button"
              onClick={() => setRiskFilter(risk)}
              className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all ${
                riskFilter === risk
                  ? "bg-blue-600 text-white shadow-md shadow-blue-600/30"
                  : "bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800"
              }`}
            >
              {risk === "ALL" ? "All Risk Levels" : risk}
            </button>
          ))}
        </div>
      </div>

      {/* Candidates Live Grid */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-500">
          <RefreshCw className="w-8 h-8 animate-spin mb-3 text-blue-500" />
          <p className="text-sm">Connecting live proctoring stream...</p>
        </div>
      ) : filteredSessions.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400">
          <Video className="w-12 h-12 mx-auto mb-3 opacity-30 text-slate-500" />
          <h3 className="text-base font-bold text-slate-200 mb-1">No Active Candidates Found</h3>
          <p className="text-xs text-slate-500">No candidates currently match the search query or risk filter.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredSessions.map((sess) => {
            const sId = sess.session_id || sess.id || "";
            const sig = signals[sId] || { warningCount: 0, cameraState: "waiting" as const };
            const riskLevel = (sess.risk_level || "LOW").toUpperCase();
            const vCount = sess.violation_count ?? sig.warningCount ?? 0;

            const isCriticalCheater = vCount >= 4 || riskLevel === "CRITICAL" || sess.status === "EXPIRED";
            const isOrangeWarning = (vCount === 2 || vCount === 3 || riskLevel === "MEDIUM") && !isCriticalCheater;

            return (
              <div
                key={sId}
                className={`bg-slate-900 border rounded-2xl overflow-hidden flex flex-col transition-all hover:border-slate-700 shadow-xl ${
                  isCriticalCheater ? "border-red-500/80 bg-red-950/20 ring-2 ring-red-500/40" : isOrangeWarning ? "border-amber-500/50 bg-amber-950/10" : "border-slate-800"
                }`}
              >
                {/* Frame / Feed Header */}
                <div className="aspect-video bg-slate-950 relative flex items-center justify-center overflow-hidden border-b border-slate-800">
                  {sig.latestFrame ? (
                    <Image
                      src={sig.latestFrame}
                      alt="Candidate frame preview"
                      fill
                      unoptimized
                      className="object-cover"
                    />
                  ) : (
                    <div className="flex flex-col items-center justify-center text-slate-600 text-xs">
                      <Video className="w-8 h-8 mb-2 opacity-30" />
                      <span>Webcam Feed Active</span>
                    </div>
                  )}

                  <div className="absolute top-3 left-3 flex items-center gap-2">
                    <span className="px-2.5 py-1 bg-black/70 backdrop-blur rounded-lg text-[10px] font-bold text-white flex items-center gap-1.5 border border-white/10">
                      <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" /> LIVE
                    </span>
                  </div>

                  {/* Violation Indicator Light Badge */}
                  <div className="absolute bottom-3 right-3">
                    {isCriticalCheater ? (
                      <span className="px-3 py-1 rounded-full text-[11px] font-black uppercase border backdrop-blur bg-red-600/90 text-white border-red-400 shadow-lg shadow-red-600/50 flex items-center gap-1.5 animate-pulse">
                        <span className="w-2 h-2 rounded-full bg-white animate-ping" /> 🔴 CHEATER ({vCount}/4)
                      </span>
                    ) : isOrangeWarning ? (
                      <span className="px-3 py-1 rounded-full text-[11px] font-extrabold uppercase border backdrop-blur bg-amber-500/20 text-amber-300 border-amber-500/40 flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-amber-400" /> 🟠 WARNING ({vCount}/3)
                      </span>
                    ) : (
                      <span className="px-3 py-1 rounded-full text-[11px] font-extrabold uppercase border backdrop-blur bg-emerald-500/20 text-emerald-300 border-emerald-500/40 flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-400" /> 🟢 CLEAN ({vCount}/3)
                      </span>
                    )}
                  </div>
                </div>

                {/* Card Info */}
                <div className="p-5 flex-1 flex flex-col justify-between space-y-4">
                  <div>
                    <h3 className="font-bold text-white text-base truncate">{sess.candidate_name}</h3>
                    <p className="text-xs text-slate-400 truncate mt-0.5">{sess.exam_title || sess.exam_name || "Examination"}</p>
                    {sess.candidate_email && <p className="text-[11px] font-mono text-slate-500 mt-0.5">{sess.candidate_email}</p>}
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80">
                      <span className="text-slate-500 text-[10px] block uppercase font-semibold">AI Camera</span>
                      <span className={`font-bold ${sig.cameraState === "tracking" ? "text-emerald-400" : "text-amber-400"}`}>
                        {sig.cameraState === "tracking" ? "✓ Tracking OK" : "⚠ Flagged"}
                      </span>
                    </div>
                    <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80">
                      <span className="text-slate-500 text-[10px] block uppercase font-semibold">Warnings</span>
                      <span className={`font-bold ${sig.warningCount > 0 ? "text-red-400" : "text-slate-300"}`}>
                        {sig.warningCount} Logged
                      </span>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-slate-800/60 flex items-center justify-between">
                    <span className="text-[11px] text-slate-500">
                      Started: {sess.started_at ? new Date(sess.started_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—"}
                    </span>

                    <button
                      onClick={() => setSelectedSession(sess)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600/90 hover:bg-blue-600 text-white rounded-lg text-xs font-bold transition-all shadow-sm"
                    >
                      <Eye className="w-3.5 h-3.5" /> Inspect & Intervene
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Inspection Modal */}
      {selectedSession && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-2xl w-full overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
            <div className="p-6 border-b border-slate-800 bg-slate-950/50 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <Video className="w-5 h-5 text-blue-500" />
                  Candidate Live Inspection: {selectedSession.candidate_name}
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  Exam: {selectedSession.exam_title || selectedSession.exam_name} • Session: <span className="font-mono text-slate-300">{(selectedSession.session_id || selectedSession.id || "").slice(0, 8)}</span>
                </p>
              </div>
              <button
                onClick={() => setSelectedSession(null)}
                className="text-slate-400 hover:text-white text-xl font-bold p-2"
              >
                ✕
              </button>
            </div>

            <div className="p-6 space-y-6 overflow-y-auto">
              {/* Snapshot view */}
              <div className="aspect-video bg-slate-950 rounded-2xl relative overflow-hidden border border-slate-800 flex items-center justify-center">
                {signals[selectedSession.session_id || selectedSession.id || ""]?.latestFrame ? (
                  <Image
                    src={signals[selectedSession.session_id || selectedSession.id || ""]?.latestFrame!}
                    alt="Webcam snapshot"
                    fill
                    unoptimized
                    className="object-contain"
                  />
                ) : (
                  <div className="text-center text-slate-500 text-xs">
                    <Video className="w-10 h-10 mx-auto mb-2 opacity-30" />
                    <span>Live Stream Active — Awaiting Frame Snapshot</span>
                  </div>
                )}
              </div>

              {/* Proctor Action Controls */}
              <div className="bg-slate-950 p-5 rounded-2xl border border-slate-800 space-y-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-blue-400" /> Issue Live Proctor Intervention
                </h3>

                <input
                  type="text"
                  value={warningInput}
                  onChange={(e) => setWarningInput(e.target.value)}
                  placeholder="Type custom warning message to send to candidate..."
                  className="w-full px-4 py-2.5 bg-slate-900 border border-slate-700 rounded-xl text-xs text-white placeholder-slate-500 outline-none focus:border-blue-500"
                />

                <div className="flex flex-col sm:flex-row items-center gap-3">
                  <button
                    onClick={() => handleIssueWarning(selectedSession.session_id || selectedSession.id || "")}
                    disabled={isIntervening}
                    className="flex-1 w-full py-2.5 px-4 bg-amber-600 hover:bg-amber-500 text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    <Send className="w-4 h-4" /> Send Warning Notification
                  </button>

                  <button
                    onClick={() => handleTerminateSession(selectedSession.session_id || selectedSession.id || "", selectedSession.candidate_name)}
                    disabled={isIntervening}
                    className="flex-1 w-full py-2.5 px-4 bg-red-600 hover:bg-red-500 text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    <OctagonAlert className="w-4 h-4" /> Emergency Terminate Session
                  </button>
                </div>
              </div>
            </div>

            <div className="p-4 border-t border-slate-800 bg-slate-950 text-right">
              <button
                onClick={() => setSelectedSession(null)}
                className="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold"
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
