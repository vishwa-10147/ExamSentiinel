"use client";
export const dynamic = "force-dynamic";

import React, { useRef, useState, useEffect, useCallback } from "react";
import { apiClient } from "@/services/apiClient";
import { Camera, RefreshCw, AlertTriangle, CheckCircle, Shield, Play, Square, Cpu } from "lucide-react";

interface AIAnalysisSummary {
  face_detected: boolean;
  multiple_faces: boolean;
  phone_detected: boolean;
  faces_found?: number;
  raw_detections: Array<{ event_type: string | null; details: any }>;
}

export default function AITestDashboard() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  const [streamActive, setStreamActive] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [autoStream, setAutoStream] = useState(false);
  const [results, setResults] = useState<AIAnalysisSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const videoElement = videoRef.current;
    return () => {
      if (videoElement?.srcObject) {
        const stream = videoElement.srcObject as MediaStream;
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: { ideal: 640 }, height: { ideal: 480 } } 
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setStreamActive(true);
        setError(null);
      }
    } catch (err: any) {
      console.error("Camera access error", err);
      setError("Could not access webcam. Please ensure camera permissions are granted.");
    }
  };

  const stopCamera = () => {
    if (videoRef.current?.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach(track => track.stop());
      videoRef.current.srcObject = null;
    }
    setStreamActive(false);
    setAutoStream(false);
  };

  const captureAndAnalyze = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current || analyzing) return;
    
    setAnalyzing(true);
    setError(null);
    
    try {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (video.videoWidth === 0 || video.videoHeight === 0) {
        setAnalyzing(false);
        return;
      }

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("Could not initialize canvas context");
      
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      
      canvas.toBlob(async (blob) => {
        if (!blob) {
          setAnalyzing(false);
          return;
        }
        
        const formData = new FormData();
        formData.append("frame", blob, "frame.jpg");
        
        try {
          const response = await apiClient.post<{ success: boolean; detections: Array<{ event_type: string | null; details: any }> }>(
            "/api/proctoring/dev/analyze-frame", 
            formData
          );

          const rawDetections = response.detections || [];
          
          const faceNotDetected = rawDetections.some(d => d.event_type === "FACE_NOT_DETECTED");
          const multipleFacesEvent = rawDetections.find(d => d.event_type === "MULTIPLE_FACES");
          const phoneDetected = rawDetections.some(d => d.event_type === "PHONE_DETECTED");
          
          // YOLO reports people_found; the Haar fallback reports faces_found.
          const facesFound =
            multipleFacesEvent?.details?.people_found ?? multipleFacesEvent?.details?.faces_found ?? (faceNotDetected ? 0 : 1);

          setResults({
            face_detected: !faceNotDetected,
            multiple_faces: Boolean(multipleFacesEvent),
            phone_detected: phoneDetected,
            faces_found: facesFound,
            raw_detections: rawDetections,
          });
        } catch(e: any) {
          console.error("Frame analysis failed", e);
          setError(e.message || "Failed to analyze frame with backend AI engine.");
        } finally {
          setAnalyzing(false);
        }
      }, "image/jpeg", 0.85);
      
    } catch (e: any) {
      setError(e.message);
      setAnalyzing(false);
    }
  }, [analyzing]);

  // Interval for continuous AI live stream mode
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    if (autoStream && streamActive) {
      interval = setInterval(() => {
        void captureAndAnalyze();
      }, 1500);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoStream, streamActive, captureAndAnalyze]);

  return (
    <div className="flex-1 w-full bg-slate-50 dark:bg-slate-900">
      <div className="flex-1 p-6 sm:p-8 max-w-5xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex items-center space-x-3 border-b border-slate-200 dark:border-slate-700 pb-5">
          <div className="p-3 bg-indigo-100 dark:bg-indigo-500/20 rounded-xl">
            <Cpu className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">AI Vision Testing Sandbox</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">Live testing suite for OpenCV Face Recognition & YOLO Object Detection</p>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 text-red-700 dark:text-red-400 rounded-xl flex items-center text-sm">
            <AlertTriangle className="w-5 h-5 mr-2 shrink-0" />
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Camera Feed Card */}
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden flex flex-col">
            <div className="p-4 border-b border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 flex justify-between items-center">
              <h3 className="font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2 text-sm">
                <Camera className="w-4 h-4 text-indigo-600 dark:text-indigo-400" /> Live Webcam Feed
              </h3>
              
              <div className="flex gap-2">
                {!streamActive ? (
                  <button 
                    onClick={startCamera}
                    className="px-3.5 py-1.5 bg-indigo-600 text-white text-xs font-semibold rounded-lg hover:bg-indigo-500 transition cursor-pointer"
                  >
                    Start Camera
                  </button>
                ) : (
                  <>
                    <button 
                      onClick={() => setAutoStream(!autoStream)}
                      className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition flex items-center gap-1 ${
                        autoStream 
                          ? "bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-300 dark:border-amber-500/30" 
                          : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-700 hover:bg-slate-200"
                      }`}
                    >
                      {autoStream ? <Square className="w-3 h-3 fill-amber-700" /> : <Play className="w-3 h-3 fill-slate-700" />}
                      {autoStream ? "Live AI Active" : "Auto AI Mode"}
                    </button>
                    
                    <button 
                      onClick={captureAndAnalyze}
                      disabled={analyzing}
                      className="px-3.5 py-1.5 bg-indigo-600 text-white text-xs font-semibold rounded-lg hover:bg-indigo-500 disabled:opacity-50 flex items-center gap-1 transition cursor-pointer"
                    >
                      {analyzing ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : null}
                      {analyzing ? "Analyzing..." : "Analyze Frame"}
                    </button>

                    <button 
                      onClick={stopCamera}
                      className="px-3 py-1.5 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold rounded-lg hover:bg-slate-300 transition"
                    >
                      Stop
                    </button>
                  </>
                )}
              </div>
            </div>

            <div className="aspect-video bg-slate-900 relative flex items-center justify-center overflow-hidden">
              <video 
                ref={videoRef} 
                autoPlay 
                playsInline 
                muted 
                className="w-full h-full object-cover"
              />
              {!streamActive && (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500 dark:text-slate-400 gap-2">
                  <Camera className="w-10 h-10 opacity-40" />
                  <span className="text-xs font-medium">Webcam Disconnected</span>
                </div>
              )}
              {autoStream && (
                <div className="absolute top-3 left-3 bg-red-600/90 text-white px-2.5 py-1 rounded-md text-[11px] font-bold flex items-center gap-1.5 backdrop-blur-sm">
                  <span className="w-2 h-2 rounded-full bg-white dark:bg-slate-800 animate-pulse"></span>
                  LIVE AI PROCTORING
                </div>
              )}
            </div>
            <canvas ref={canvasRef} className="hidden" />
          </div>

          {/* Results View Card */}
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-6 flex flex-col">
            <h3 className="font-bold text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-700 pb-3 mb-4 text-sm flex items-center justify-between">
              <span>AI Vision Engine Output</span>
              {analyzing && <span className="text-xs text-indigo-600 dark:text-indigo-400 animate-pulse font-normal">Processing frame...</span>}
            </h3>
            
            {!results ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400 border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-xl">
                <Shield className="w-10 h-10 mb-2 text-slate-300" />
                <p className="text-xs font-medium">Start camera & click &apos;Analyze Frame&apos; or enable &apos;Auto AI Mode&apos;</p>
              </div>
            ) : (
              <div className="space-y-3 flex-1 flex flex-col justify-between">
                
                {/* Face Detection Status */}
                <div className={`p-3.5 rounded-xl border transition ${results.face_detected ? 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30 text-emerald-800 dark:text-emerald-300 dark:text-emerald-300' : 'bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/30 text-red-800 dark:text-red-300 dark:text-red-300'}`}>
                  <div className="flex items-center justify-between font-bold text-sm">
                    <span className="flex items-center gap-2">
                      {results.face_detected ? <CheckCircle className="w-4 h-4 text-emerald-600 dark:text-emerald-400" /> : <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400" />}
                      Face Recognition
                    </span>
                    <span className="text-xs font-mono">
                      {results.face_detected ? `${results.faces_found || 1} Face Detected` : "No Face Detected"}
                    </span>
                  </div>
                </div>
                
                {/* Multiple Faces Imposter Status */}
                <div className={`p-3.5 rounded-xl border transition ${results.multiple_faces ? 'bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/30 text-red-800 dark:text-red-300 dark:text-red-300' : 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30 text-emerald-800 dark:text-emerald-300 dark:text-emerald-300'}`}>
                  <div className="flex items-center justify-between font-bold text-sm">
                    <span className="flex items-center gap-2">
                      {results.multiple_faces ? <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400" /> : <CheckCircle className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />}
                      Imposter Detection (Multiple Faces)
                    </span>
                    <span className="text-xs font-mono">
                      {results.multiple_faces ? `FLAGGED (${results.faces_found} Faces)` : "PASSED (Single Face)"}
                    </span>
                  </div>
                </div>

                {/* Mobile Phone Status */}
                <div className={`p-3.5 rounded-xl border transition ${results.phone_detected ? 'bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/30 text-red-800 dark:text-red-300 dark:text-red-300' : 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30 text-emerald-800 dark:text-emerald-300 dark:text-emerald-300'}`}>
                  <div className="flex items-center justify-between font-bold text-sm">
                    <span className="flex items-center gap-2">
                      {results.phone_detected ? <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400" /> : <CheckCircle className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />}
                      Object Detection (Mobile Phone)
                    </span>
                    <span className="text-xs font-mono">
                      {results.phone_detected ? "FLAGGED (Phone Detected)" : "PASSED (No Phone)"}
                    </span>
                  </div>
                </div>

                {/* Raw JSON Debug */}
                <div className="mt-4 pt-2">
                  <h4 className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">Raw Backend AI Response</h4>
                  <pre className="bg-slate-900 text-emerald-400 p-3 rounded-xl text-[11px] font-mono overflow-auto h-28 border border-slate-800">
                    {JSON.stringify(results.raw_detections, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
