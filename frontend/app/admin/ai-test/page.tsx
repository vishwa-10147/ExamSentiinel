"use client";

import { useRef, useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import { apiClient } from "@/services/apiClient";
import { Camera, RefreshCw, AlertTriangle, CheckCircle, Shield } from "lucide-react";

export default function AITestDashboard() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  const [streamActive, setStreamActive] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      // Cleanup video stream on unmount
      if (videoRef.current && videoRef.current.srcObject) {
        const stream = videoRef.current.srcObject as MediaStream;
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setStreamActive(true);
        setError(null);
      }
    } catch (err: any) {
      setError("Could not access webcam. Please grant permissions.");
    }
  };

  const captureAndAnalyze = async () => {
    if (!videoRef.current || !canvasRef.current) return;
    
    setAnalyzing(true);
    setError(null);
    
    try {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("Could not get canvas context");
      
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      
      canvas.toBlob(async (blob) => {
        if (!blob) throw new Error("Could not create image blob");
        
        const formData = new FormData();
        formData.append("frame", blob, "frame.jpg");
        
        try {
          // Send to dev endpoint
          const response = await apiClient.post<any>("/api/proctoring/dev/analyze-frame", formData, {
            headers: { "Content-Type": "multipart/form-data" }
          });
          setResults(response.detections);
        } catch(e: any) {
          setError(e.message || "Failed to analyze frame");
        } finally {
          setAnalyzing(false);
        }
      }, "image/jpeg", 0.9);
      
    } catch (e: any) {
      setError(e.message);
      setAnalyzing(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <div className="flex-1 p-8 overflow-auto">
        <div className="max-w-4xl mx-auto space-y-6">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-indigo-100 rounded-lg">
              <Shield className="w-6 h-6 text-indigo-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">AI Vision Testing Lab</h1>
              <p className="text-slate-500">Developer Sandbox for YOLO Face & Object Detection</p>
            </div>
          </div>

          {error && (
            <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg flex items-center">
              <AlertTriangle className="w-5 h-5 mr-2" />
              {error}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Camera View */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
              <div className="p-4 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
                <h3 className="font-semibold text-slate-800 flex items-center">
                  <Camera className="w-4 h-4 mr-2" /> Live Feed
                </h3>
                {!streamActive ? (
                  <button 
                    onClick={startCamera}
                    className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700"
                  >
                    Start Camera
                  </button>
                ) : (
                  <button 
                    onClick={captureAndAnalyze}
                    disabled={analyzing}
                    className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center"
                  >
                    {analyzing ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : null}
                    {analyzing ? "Analyzing..." : "Analyze Frame"}
                  </button>
                )}
              </div>
              <div className="aspect-video bg-black relative">
                <video 
                  ref={videoRef} 
                  autoPlay 
                  playsInline 
                  muted 
                  className="w-full h-full object-cover"
                />
                {!streamActive && (
                  <div className="absolute inset-0 flex items-center justify-center text-slate-500">
                    Camera Inactive
                  </div>
                )}
              </div>
              <canvas ref={canvasRef} className="hidden" />
            </div>

            {/* Results View */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <h3 className="font-semibold text-slate-800 border-b border-slate-100 pb-4 mb-4">
                AI Telemetry Output
              </h3>
              
              {!results ? (
                <div className="h-48 flex items-center justify-center text-slate-400 border-2 border-dashed border-slate-200 rounded-lg">
                  Click 'Analyze Frame' to generate telemetry
                </div>
              ) : (
                <div className="space-y-4">
                  <div className={`p-4 rounded-lg border ${results.face_detected ? 'bg-green-50 border-green-200 text-green-700' : 'bg-red-50 border-red-200 text-red-700'}`}>
                    <div className="flex items-center justify-between font-semibold">
                      <span>Face Detected</span>
                      {results.face_detected ? <CheckCircle className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
                    </div>
                  </div>
                  
                  <div className={`p-4 rounded-lg border ${results.multiple_faces ? 'bg-red-50 border-red-200 text-red-700' : 'bg-green-50 border-green-200 text-green-700'}`}>
                    <div className="flex items-center justify-between font-semibold">
                      <span>Multiple Faces (Imposter)</span>
                      {results.multiple_faces ? <AlertTriangle className="w-5 h-5" /> : <CheckCircle className="w-5 h-5" />}
                    </div>
                  </div>

                  <div className={`p-4 rounded-lg border ${results.phone_detected ? 'bg-red-50 border-red-200 text-red-700' : 'bg-green-50 border-green-200 text-green-700'}`}>
                    <div className="flex items-center justify-between font-semibold">
                      <span>Mobile Phone / Device</span>
                      {results.phone_detected ? <AlertTriangle className="w-5 h-5" /> : <CheckCircle className="w-5 h-5" />}
                    </div>
                  </div>
                  
                  <div className="mt-6">
                    <h4 className="text-xs font-semibold text-slate-400 uppercase mb-2">Raw JSON Output</h4>
                    <pre className="bg-slate-900 text-green-400 p-4 rounded-lg text-xs overflow-auto h-32">
                      {JSON.stringify(results, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
