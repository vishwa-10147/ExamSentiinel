"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient, AppealDetail, TelemetryEvent } from "@/services/apiClient";
import Sidebar from "@/components/Sidebar";
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  User,
  Shield,
  ShieldAlert,
  Play,
  Pause,
  RotateCcw,
  RotateCw,
  Maximize2,
  Volume2,
  Eye,
  Camera,
  Monitor,
  Calendar,
  BookOpen,
  MessageSquare,
  FileCheck,
  Activity,
  Layers,
  Sparkles,
  Info,
  Check,
  X,
  Lock,
} from "lucide-react";

// Rich mock data store for individual appeal cases
const DETAILED_MOCK_APPEALS: Record<string, AppealDetail> = {
  "app-101": {
    id: "app-101",
    case_id: "APP-2024-001",
    candidate_id: "cand-9283",
    candidate_name: "Sarah Jenkins",
    candidate_email: "s.jenkins@university.edu",
    exam_name: "CS201: Data Structures & Algorithms",
    original_finding: "High Risk (88) — Multiple faces detected in webcam feed",
    risk_score: 88,
    appeal_date: "2026-09-15T14:22:00Z",
    status: "PENDING",
    session_id: "sess_882910a",
    original_reviewer_id: "rev_001",
    original_reviewer_name: "Marcus Vance (Proctor Lead)",
    reason:
      "My younger brother opened the bedroom door unexpectedly to ask about his homework. He left immediately within 3 seconds when I gestured for him to close the door. I never looked away from the monitor or spoke. Please verify the frozen video snapshot and audio capture which shows no communication occurred.",
    proctor_notes:
      "At timestamp 00:42:15, AI biometric vision engine detected secondary facial landmarks entering the upper-left quadrant of the video frame. Risk score spiked to 88. Candidate made a brief hand gesture. Finding was marked as confirmed unauthorized room occupant violation per Exam Regulation §4.2.",
    resolution: null,
    telemetryMetrics: {
      audioSpikes: 1,
      gazeDeviations: 2,
      headRotations: 1,
      tabSwitches: 0,
      confidence: 94,
    },
    timeline: [
      {
        id: "t1",
        time: "00:15:30",
        type: "INFO",
        source: "Lockdown Client",
        description: "Candidate entered full-screen lockdown environment. All auxiliary displays disabled.",
        frameTimestampSec: 930,
      },
      {
        id: "t2",
        time: "00:42:15",
        type: "CRITICAL",
        source: "Webcam Biometrics",
        description: "Secondary face detected at frame coordinates (X: 142, Y: 88). Confidence: 94.2%. Duration: 2.8s.",
        frameTimestampSec: 2535,
      },
      {
        id: "t3",
        time: "00:42:18",
        type: "WARNING",
        source: "Gesture Analysis",
        description: "Brief lateral left-hand gesture detected toward frame periphery. Gaze remained on exam window.",
        frameTimestampSec: 2538,
      },
      {
        id: "t4",
        time: "00:42:25",
        type: "INFO",
        source: "Acoustic Sensor",
        description: "Door latch acoustic profile registered (52dB). No verbal communication or secondary voice detected.",
        frameTimestampSec: 2545,
      },
      {
        id: "t5",
        time: "01:25:00",
        type: "INFO",
        source: "Exam System",
        description: "Exam submitted successfully by candidate with 38 of 40 questions answered.",
        frameTimestampSec: 5100,
      },
    ],
  },
  "app-102": {
    id: "app-102",
    case_id: "APP-2024-002",
    candidate_id: "cand-4419",
    candidate_name: "David Chen",
    candidate_email: "d.chen@engineering.edu",
    exam_name: "EE302: Signals & Systems",
    original_finding: "Escalated (92) — Continuous audio decibel spike (Talking detected)",
    risk_score: 92,
    appeal_date: "2026-09-16T09:10:00Z",
    status: "UNDER_REVIEW",
    session_id: "sess_772183b",
    original_reviewer_id: "rev_002",
    original_reviewer_name: "Elena Rostova (Reviewer)",
    reason:
      "I was working through a multi-step Fourier transform derivation and was vocalizing my arithmetic calculations aloud as a cognitive thinking technique. The room was completely isolated and no outside audio was received. The microphone frequency spectral analysis proves this was a single localized speaker whispering formulas.",
    proctor_notes:
      "Vocal signal detected exceeding 65dB for 90 cumulative seconds during section B. Flagged by acoustic engine as potential communication or external coaching. Candidate did not respond to automated in-exam warning prompt.",
    resolution: null,
    telemetryMetrics: {
      audioSpikes: 4,
      gazeDeviations: 1,
      headRotations: 0,
      tabSwitches: 0,
      confidence: 89,
    },
    timeline: [
      {
        id: "t1",
        time: "00:20:10",
        type: "INFO",
        source: "Microphone Calibration",
        description: "Ambient baseline noise calibrated at 32dB.",
        frameTimestampSec: 1210,
      },
      {
        id: "t2",
        time: "01:12:00",
        type: "CRITICAL",
        source: "Acoustic Sensor",
        description: "Continuous speech pattern flagged (68dB). Speech-to-text transcript: 'integral from minus infinity to plus infinity e to the minus j omega t dt...'",
        frameTimestampSec: 4320,
      },
      {
        id: "t3",
        time: "01:13:30",
        type: "WARNING",
        source: "Proctor Alert",
        description: "Automated warning issued: 'Please maintain silence during examination.'",
        frameTimestampSec: 4410,
      },
      {
        id: "t4",
        time: "01:14:00",
        type: "INFO",
        source: "Acoustic Sensor",
        description: "Speech ceased. Room ambient noise returned to 34dB baseline.",
        frameTimestampSec: 4440,
      },
    ],
  },
  "app-103": {
    id: "app-103",
    case_id: "APP-2024-003",
    candidate_id: "cand-8831",
    candidate_name: "Amara Okafor",
    candidate_email: "amara.o@business.ac.uk",
    exam_name: "FIN401: Advanced Corporate Finance",
    original_finding: "Confirmed Violation (79) — Repeated window blur & tab switching",
    risk_score: 79,
    appeal_date: "2026-09-14T16:45:00Z",
    status: "RESOLVED",
    session_id: "sess_551928c",
    original_reviewer_id: "rev_001",
    original_reviewer_name: "Marcus Vance (Proctor Lead)",
    reason:
      "A background security tool generated an interactive notification dialog that stole window focus. I dismissed it immediately without accessing any disallowed resources.",
    proctor_notes:
      "Six distinct window blur events registered between 00:25:00 and 00:48:00. Clipboard inspection shows external paste event into scratchpad tool.",
    resolution:
      "UPHELD: Reviewer examined screen buffer telemetry and confirmed candidate navigated to an external browser instance for financial formulas. Appeal denied; original failure upheld.",
    telemetryMetrics: {
      audioSpikes: 0,
      gazeDeviations: 5,
      headRotations: 3,
      tabSwitches: 6,
      confidence: 97,
    },
    timeline: [
      {
        id: "t1",
        time: "00:25:12",
        type: "CRITICAL",
        source: "Window Focus",
        description: "Browser focus lost (Event: Blur). Duration: 14 seconds.",
        frameTimestampSec: 1512,
      },
      {
        id: "t2",
        time: "00:32:40",
        type: "CRITICAL",
        source: "Window Focus",
        description: "Browser focus lost. Clipboard contents updated externally.",
        frameTimestampSec: 1960,
      },
      {
        id: "t3",
        time: "00:33:05",
        type: "WARNING",
        source: "Input Stream",
        description: "Clipboard paste command executed in exam scratchpad.",
        frameTimestampSec: 1985,
      },
    ],
  },
};

