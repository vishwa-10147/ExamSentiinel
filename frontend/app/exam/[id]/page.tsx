"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import {
  CandidateResponse,
  examService,
  QuestionCandidate,
  SessionState,
} from "@/services/examService";
import { AutoSaveIndicator, SaveStatus } from "@/components/exam/AutoSaveIndicator";
import { TimerBanner } from "@/components/exam/TimerBanner";
import { QuestionPalette } from "@/components/exam/QuestionPalette";
import { QuestionCard } from "@/components/exam/QuestionCard";
import { SubmitModal } from "@/components/exam/SubmitModal";
import FaceTracker from "@/components/FaceTracker";
import { proctoringService } from "@/services/proctoringService";

export default function ExamTakingPage() {
  const params = useParams();
  const examId = params.id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [session, setSession] = useState<SessionState | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Active question index
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState<number>(0);

  // Responses state map: question_id -> CandidateResponse
  const [responses, setResponses] = useState<Record<string, CandidateResponse>>({});

  // Auto-save state
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("saved");
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const sequenceCounters = useRef<Record<string, number>>({});
  const debounceTimers = useRef<Record<string, NodeJS.Timeout>>({});

  // Submit Modal
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isSubmitted, setIsSubmitted] = useState<boolean>(false);

  // Integrity warning flags
  const [blurWarning, setBlurWarning] = useState<boolean>(false);

  // Load / Start Session
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/auth/login");
      return;
    }

    if (examId) {
      examService
        .startSession(examId)
        .then((sessionData) => {
          setSession(sessionData);
          setResponses(sessionData.responses || {});

          // Initialize sequence counters
          const initSeq: Record<string, number> = {};
          Object.values(sessionData.responses || {}).forEach((r) => {
            initSeq[r.question_id] = r.sequence_id || 1;
          });
          sequenceCounters.current = initSeq;

          if (sessionData.status === "SUBMITTED") {
            setIsSubmitted(true);
          }
          setLoading(false);
        })
        .catch((err) => {
          setError(err.message || "Failed to initialize exam session.");
          setLoading(false);
        });
    }
  }, [examId, isAuthenticated, authLoading, router]);

  const submitTelemetry = useCallback(
    (eventType: Parameters<typeof proctoringService.submitEvent>[1], details: Record<string, unknown> = {}) => {
      if (!session || isSubmitted) return;
      void proctoringService.submitEvent(session.session_id, eventType, details).catch(() => undefined);
    },
    [session, isSubmitted]
  );

  useEffect(() => {
    const handleBlur = () => {
      setBlurWarning(true);
      submitTelemetry("TAB_BLUR");
    };
    const handleFocus = () => {
      submitTelemetry("TAB_FOCUS");
      setTimeout(() => setBlurWarning(false), 4000);
    };
    const handleFullscreenChange = () => {
      if (!document.fullscreenElement) submitTelemetry("FULLSCREEN_EXIT");
    };
    const handleCopy = () => submitTelemetry("COPY_ATTEMPT");
    const handlePaste = (event: ClipboardEvent) => {
      submitTelemetry("PASTE_ATTEMPT", {
        text_length: event.clipboardData?.getData("text").length || 0,
      });
    };
    const handleContextMenu = (event: MouseEvent) => {
      event.preventDefault();
      submitTelemetry("RIGHT_CLICK");
    };
    const handleResize = () => {
      submitTelemetry("RESIZE", { width: window.innerWidth, height: window.innerHeight });
    };
    
    const handleOffline = () => {
      setSaveStatus("offline");
      submitTelemetry("NETWORK_DISCONNECT");
    };
    
    const handleOnline = async () => {
      submitTelemetry("NETWORK_RECONNECT");
      // Attempt to sync offline queue
      const queueKey = `offline_answers_${session?.session_id}`;
      const cached = localStorage.getItem(queueKey);
      if (cached) {
        setSaveStatus("saving");
        try {
          const queue = JSON.parse(cached);
          for (const item of queue) {
            await examService.saveAnswer(session!.session_id, item);
          }
          localStorage.removeItem(queueKey);
          setSaveStatus("saved");
        } catch(e) {
          console.error("Failed to sync offline answers", e);
          setSaveStatus("offline");
        }
      }
    };


    window.addEventListener("blur", handleBlur);
    window.addEventListener("focus", handleFocus);
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    document.addEventListener("copy", handleCopy);
    document.addEventListener("paste", handlePaste);
    document.addEventListener("contextmenu", handleContextMenu);
    window.addEventListener("resize", handleResize);
    window.addEventListener("offline", handleOffline);
    window.addEventListener("online", handleOnline);
    return () => {
      window.removeEventListener("blur", handleBlur);
      window.removeEventListener("focus", handleFocus);
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      document.removeEventListener("copy", handleCopy);
      document.removeEventListener("paste", handlePaste);
      document.removeEventListener("contextmenu", handleContextMenu);
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("online", handleOnline);
    };
  }, [submitTelemetry]);

  // Debounced Answer Auto-Saver
  const queueSave = useCallback(
    (questionId: string, responseData: any, isFlagged?: boolean) => {
      if (!session || isSubmitted) return;

      setSaveStatus("saving");

      // Increment sequence ID for Last-Write-Wins
      const nextSeq = (sequenceCounters.current[questionId] || 0) + 1;
      sequenceCounters.current[questionId] = nextSeq;

      // Update local state immediately for snappy UI
      setResponses((prev) => ({
        ...prev,
        [questionId]: {
          question_id: questionId,
          response_data: responseData,
          is_flagged: isFlagged !== undefined ? isFlagged : (prev[questionId]?.is_flagged || false),
          sequence_id: nextSeq,
          server_timestamp: new Date().toISOString(),
        },
      }));

      // Clear existing debounce timer for this question
      if (debounceTimers.current[questionId]) {
        clearTimeout(debounceTimers.current[questionId]);
      }

      debounceTimers.current[questionId] = setTimeout(async () => {
        try {
          const result = await examService.saveAnswer(session.session_id, {
            question_id: questionId,
            response_data: responseData,
            sequence_id: nextSeq,
            is_flagged: isFlagged,
          });

          setSaveStatus("saved");
          setLastSavedAt(new Date(result.server_timestamp || Date.now()));
        } catch (err: any) {
          console.error("Auto-save error:", err);
          setSaveStatus("offline");
          // Queue offline
          if (session?.session_id) {
            const queueKey = `offline_answers_${session.session_id}`;
            const existing = JSON.parse(localStorage.getItem(queueKey) || "[]");
            existing.push({
              question_id: questionId,
              response_data: responseData,
              sequence_id: nextSeq,
              is_flagged: isFlagged,
            });
            localStorage.setItem(queueKey, JSON.stringify(existing));
          }
        }
      }, 600); // 600ms debounce
    },
    [session, isSubmitted]
  );

  const handleAnswerChange = (data: any) => {
    if (!session || session.questions.length === 0) return;
    const currentQ = session.questions[currentQuestionIndex];
    queueSave(currentQ.id, data);
  };

  const handleToggleFlag = () => {
    if (!session || session.questions.length === 0) return;
    const currentQ = session.questions[currentQuestionIndex];
    const currentFlag = !!responses[currentQ.id]?.is_flagged;
    const currentData = responses[currentQ.id]?.response_data || {};
    queueSave(currentQ.id, currentData, !currentFlag);
  };

  const handleClearResponse = () => {
    if (!session || session.questions.length === 0) return;
    const currentQ = session.questions[currentQuestionIndex];
    queueSave(currentQ.id, {});
  };

  const handleTimeout = async () => {
    if (isSubmitted || !session) return;
    try {
      await examService.submitSession(session.session_id);
      setIsSubmitted(true);
    } catch {
      setIsSubmitted(true);
    }
  };

  const handleConfirmSubmit = async () => {
    if (!session || isSubmitting) return;
    setIsSubmitting(true);
    try {
      await examService.submitSession(session.session_id);
      setIsSubmitted(true);
      setIsSubmitModalOpen(false);
    } catch (err: any) {
      alert(err.message || "Failed to submit exam session.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading || authLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-300">
        <div className="flex items-center gap-3">
          <svg className="animate-spin h-6 w-6 text-indigo-500" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>Initializing secure examination session...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-2xl p-6 text-center">
          <div className="h-12 w-12 rounded-full bg-red-500/20 text-red-400 flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-lg font-bold text-white mb-2">Exam Launch Issue</h2>
          <p className="text-sm text-slate-400 mb-6">{error}</p>
          <button
            onClick={() => router.push("/dashboard")}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  // Completion Screen
  if (isSubmitted) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="max-w-lg w-full bg-slate-900 border border-slate-800 rounded-3xl p-8 text-center shadow-2xl">
          <div className="h-16 w-16 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-2xl font-extrabold text-white mb-2">Exam Submitted Successfully</h2>
          <p className="text-slate-400 text-sm mb-6">
            Your responses have been securely transmitted and encrypted. The evaluation and human review process is
            now underway.
          </p>

          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-left text-xs space-y-2 mb-6 text-slate-300">
            <div className="flex justify-between">
              <span className="text-slate-500">Exam:</span>
              <span className="font-semibold">{session?.exam_title}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Session ID:</span>
              <span className="font-mono text-slate-400">{session?.session_id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Questions Answered:</span>
              <span className="text-emerald-400 font-semibold">
                {Object.keys(responses).length} of {session?.total_questions}
              </span>
            </div>
          </div>

          <button
            onClick={() => router.push("/exam/completed")}
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-bold transition-all shadow-lg shadow-indigo-600/30"
          >
            Finish & Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const questions = session?.questions || [];
  const currentQuestion = questions[currentQuestionIndex];
  const currentResponse = currentQuestion ? responses[currentQuestion.id] : null;

  const isAnswered = (qId: string) => {
    const resp = responses[qId];
    if (!resp || !resp.response_data) return false;
    const data = resp.response_data;
    if (data.selected_option_id) return true;
    if (Array.isArray(data.selected_option_ids) && data.selected_option_ids.length > 0) return true;
    if (typeof data.text === "string" && data.text.trim().length > 0) return true;
    return false;
  };

  const answeredCount = questions.filter((q) => isAnswered(q.id)).length;
  const flaggedCount = questions.filter((q) => !!responses[q.id]?.is_flagged).length;
  const unansweredCount = questions.length - answeredCount;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Banner Navigation */}
      <header className="bg-slate-900 border-b border-slate-800 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="h-8 w-8 rounded-lg bg-indigo-600 flex items-center justify-center font-black text-white text-sm">
              ES
            </span>
            <div>
              <h1 className="text-sm font-bold text-white truncate max-w-[200px] sm:max-w-md">
                {session?.exam_title}
              </h1>
              <p className="text-[11px] text-slate-400">Exam Sentinel Candidate Environment</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <AutoSaveIndicator status={saveStatus} lastSavedAt={lastSavedAt} />

            {session && (
              <TimerBanner
                initialSeconds={session.remaining_seconds}
                onTimeout={handleTimeout}
                examTitle={session.exam_title}
              />
            )}

            <button
              onClick={() => setIsSubmitModalOpen(true)}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold transition-all shadow-md shadow-emerald-600/30"
            >
              Submit Exam
            </button>
          </div>
        </div>
      </header>

      {/* Blur Warning Notification */}
      {blurWarning && (
        <div className="bg-amber-900/90 border-b border-amber-500 text-amber-200 text-xs px-4 py-2 text-center font-semibold animate-pulse flex items-center justify-center gap-2">
          <svg className="w-4 h-4 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          Warning: Browser focus lost! Switching windows or tabs is recorded as an integrity event.
        </div>
      )}

      {/* Main Workspace Layout */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Question Content (3 cols) */}
        <div className="lg:col-span-3">
          {currentQuestion ? (
            <QuestionCard
              question={currentQuestion}
              index={currentQuestionIndex}
              total={questions.length}
              responseData={currentResponse?.response_data || {}}
              isFlagged={!!currentResponse?.is_flagged}
              onAnswerChange={handleAnswerChange}
              onToggleFlag={handleToggleFlag}
              onClearResponse={handleClearResponse}
              onNext={() => setCurrentQuestionIndex((prev) => Math.min(questions.length - 1, prev + 1))}
              onPrev={() => setCurrentQuestionIndex((prev) => Math.max(0, prev - 1))}
              isFirst={currentQuestionIndex === 0}
              isLast={currentQuestionIndex === questions.length - 1}
            />
          ) : (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-slate-400">
              No questions found in this examination.
            </div>
          )}
        </div>

        {/* Sidebar Palette (1 col) */}
        <div className="lg:col-span-1">
          <QuestionPalette
            questions={questions}
            currentIndex={currentQuestionIndex}
            responses={responses}
            onSelectQuestion={(idx) => setCurrentQuestionIndex(idx)}
          />
        </div>
      </main>

      {/* Submit Confirmation Modal */}
      <SubmitModal
        isOpen={isSubmitModalOpen}
        onClose={() => setIsSubmitModalOpen(false)}
        onConfirmSubmit={handleConfirmSubmit}
        isSubmitting={isSubmitting}
        totalQuestions={questions.length}
        answeredCount={answeredCount}
        unansweredCount={unansweredCount}
        flaggedCount={flaggedCount}
      />
    </div>
  );
}
