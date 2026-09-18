"use client";

import React, { useEffect, useRef, useState } from "react";
import * as tf from "@tensorflow/tfjs";
import * as blazeface from "@tensorflow-models/blazeface";

interface FaceTrackerProps {
  onEventDetected: (eventType: string, details: any) => void;
  enabled: boolean;
}

export default function FaceTracker({ onEventDetected, enabled }: FaceTrackerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [model, setModel] = useState<blazeface.BlazeFaceModel | null>(null);
  const [error, setError] = useState<string | null>(null);
  const isTracking = useRef(false);

  useEffect(() => {
    const initModel = async () => {
      try {
        await tf.ready();
        const loadedModel = await blazeface.load();
        setModel(loadedModel);
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
    let trackInterval: any;

    const startCamera = async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play();
        }
        isTracking.current = true;

        trackInterval = setInterval(async () => {
          if (!videoRef.current || !isTracking.current) return;
          if (videoRef.current.readyState < 2) return;

          try {
            const predictions = await model.estimateFaces(videoRef.current, false);
            
            if (predictions.length === 0) {
              onEventDetected("FACE_NOT_DETECTED", { source: "ai_vision", faceCount: 0 });
            } else if (predictions.length > 1) {
              onEventDetected("MULTIPLE_FACES", { source: "ai_vision", faceCount: predictions.length });
            } else {
              // Exactly 1 face, potentially could do head pose estimation here
              onEventDetected("FACE_DETECTED_OK", { source: "ai_vision", faceCount: 1 });
            }
          } catch (e) {
             console.error("Error predicting face", e);
          }
        }, 3000); // Check every 3 seconds
      } catch (err) {
        console.error("Camera access denied", err);
        setError("Camera access is required for proctoring.");
        onEventDetected("CAMERA_DENIED", { source: "browser" });
      }
    };

    startCamera();

    return () => {
      isTracking.current = false;
      if (trackInterval) clearInterval(trackInterval);
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [enabled, model]);

  if (!enabled) return null;

  return (
    <div className="relative overflow-hidden rounded-lg border border-slate-200 bg-slate-900 shadow-sm">
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="w-48 h-36 object-cover opacity-80"
      />
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80 p-2 text-center text-xs text-red-400 font-semibold">
          {error}
        </div>
      )}
      {!model && !error && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/50 p-2 text-center text-xs text-slate-300">
          Loading AI Model...
        </div>
      )}
      <div className="absolute bottom-1 right-1 flex items-center gap-1.5 bg-black/60 rounded px-1.5 py-0.5">
        <div className={`w-2 h-2 rounded-full ${model && !error ? "bg-green-500 animate-pulse" : "bg-slate-500"}`} />
        <span className="text-[10px] text-white font-medium uppercase tracking-wider">AI Proctor</span>
      </div>
    </div>
  );
}
