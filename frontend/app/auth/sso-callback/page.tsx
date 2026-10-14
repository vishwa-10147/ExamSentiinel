"use client";

import React, { useEffect, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ShieldCheck } from "lucide-react";
import { apiClient } from "@/services/apiClient";

function SSOCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const started = useRef(false); // the ticket is single-use: never redeem it twice (e.g. StrictMode)

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const ticket = searchParams.get("ticket");
    if (!ticket) {
      router.replace("/auth/login?error=sso_failed");
      return;
    }
    apiClient
      .completeSsoLogin(ticket)
      // Full navigation so the auth context loads the new session.
      .then(() => window.location.replace("/dashboard"))
      .catch(() => router.replace("/auth/login?error=sso_failed"));
  }, [router, searchParams]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-900 p-4">
      <div className="mb-6 flex h-16 w-16 animate-pulse items-center justify-center rounded-2xl bg-indigo-600 shadow-lg shadow-indigo-500/20">
        <ShieldCheck className="h-8 w-8 text-white" />
      </div>
      <h1 className="mb-2 text-2xl font-bold text-white">Signing you in</h1>
      <p className="max-w-md text-center text-slate-400">Completing sign-in with your institution…</p>
    </div>
  );
}

export default function SSOCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-slate-900">
          <div className="text-slate-400">Loading…</div>
        </div>
      }
    >
      <SSOCallbackContent />
    </Suspense>
  );
}