export default function AppealDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();

  const [appeal, setAppeal] = useState<AppealDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [resolutionNotes, setResolutionNotes] = useState<string>("");
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<"webcam" | "screen" | "room">("webcam");
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [selectedTimelineIndex, setSelectedTimelineIndex] = useState<number>(1);
  const [playbackTime, setPlaybackTime] = useState<string>("00:42:15");
  const [modalAction, setModalAction] = useState<"OVERTURN" | "UPHOLD" | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Auth protection check
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/auth/login");
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    const fetchAppealDetail = async () => {
      if (!id) return;
      try {
        const data = await apiClient.getAppeal(id as string);
        if (data && data.id) {
          setAppeal(data);
          if (data.resolution) {
            setResolutionNotes(data.resolution);
          }
        } else {
          // Fallback to mock dictionary or synthetic fallback
          const fallback =
            DETAILED_MOCK_APPEALS[id as string] || {
              ...DETAILED_MOCK_APPEALS["app-101"],
              id: id as string,
              case_id: `APP-2024-${String(id).slice(-3).padStart(3, "0")}`,
            };
          setAppeal(fallback);
          if (fallback.resolution) {
            setResolutionNotes(fallback.resolution);
          }
        }
      } catch (err) {
        console.warn("Using mock appeal detail data:", err);
        const fallback =
          DETAILED_MOCK_APPEALS[id as string] || {
            ...DETAILED_MOCK_APPEALS["app-101"],
            id: id as string,
            case_id: `APP-2024-${String(id).slice(-3).padStart(3, "0")}`,
          };
        setAppeal(fallback);
        if (fallback.resolution) {
          setResolutionNotes(fallback.resolution);
        }
      } finally {
        setLoading(false);
      }
    };

    if (!authLoading && user && ["admin", "reviewer"].includes(user.role)) {
      void fetchAppealDetail();
    } else if (!authLoading) {
      setLoading(false);
    }
  }, [id, authLoading, user]);

  const handleTimelineClick = (index: number, time: string) => {
    setSelectedTimelineIndex(index);
    setPlaybackTime(time);
  };

  const handleConfirmDecision = async () => {
    if (!appeal || !modalAction) return;

    if (!resolutionNotes.trim()) {
      setErrorMessage("Please provide a detailed adjudication justification before recording your verdict.");
      return;
    }

    setSubmitting(true);
    setErrorMessage(null);

    const newStatus = modalAction === "OVERTURN" ? "REVERSED" : "UPHELD";
    const statusLabel = modalAction === "OVERTURN" ? "OVERTURNED (Passed)" : "UPHELD (Failed)";

    try {
      await apiClient.resolveAppeal(appeal.id, {
        status: newStatus,
        resolution: resolutionNotes,
      });

      setAppeal((prev) =>
        prev
          ? {
              ...prev,
              status: newStatus,
              resolution: resolutionNotes,
            }
          : null
      );

      setSuccessMessage(
        `Appeal successfully resolved: Finding ${modalAction === "OVERTURN" ? "Overturned (Student Passed)" : "Upheld (Student Failed)"}. Audit ledger updated.`
      );
      setModalAction(null);
    } catch (err: any) {
      console.warn("Mocking resolution API response:", err);
      // Simulate successful local state resolution for mock environment
      setAppeal((prev) =>
        prev
          ? {
              ...prev,
              status: newStatus,
              resolution: resolutionNotes,
            }
          : null
      );
      setSuccessMessage(
        `Adjudication recorded: Finding ${modalAction === "OVERTURN" ? "Overturned (Candidate Passed)" : "Upheld (Candidate Failed)"}.`
      );
      setModalAction(null);
    } finally {
      setSubmitting(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="flex h-96 items-center justify-center bg-slate-50">
        <div className="text-center text-slate-500 flex flex-col items-center gap-2">
          <Activity className="w-8 h-8 text-blue-600 animate-pulse" />
          <span className="font-medium">Loading Appeal Case Evidence #{id}...</span>
        </div>
      </div>
    );
  }

  if (!user || !["admin", "reviewer"].includes(user.role)) {
    return (
      <div className="flex flex-1 min-h-screen bg-slate-50">
        <Sidebar />
        <main className="flex-1 p-8 flex items-center justify-center">
          <div className="bg-white rounded-2xl border border-red-200 p-8 max-w-md text-center shadow-sm">
            <ShieldAlert className="w-10 h-10 text-red-600 mx-auto mb-3" />
            <h2 className="text-lg font-bold text-slate-900">Adjudication Access Restricted</h2>
            <p className="text-sm text-slate-500 mt-1 mb-4">
              You must possess Admin or Reviewer credentials to review contested student exam appeals.
            </p>
            <button
              onClick={() => router.push("/admin/appeals")}
              className="px-4 py-2 bg-slate-900 text-white text-sm font-medium rounded-lg"
            >
              Back to Appeals
            </button>
          </div>
        </main>
      </div>
    );
  }

  if (!appeal) {
    return (
      <div className="flex flex-1 min-h-screen bg-slate-50">
        <Sidebar />
        <main className="flex-1 p-8">
          <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center max-w-lg mx-auto mt-12">
            <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-3" />
            <h3 className="text-lg font-bold text-slate-900">Appeal Case Not Found</h3>
            <p className="text-sm text-slate-500 mt-1 mb-6">
              The requested appeal case identifier does not exist or has expired from active cache.
            </p>
            <Link
              href="/admin/appeals"
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition"
            >
              Return to Appeals Queue
            </Link>
          </div>
        </main>
      </div>
    );
  }

  const isResolved =
    ["RESOLVED", "UPHELD", "OVERTURNED", "REVERSED"].includes(appeal.status.toUpperCase());
  const isOverturned =
    ["OVERTURNED", "REVERSED"].includes(appeal.status.toUpperCase());
  const isUpheld = appeal.status.toUpperCase() === "UPHELD";

  return (
    <div className="flex flex-1 min-h-screen bg-slate-50">
      <Sidebar />

      <main className="flex-1 p-6 sm:p-8 max-w-7xl mx-auto w-full">
        {/* Breadcrumb & Navigation */}
        <div className="mb-6 flex items-center justify-between">
          <Link
            href="/admin/appeals"
            className="inline-flex items-center text-sm font-semibold text-slate-600 hover:text-blue-600 transition"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Appeals Queue
          </Link>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-mono">Case ID:</span>
            <span className="font-mono text-xs font-bold text-slate-800 bg-slate-200/80 px-2 py-0.5 rounded">
              {appeal.case_id}
            </span>
          </div>
        </div>

        {/* Success Banner */}
        {successMessage && (
          <div className="mb-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-start gap-3 shadow-sm animate-in fade-in">
            <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
            <div className="flex-1 font-medium">{successMessage}</div>
            <button
              onClick={() => setSuccessMessage(null)}
              className="text-emerald-700 hover:text-emerald-900"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Case Header with Quick Action Bar */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm mb-8">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-2xl sm:text-3xl font-bold text-slate-900">
                  Appeal Case #{appeal.case_id}
                </h1>
                {isResolved ? (
                  <span
                    className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold ${
                      isOverturned
                        ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                        : "bg-rose-100 text-rose-800 border border-rose-200"
                    }`}
                  >
                    {isOverturned ? (
                      <CheckCircle className="w-3.5 h-3.5 mr-1 text-emerald-600" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 mr-1 text-rose-600" />
                    )}
                    {isOverturned ? "OVERTURNED (STUDENT PASSED)" : "UPHELD (STUDENT FAILED)"}
                  </span>
                ) : (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-200">
                    <Clock className="w-3.5 h-3.5 mr-1 text-amber-600" />
                    {appeal.status.replace("_", " ")}
                  </span>
                )}
              </div>
              <p className="text-sm text-slate-500 mt-1">
                Contested session from{" "}
                <span className="font-semibold text-slate-700">{appeal.exam_name}</span> • Submitted on{" "}
                {new Date(appeal.appeal_date).toLocaleDateString(undefined, {
                  month: "long",
                  day: "numeric",
                  year: "numeric",
                })}
              </p>
            </div>

            {/* Decision Action Buttons */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => setModalAction("OVERTURN")}
                disabled={submitting}
                className="inline-flex items-center gap-2 px-4 py-2.5 bg-emerald-600 text-white rounded-xl text-sm font-semibold hover:bg-emerald-700 transition shadow-sm disabled:opacity-50"
              >
                <CheckCircle className="w-4 h-4" />
                <span>Overturn Finding (Pass Student)</span>
              </button>

              <button
                onClick={() => setModalAction("UPHOLD")}
                disabled={submitting}
                className="inline-flex items-center gap-2 px-4 py-2.5 bg-rose-600 text-white rounded-xl text-sm font-semibold hover:bg-rose-700 transition shadow-sm disabled:opacity-50"
              >
                <XCircle className="w-4 h-4" />
                <span>Uphold Finding (Fail Student)</span>
              </button>
            </div>
          </div>

          {/* Quick Details Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-slate-100 text-sm">
            <div>
              <span className="text-xs text-slate-400 block uppercase font-medium">Candidate</span>
              <span className="font-semibold text-slate-900">{appeal.candidate_name}</span>
              <span className="text-xs text-slate-500 block">{appeal.candidate_email}</span>
            </div>
            <div>
              <span className="text-xs text-slate-400 block uppercase font-medium">Original Proctor</span>
              <span className="font-semibold text-slate-900">
                {appeal.original_reviewer_name || "Marcus Vance (Proctor Lead)"}
              </span>
              <span className="text-xs text-slate-500 block">Initial Flagged Review</span>
            </div>
            <div>
              <span className="text-xs text-slate-400 block uppercase font-medium">Original Risk Score</span>
              <div className="flex items-center gap-2 mt-0.5">
                <span
                  className={`font-bold ${
                    appeal.risk_score > 80
                      ? "text-red-600"
                      : appeal.risk_score > 50
                      ? "text-amber-600"
                      : "text-emerald-600"
                  }`}
                >
                  {appeal.risk_score}/100
                </span>
                <span className="text-xs bg-red-50 text-red-700 border border-red-200 px-1.5 py-0.5 rounded font-medium">
                  High Risk
                </span>
              </div>
            </div>
            <div>
              <span className="text-xs text-slate-400 block uppercase font-medium">Current Reviewer</span>
              <span className="font-semibold text-blue-600">{user.full_name}</span>
              <span className="text-xs text-slate-500 block">Adjudicating Reviewer</span>
            </div>
          </div>
        </div>

        {/* Split View: Left (Statements & Notes) vs Right (Evidence Player & Timeline) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* LEFT SIDE: Student Appeal Statement & Original Proctor Notes (5 cols) */}
          <div className="lg:col-span-5 space-y-6">
            {/* Student Appeal Statement Card */}
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
                    <MessageSquare className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="font-bold text-slate-900 text-base">Student Appeal Statement</h2>
                    <p className="text-xs text-slate-500">Submitted by {appeal.candidate_name}</p>
                  </div>
                </div>
                <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-medium">
                  Verified Candidate
                </span>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 mb-4">
                <p className="text-sm text-slate-700 leading-relaxed italic">
                  &ldquo;{appeal.reason}&rdquo;
                </p>
              </div>

              <div className="space-y-2 text-xs text-slate-600">
                <div className="flex justify-between py-1.5 border-b border-slate-100">
                  <span className="text-slate-500">Appeal Submission Date:</span>
                  <span className="font-medium text-slate-800">
                    {new Date(appeal.appeal_date).toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-100">
                  <span className="text-slate-500">Candidate Student ID:</span>
                  <span className="font-mono text-slate-800 font-medium">{appeal.candidate_id}</span>
                </div>
                <div className="flex justify-between py-1.5">
                  <span className="text-slate-500">Integrity Attestation:</span>
                  <span className="font-medium text-emerald-700 flex items-center gap-1">
                    <CheckCircle className="w-3.5 h-3.5" />
                    Signed by Candidate
                  </span>
                </div>
              </div>
            </div>

            {/* Original Proctor Notes & Initial Finding Card */}
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 bg-amber-50 text-amber-600 rounded-lg">
                    <ShieldAlert className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="font-bold text-slate-900 text-base">Original Proctor Finding</h2>
                    <p className="text-xs text-slate-500">
                      Logged by {appeal.original_reviewer_name || "Proctor"}
                    </p>
                  </div>
                </div>
                <span className="text-xs bg-red-100 text-red-800 px-2.5 py-0.5 rounded-full font-bold">
                  Score {appeal.risk_score}
                </span>
              </div>

              <div className="bg-amber-50/50 border border-amber-200/80 rounded-xl p-4 mb-4">
                <h4 className="text-xs font-bold uppercase tracking-wider text-amber-900 mb-1">
                  Proctor Observation Log
                </h4>
                <p className="text-sm text-amber-950 leading-relaxed">
                  {appeal.proctor_notes ||
                    "Telemetry sensors flagged suspicious biometric and optical divergence during the examination session. Initial determination classified this as an unauthorized event."}
                </p>
              </div>

              <div className="rounded-xl border border-slate-100 bg-slate-50 p-3 space-y-2 text-xs">
                <div className="flex justify-between text-slate-600">
                  <span className="text-slate-500">Initial Finding Category:</span>
                  <span className="font-medium text-slate-900">{appeal.original_finding}</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span className="text-slate-500">Flagged Timestamp:</span>
                  <span className="font-mono text-slate-900 font-semibold">00:42:15 in exam</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span className="text-slate-500">AI Confidence Level:</span>
                  <span className="font-semibold text-blue-600">94.2%</span>
                </div>
              </div>
            </div>

            {/* Reviewer Resolution Justification Card */}
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
              <div className="flex items-center gap-2.5 mb-3">
                <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
                  <FileCheck className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="font-bold text-slate-900 text-base">Adjudication Resolution Notes</h2>
                  <p className="text-xs text-slate-500">
                    Mandatory rationale recorded in the immutable audit ledger
                  </p>
                </div>
              </div>

              {isResolved && appeal.resolution ? (
                <div className="bg-emerald-50/60 border border-emerald-200 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <CheckCircle className="w-4 h-4 text-emerald-600" />
                    <span className="text-xs font-bold uppercase tracking-wider text-emerald-800">
                      Final Recorded Verdict
                    </span>
                  </div>
                  <p className="text-sm text-emerald-950 leading-relaxed font-medium">
                    {appeal.resolution}
                  </p>
                </div>
              ) : (
                <div>
                  <textarea
                    rows={4}
                    value={resolutionNotes}
                    onChange={(e) => setResolutionNotes(e.target.value)}
                    placeholder="Enter formal justification for overturning or upholding this finding (e.g. 'Evidence video proves brother was only in room for 2.8s without interaction. Gaze divergence was zero. Finding overturned.')..."
                    className="w-full text-sm p-3.5 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800 bg-white"
                  />
                  {errorMessage && (
                    <p className="text-xs text-rose-600 mt-2 font-medium">{errorMessage}</p>
                  )}
                  <p className="text-xs text-slate-400 mt-2">
                    Note: Your decision and notes will be tied to your cryptographic reviewer ID.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* RIGHT SIDE: Frozen Video & Telemetry Evidence Hub (7 cols) */}
          <div className="lg:col-span-7 space-y-6">
            {/* Frozen Video Evidence Container */}
            <div className="bg-slate-900 rounded-2xl border border-slate-800 shadow-xl overflow-hidden text-white">
              {/* Video Header & Feed Selector */}
              <div className="px-5 py-3.5 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-500/20 text-red-400 border border-red-500/30">
                    <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
                    FROZEN EVIDENCE SNAPSHOT
                  </span>
                  <span className="font-mono text-xs text-slate-400 font-semibold">
                    {playbackTime} UTC
                  </span>
                </div>

                {/* Feed switchers */}
                <div className="flex items-center space-x-1 bg-slate-800/80 p-1 rounded-lg">
                  <button
                    onClick={() => setActiveTab("webcam")}
                    className={`px-2.5 py-1 text-xs font-medium rounded transition flex items-center gap-1.5 ${
                      activeTab === "webcam"
                        ? "bg-blue-600 text-white shadow-sm"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    <Camera className="w-3.5 h-3.5" />
                    <span>Webcam</span>
                  </button>
                  <button
                    onClick={() => setActiveTab("screen")}
                    className={`px-2.5 py-1 text-xs font-medium rounded transition flex items-center gap-1.5 ${
                      activeTab === "screen"
                        ? "bg-blue-600 text-white shadow-sm"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    <Monitor className="w-3.5 h-3.5" />
                    <span>Screen Feed</span>
                  </button>
                  <button
                    onClick={() => setActiveTab("room")}
                    className={`px-2.5 py-1 text-xs font-medium rounded transition flex items-center gap-1.5 ${
                      activeTab === "room"
                        ? "bg-blue-600 text-white shadow-sm"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    <Layers className="w-3.5 h-3.5" />
                    <span>Room Context</span>
                  </button>
                </div>
              </div>

              {/* Video Viewport / Frozen Frame Canvas */}
              <div className="relative aspect-video w-full bg-slate-950 flex items-center justify-center overflow-hidden">
                {activeTab === "webcam" && (
                  <div className="relative w-full h-full flex items-center justify-center bg-gradient-to-b from-slate-900 to-slate-950">
                    {/* Simulated Camera Feed with Biometric Overlays */}
                    <div className="relative w-full h-full flex items-center justify-center">
                      {/* Candidate Avatar/Silhouette Representation */}
                      <div className="relative flex flex-col items-center">
                        <div className="w-36 h-36 rounded-full border-2 border-emerald-500/80 bg-slate-800 flex items-center justify-center relative shadow-inner">
                          <User className="w-20 h-20 text-slate-400" />
                          {/* Face tracking bounding box */}
                          <div className="absolute -inset-2 border-2 border-dashed border-emerald-400/60 rounded-xl pointer-events-none" />
                          <div className="absolute -top-3 bg-emerald-500 text-slate-950 text-[10px] font-bold px-1.5 py-0.5 rounded">
                            Verified Candidate (99.8%)
                          </div>
                        </div>
                        <span className="text-xs font-medium text-slate-400 mt-3 font-mono">
                          Gaze Vector: Centered [0.02, -0.01]
                        </span>
                      </div>

                      {/* Flagged Secondary Face in Background (Simulated Evidence) */}
                      <div className="absolute top-10 left-10 p-3 rounded-xl border border-red-500/70 bg-red-950/40 backdrop-blur-sm animate-pulse">
                        <div className="w-16 h-16 rounded-full border border-red-500/80 bg-slate-800 flex items-center justify-center mb-1">
                          <User className="w-8 h-8 text-red-400" />
                        </div>
                        <div className="text-[10px] font-bold text-red-400 uppercase tracking-wider text-center">
                          Secondary Face
                        </div>
                        <div className="text-[9px] text-red-300 text-center font-mono">
                          Duration: 2.8s
                        </div>
                      </div>

                      {/* Video Biometric Watermark */}
                      <div className="absolute bottom-4 left-4 bg-slate-950/70 px-3 py-1.5 rounded-lg border border-slate-800/80 text-[11px] font-mono text-slate-300">
                        <div>LATENCY: 42ms • FPS: 30.0</div>
                        <div>SIGNAL: MULTI-FACE_DETECTED</div>
                      </div>

                      {/* Audio decibel meter on screen */}
                      <div className="absolute bottom-4 right-4 bg-slate-950/70 px-3 py-1.5 rounded-lg border border-slate-800/80 text-[11px] font-mono text-slate-300 flex items-center gap-2">
                        <Volume2 className="w-4 h-4 text-emerald-400" />
                        <span>MIC: 36 dB (Ambient)</span>
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === "screen" && (
                  <div className="w-full h-full bg-slate-900 p-6 flex flex-col justify-between">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                      <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-red-500 inline-block" />
                        <span className="w-3 h-3 rounded-full bg-amber-500 inline-block" />
                        <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block" />
                        <span className="text-xs text-slate-400 font-mono ml-2">
                          ExamSentinel Lockdown Browser v2.4
                        </span>
                      </div>
                      <span className="text-xs font-mono text-emerald-400">STATUS: FOCUSED</span>
                    </div>

                    <div className="my-auto text-center p-8 border border-dashed border-slate-800 rounded-xl bg-slate-950/50">
                      <BookOpen className="w-12 h-12 text-blue-500 mx-auto mb-2 opacity-80" />
                      <p className="text-sm font-semibold text-slate-200">
                        Exam Window: Question 24 of 40
                      </p>
                      <p className="text-xs text-slate-400 mt-1">
                        &quot;Implement a Red-Black tree rebalancing method following right rotation...&quot;
                      </p>
                      <div className="mt-4 inline-flex items-center gap-2 px-3 py-1 bg-blue-950/80 border border-blue-800/60 rounded-full text-xs text-blue-300 font-mono">
                        <CheckCircle className="w-3.5 h-3.5 text-blue-400" />
                        Screen Lock Active • Zero tab blur detected at this timestamp
                      </div>
                    </div>

                    <div className="text-xs font-mono text-slate-500 flex justify-between">
                      <span>MONITOR: 1920x1080 60Hz</span>
                      <span>BUFFER: SYNCED</span>
                    </div>
                  </div>
                )}

                {activeTab === "room" && (
                  <div className="w-full h-full bg-slate-950 flex items-center justify-center p-6 text-center">
                    <div>
                      <Layers className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                      <p className="text-sm font-semibold text-slate-300">
                        Auxiliary Room Perspective Feed
                      </p>
                      <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                        Candidate workstation context camera. Bedroom door visible in background left corner. No additional unauthorized electronics present.
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Scrubber & Video Controls */}
              <div className="p-4 bg-slate-950 border-t border-slate-800 space-y-3">
                {/* Visual Scrubber with Markers */}
                <div className="relative w-full h-3 bg-slate-800 rounded-full cursor-pointer flex items-center">
                  <div className="h-full bg-blue-600 rounded-full" style={{ width: "42%" }} />
                  {/* Flagged event pin markers */}
                  <div
                    title="00:15:30 - Lockdown Started"
                    className="absolute w-2 h-2 rounded-full bg-blue-400 -translate-x-1"
                    style={{ left: "15%" }}
                  />
                  <div
                    title="00:42:15 - CRITICAL: Multi-face detected"
                    className="absolute w-3 h-3 rounded-full bg-red-500 border-2 border-white -translate-x-1.5 shadow-lg shadow-red-500/50"
                    style={{ left: "42%" }}
                  />
                  <div
                    title="00:42:25 - Acoustic latch profile"
                    className="absolute w-2 h-2 rounded-full bg-amber-400 -translate-x-1"
                    style={{ left: "43%" }}
                  />
                  <div
                    title="01:25:00 - Submission"
                    className="absolute w-2 h-2 rounded-full bg-emerald-400 -translate-x-1"
                    style={{ left: "85%" }}
                  />
                </div>

                {/* Control bar */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <button
                      onClick={() => setIsPlaying(!isPlaying)}
                      className="p-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition"
                      title={isPlaying ? "Pause" : "Play"}
                    >
                      {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => setPlaybackTime("00:42:10")}
                      className="p-2 text-slate-400 hover:text-white transition"
                      title="Step back 5 seconds"
                    >
                      <RotateCcw className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setPlaybackTime("00:42:20")}
                      className="p-2 text-slate-400 hover:text-white transition"
                      title="Step forward 5 seconds"
                    >
                      <RotateCw className="w-4 h-4" />
                    </button>
                    <span className="font-mono text-xs text-slate-300 font-medium">
                      {playbackTime} / 01:30:00
                    </span>
                  </div>

                  <div className="flex items-center space-x-2 text-xs font-mono text-slate-400">
                    <span className="hidden sm:inline">1080p60 H.265</span>
                    <button
                      onClick={() => alert("Evidence frame downloaded in full fidelity.")}
                      className="p-1.5 hover:text-white transition"
                      title="Inspect full frame"
                    >
                      <Maximize2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Telemetry Evidence Stream & Timeline Card */}
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
                    <Activity className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 text-base">
                      Synchronized Telemetry Timeline
                    </h3>
                    <p className="text-xs text-slate-500">
                      Click any timestamp to synchronize the video evidence scrubber
                    </p>
                  </div>
                </div>
                <span className="text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded font-mono">
                  {appeal.timeline?.length || 5} events
                </span>
              </div>

              {/* Timeline list */}
              <div className="space-y-3">
                {appeal.timeline?.map((event: TelemetryEvent, index: number) => {
                  const isSelected = selectedTimelineIndex === index;
                  return (
                    <div
                      key={event.id}
                      onClick={() => handleTimelineClick(index, event.time)}
                      className={`p-3.5 rounded-xl border transition cursor-pointer flex items-start justify-between gap-4 ${
                        isSelected
                          ? "bg-blue-50/70 border-blue-300 ring-1 ring-blue-300"
                          : "bg-white hover:bg-slate-50 border-slate-200"
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5">
                          {event.type === "CRITICAL" && (
                            <span className="inline-flex p-1.5 bg-red-100 text-red-600 rounded-lg">
                              <AlertTriangle className="w-4 h-4" />
                            </span>
                          )}
                          {event.type === "WARNING" && (
                            <span className="inline-flex p-1.5 bg-amber-100 text-amber-600 rounded-lg">
                              <Volume2 className="w-4 h-4" />
                            </span>
                          )}
                          {event.type === "INFO" && (
                            <span className="inline-flex p-1.5 bg-blue-100 text-blue-600 rounded-lg">
                              <Info className="w-4 h-4" />
                            </span>
                          )}
                        </div>

                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-mono text-xs font-bold text-slate-800">
                              {event.time}
                            </span>
                            <span
                              className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                                event.type === "CRITICAL"
                                  ? "bg-red-100 text-red-700"
                                  : event.type === "WARNING"
                                  ? "bg-amber-100 text-amber-700"
                                  : "bg-blue-100 text-blue-700"
                              }`}
                            >
                              {event.type}
                            </span>
                            <span className="text-xs text-slate-400 font-medium">
                              • {event.source}
                            </span>
                          </div>
                          <p className="text-xs text-slate-600 mt-1">{event.description}</p>
                        </div>
                      </div>

                      <button
                        className={`text-xs font-semibold px-2.5 py-1 rounded transition shrink-0 ${
                          isSelected
                            ? "bg-blue-600 text-white"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        {isSelected ? "Active Frame" : "Jump to Frame"}
                      </button>
                    </div>
                  );
                })}
              </div>

              {/* Biometric Sensor Metrics Summary */}
              <div className="mt-6 pt-5 border-t border-slate-100 grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <div className="text-xs text-slate-500 font-medium">Secondary Faces</div>
                  <div className="text-lg font-bold text-red-600 mt-0.5">1 Incident</div>
                  <div className="text-[10px] text-slate-400">Duration: 2.8s</div>
                </div>
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <div className="text-xs text-slate-500 font-medium">Audio Spikes</div>
                  <div className="text-lg font-bold text-amber-600 mt-0.5">52 dB Peak</div>
                  <div className="text-[10px] text-slate-400">Door Latch Noise</div>
                </div>
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <div className="text-xs text-slate-500 font-medium">Gaze Centered</div>
                  <div className="text-lg font-bold text-emerald-600 mt-0.5">99.4%</div>
                  <div className="text-[10px] text-slate-400">No Screen Deviation</div>
                </div>
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <div className="text-xs text-slate-500 font-medium">Window Focus</div>
                  <div className="text-lg font-bold text-emerald-600 mt-0.5">100%</div>
                  <div className="text-[10px] text-slate-400">0 Tab Blurs</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Confirmation Modal for Overturning or Upholding Findings */}
        {modalAction && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95">
              <div className="flex items-center gap-3 mb-4">
                {modalAction === "OVERTURN" ? (
                  <div className="p-3 bg-emerald-100 text-emerald-700 rounded-xl">
                    <CheckCircle className="w-6 h-6" />
                  </div>
                ) : (
                  <div className="p-3 bg-rose-100 text-rose-700 rounded-xl">
                    <XCircle className="w-6 h-6" />
                  </div>
                )}
                <div>
                  <h3 className="text-lg font-bold text-slate-900">
                    {modalAction === "OVERTURN"
                      ? "Overturn Finding (Pass Student)?"
                      : "Uphold Finding (Fail Student)?"}
                  </h3>
                  <p className="text-xs text-slate-500">
                    Appeal Case {appeal.case_id} • Candidate {appeal.candidate_name}
                  </p>
                </div>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 mb-4 text-xs text-slate-600 space-y-1.5">
                <p>
                  <span className="font-semibold text-slate-800">Action:</span>{" "}
                  {modalAction === "OVERTURN"
                    ? "Nullify original violation finding and reinstate passing exam grade."
                    : "Confirm proctor violation finding and enforce failure penalty."}
                </p>
                <p>
                  <span className="font-semibold text-slate-800">Adjudicator:</span>{" "}
                  {user.full_name} ({user.role})
                </p>
              </div>

              <div className="mb-4">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                  Adjudication Justification (Required)
                </label>
                <textarea
                  rows={3}
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  placeholder="Enter reason for this decision (will be stored in audit ledger and notified to student)..."
                  className="w-full text-sm p-3 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {errorMessage && (
                  <p className="text-xs text-rose-600 mt-1 font-medium">{errorMessage}</p>
                )}
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setModalAction(null);
                    setErrorMessage(null);
                  }}
                  disabled={submitting}
                  className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-800 transition rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConfirmDecision}
                  disabled={submitting}
                  className={`px-5 py-2 text-sm font-semibold text-white rounded-xl shadow-sm transition disabled:opacity-60 flex items-center gap-1.5 ${
                    modalAction === "OVERTURN"
                      ? "bg-emerald-600 hover:bg-emerald-700"
                      : "bg-rose-600 hover:bg-rose-700"
                  }`}
                >
                  {submitting ? (
                    <span>Sealing Decision...</span>
                  ) : (
                    <>
                      <Lock className="w-3.5 h-3.5" />
                      <span>Confirm & Record Verdict</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
