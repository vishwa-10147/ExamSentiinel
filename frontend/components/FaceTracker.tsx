"use client";

import React, { useEffect, useRef, useState } from "react";
import * as tf from "@tensorflow/tfjs";
import * as blazeface from "@tensorflow-models/blazeface";
import { apiClient } from "@/services/apiClient";

export type FaceSignal = "FACE_NOT_DETECTED" | "MULTIPLE_FACES" | "CAMERA_DENIED";

/** Result of server-side frame analysis (phone / extra-person detection). */
export interface FrameAnalysis {
  recorded: boolean;
  violation_count: number;
  is_terminated: boolean;
  risk_level: string;
  signals: { event_type: string; details: Record<string, unknown> }[];
}

interface FaceTrackerProps {
  /** Fired when the in-browser face check changes state (debounced). */
  onEventDetected: (eventType: FaceSignal, details: Record<string, unknown>) => void;
  /** Fired after the server analyses a frame and records new signals. */
  onAnalysis?: (result: FrameAnalysis) => void;
  enabled: boolean;
  sessionId?: string;
}

const FACE_CHECK_MS = 3000; // in-browser BlazeFace face count
const ANALYZE_MS = 10000; // server-side YOLO phone / person detection
const LIVE_SNAPSHOT_MS = 30000; // thumbnail for the proctor's live grid
const REPEAT_MS = 30000; // re-report a persisting problem at most this often

function captureJpeg(video: HTMLVideoElement, quality: number): Promise<Blob | null> {
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  canvas.getContext("2d")?.drawImage(video, 0, 0, canvas.width, canvas.height);
  return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", quality));
}

export default function FaceTracker({ onEventDetected, onAnalysis, enabled, sessionId }: FaceTrackerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [model, setModel] = useState<blazeface.BlazeFaceModel | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const isTracking = useRef(false);
  const onEventDetectedRef = useRef(onEventDetected);
  const onAnalysisRef = useRef(onAnalysis);
  const sessionIdRef = useRef(sessionId);
  // Last reported face state and when it was reported, for debouncing.
  const faceState = useRef<{ state: "ok" | FaceSignal; reportedAt: number }>({ state: "ok", reportedAt: 0 });

  useEffect(() => {
    onEventDetectedRef.current = onEventDetected;
    onAnalysisRef.current = onAnalysis;
    sessionIdRef.current = sessionId;
  }, [onEventDetected, onAnalysis, sessionId]);

  useEffect(() => {
    const initModel = async () => {
      try {
        await tf.ready();
        setModel(await blazeface.load());
      } catch (err) {
        console.error("Failed to load BlazeFace model", err);
        setError("Failed to load AI tracking model.");
      }
    };
    initModel();
  }, []);

  useEffect(() => {
    if (!enabled || !model) return;

    let stream: MediaStream | null = null;
    const timers: ReturnType<typeof setInterval>[] = [];

    const reportFaceState = (next: "ok" | FaceSignal, details: Record<string, unknown>) => {
      const now = Date.now();
      const prev = faceState.current;
      if (next === "ok") {
        faceState.current = { state: "ok", reportedAt: now };
        setWarning(null);
        return;
      }
      setWarning(next === "MULTIPLE_FACES" ? "More than one person detected" : "Face not visible");
      // Report on change, then at most once per REPEAT_MS while it persists.
      if (prev.state !== next || now - prev.reportedAt >= REPEAT_MS) {
        faceState.current = { state: next, reportedAt: now };
        onEventDetectedRef.current(next, { source: "ai_vision", ...details });
      }
    };

    const startCamera = async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          void videoRef.current.play();
        }
        isTracking.current = true;

        // 1. In-browser face count (fast feedback, no upload).
        timers.push(
          setInterval(async () => {
            const video = videoRef.current;
            if (!video || !isTracking.current || video.readyState < 2) return;
            try {
              const predictions = await model.estimateFaces(video, false);
              if (predictions.length === 0) reportFaceState("FACE_NOT_DETECTED", { faceCount: 0 });
              else if (predictions.length > 1) reportFaceState("MULTIPLE_FACES", { faceCount: predictions.length });
              else reportFaceState("ok", {});
            } catch (e) {
              console.error("Error predicting face", e);
            }
          }, FACE_CHECK_MS)
        );

        // 2. Server-side analysis: phones and extra people (YOLO).
        timers.push(
          setInterval(async () => {
            const video = videoRef.current;
            if (!sessionIdRef.current || !video || !isTracking.current || video.readyState < 2) return;
            const blob = await captureJpeg(video, 0.7);
            if (!blob) return;
            const form = new FormData();
            form.append("frame", blob, "frame.jpg");
            try {
              const result = await apiClient.upload<FrameAnalysis>(
                `/api/proctoring/sessions/${sessionIdRef.current}/webcam/analyze`,
                form
              );
              if (result.signals.some((s) => s.event_type === "PHONE_DETECTED")) setWarning("Phone detected");
              if (result.recorded) onAnalysisRef.current?.(result);
            } catch {
              // Analysis is best-effort; the in-browser check keeps running.
            }
          }, ANALYZE_MS)
        );

        // 3. Low-rate thumbnail so proctors can see the candidate.
        timers.push(
          setInterval(async () => {
            const video = videoRef.current;
            if (!sessionIdRef.current || !video || !isTracking.current || video.readyState < 2) return;
            const canvas = document.createElement("canvas");
            canvas.width = video.videoWidth || 640;
            canvas.height = video.videoHeight || 480;
            canvas.getContext("2d")?.drawImage(video, 0, 0, canvas.width, canvas.height);
            try {
              await apiClient.post(`/api/proctoring/evidence/${sessionIdRef.current}`, {
                image_base64: canvas.toDataURL("image/jpeg", 0.6),
                event_type: "FACE_DETECTED_OK",
                metadata: { source: "ai_vision", capture_type: "periodic_frame" },
              });
            } catch {
              console.warn("Camera snapshot upload failed");
            }
          }, LIVE_SNAPSHOT_MS)
        );
      } catch (err) {
        console.error("Camera access denied", err);
        setError("Camera access is required for proctoring.");
        onEventDetectedRef.current("CAMERA_DENIED", { source: "browser" });
      }
    };

    void startCamera();

    return () => {
      isTracking.current = false;
      timers.forEach(clearInterval);
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, [enabled, model]);

  if (!enabled) return null;

  return (
    <div className="relative overflow-hidden rounded-lg border border-slate-200 bg-slate-900 shadow-sm">
      <video ref={videoRef} autoPlay playsInline muted className="h-36 w-48 object-cover opacity-80" />
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80 p-2 text-center text-xs font-semibold text-red-400">
          {error}
        </div>
      )}
      {!model && !error && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/50 p-2 text-center text-xs text-slate-300">
          Loading AI Model...
        </div>
      )}
      {warning && !error && (
        <div className="absolute inset-x-0 top-0 bg-red-600/90 px-2 py-0.5 text-center text-[10px] font-semibold uppercase tracking-wide text-white" role="status">
          {warning}
        </div>
      )}
      <div className="absolute bottom-1 right-1 flex items-center gap-1.5 rounded bg-black/60 px-1.5 py-0.5">
        <div className={`h-2 w-2 rounded-full ${model && !error ? "animate-pulse bg-green-500" : "bg-slate-500"}`} />
        <span className="text-[10px] font-medium uppercase tracking-wider text-white">AI Proctor</span>
      </div>
    </div>
  );
}
