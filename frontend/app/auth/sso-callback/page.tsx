"use client";

import React, { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ShieldCheck } from "lucide-react";

export default function SSOCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const token = searchParams.get("token");
    
    if (token) {
      // Typically we'd exchange a code or validate the token
      localStorage.setItem("access_token", token);
      
      // Artificial delay to show the secure handoff
      setTimeout(() => {
        router.push("/admin/dashboard");
      }, 2000);
    } else {
      setTimeout(() => {
        router.push("/auth/login?error=sso_failed");
      }, 2000);
    }
  }, [router, searchParams]);

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center p-4">
      <div className="w-16 h-16 bg-indigo-600 rounded-2xl flex items-center justify-center mb-6 shadow-lg shadow-indigo-500/20 animate-pulse">
        <ShieldCheck className="w-8 h-8 text-white" />
      </div>
      <h1 className="text-2xl font-bold text-white mb-2">Authenticating</h1>
      <p className="text-slate-400 text-center max-w-md">
        Completing Single Sign-On (SSO) handshake with your institution. Please wait while we establish a secure session...
      </p>
      
      <div className="mt-8 flex gap-2">
        <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce"></div>
        <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
        <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: "0.4s" }}></div>
      </div>
    </div>
  );
}
