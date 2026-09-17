"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Mic, Video, VideoOff, MicOff, PhoneOff, MessageSquare, Shield, AlertCircle } from "lucide-react";

export default function LiveInterviewExam() {
  const params = useParams();
  const router = useRouter();
  const examId = params.id as string;
  
  const [isMicOn, setIsMicOn] = useState(true);
  const [isVideoOn, setIsVideoOn] = useState(true);
  const [connectionStatus, setConnectionStatus] = useState("Connecting to secure room...");
  
  useEffect(() => {
    // Simulate WebRTC connection sequence
    const timer1 = setTimeout(() => setConnectionStatus("Verifying identity & AI proctoring..."), 1500);
    const timer2 = setTimeout(() => setConnectionStatus("Connected to Interviewer"), 3500);
    
    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
    };
  }, []);

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-200 font-sans overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-slate-900 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white">Live Technical Interview</h1>
            <p className="text-xs text-slate-400">Exam ID: {examId}</p>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold ${
            connectionStatus.includes("Connected") ? "bg-emerald-500/20 text-emerald-400" : "bg-amber-500/20 text-amber-400"
          }`}>
            <span className={`w-2 h-2 rounded-full animate-pulse ${
              connectionStatus.includes("Connected") ? "bg-emerald-500" : "bg-amber-500"
            }`}></span>
            {connectionStatus}
          </div>
          <div className="px-3 py-1 bg-slate-800 rounded text-xs font-mono text-slate-300">
            00:14:32
          </div>
        </div>
      </header>

      <main className="flex-1 flex gap-4 p-4 overflow-hidden">
        {/* Main Video Area (Interviewer) */}
        <div className="flex-1 bg-slate-900 border border-slate-800 rounded-xl relative overflow-hidden flex flex-col shadow-2xl">
          {connectionStatus.includes("Connected") ? (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-800">
              <div className="text-center">
                <div className="w-24 h-24 bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4 border-4 border-slate-600">
                  <UserAvatar />
                </div>
                <h2 className="text-lg font-semibold text-white">Dr. Sarah Jenkins</h2>
                <p className="text-slate-400 text-sm">Lead Technical Assessor</p>
              </div>
            </div>
          ) : (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
          )}
          
          <div className="absolute top-4 left-4 bg-black/50 backdrop-blur px-3 py-1.5 rounded-lg border border-white/10 flex items-center gap-2">
             <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
             <span className="text-xs font-semibold text-white">REC</span>
          </div>

          {/* Self View (Candidate PIP) */}
          <div className="absolute bottom-6 right-6 w-64 aspect-video bg-slate-800 border-2 border-slate-700 rounded-lg overflow-hidden shadow-2xl">
             {isVideoOn ? (
               <div className="w-full h-full bg-slate-700 flex items-center justify-center relative">
                  <span className="text-slate-500 text-sm">Your Camera</span>
                  <div className="absolute top-2 left-2 bg-emerald-500/90 backdrop-blur px-2 py-0.5 rounded text-[10px] font-bold text-white uppercase tracking-wider shadow-sm">
                    AI Face Match
                  </div>
               </div>
             ) : (
               <div className="w-full h-full flex flex-col items-center justify-center bg-slate-800">
                 <VideoOff className="w-8 h-8 text-slate-500 mb-2" />
                 <span className="text-xs text-slate-500">Camera Disabled</span>
               </div>
             )}
          </div>
        </div>

        {/* Right Sidebar (Real-time Transcription & Rubric) */}
        <div className="w-96 flex flex-col gap-4">
          <div className="flex-1 bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col shadow-xl">
            <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-indigo-400" />
              Live Transcription (Whisper AI)
            </h3>
            
            <div className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
               <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/50">
                 <p className="text-xs font-semibold text-indigo-400 mb-1">Interviewer</p>
                 <p className="text-sm text-slate-300">Welcome to the technical interview. Can you start by explaining how you would optimize a highly concurrent database system?</p>
               </div>
               
               <div className="bg-indigo-900/20 p-3 rounded-lg border border-indigo-500/20 ml-4">
                 <p className="text-xs font-semibold text-emerald-400 mb-1">You</p>
                 <p className="text-sm text-slate-300">Certainly. I would first look at the indexing strategy and query execution plans to identify bottlenecks...</p>
               </div>
               
               <div className="flex items-center gap-2 text-slate-500 mt-2">
                 <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce"></span>
                 <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce delay-75"></span>
                 <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce delay-150"></span>
               </div>
            </div>
          </div>
          
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl">
             <div className="flex items-start gap-3 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                <AlertCircle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-semibold text-amber-500">Proctoring Active</h4>
                  <p className="text-xs text-slate-400 mt-1">Eye tracking and audio analysis are active. Please maintain focus on the screen.</p>
                </div>
             </div>
          </div>
        </div>
      </main>

      {/* Control Bar */}
      <footer className="h-20 bg-slate-900 border-t border-slate-800 flex items-center justify-center gap-6">
        <button 
          onClick={() => setIsMicOn(!isMicOn)}
          className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${
            isMicOn ? "bg-slate-800 hover:bg-slate-700 text-white" : "bg-red-500/20 text-red-500 border border-red-500/50"
          }`}
        >
          {isMicOn ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5" />}
        </button>
        
        <button 
          onClick={() => setIsVideoOn(!isVideoOn)}
          className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${
            isVideoOn ? "bg-slate-800 hover:bg-slate-700 text-white" : "bg-red-500/20 text-red-500 border border-red-500/50"
          }`}
        >
          {isVideoOn ? <Video className="w-5 h-5" /> : <VideoOff className="w-5 h-5" />}
        </button>
        
        <div className="w-px h-8 bg-slate-800 mx-2"></div>
        
        <button 
          onClick={() => router.push("/dashboard")}
          className="w-12 h-12 rounded-full bg-red-600 hover:bg-red-500 text-white flex items-center justify-center transition-all shadow-lg shadow-red-600/20"
        >
          <PhoneOff className="w-5 h-5" />
        </button>
      </footer>
    </div>
  );
}

function UserAvatar() {
  return (
    <svg className="w-12 h-12 text-slate-500" fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
    </svg>
  );
}
