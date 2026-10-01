"use client";

export const dynamic = "force-dynamic";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { ShieldCheck, Loader2 } from "lucide-react";

export default function DashboardRedirect() {
  const router = useRouter();
  const { user, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading) {
      if (user && user.role) {
        const role = user.role.toLowerCase();
        if (role === "admin") {
          router.replace("/admin/dashboard");
        } else if (role === "candidate") {
          router.replace("/candidate/dashboard");
        } else if (role === "proctor") {
          router.replace("/proctor/dashboard");
        } else if (role === "reviewer") {
          router.replace("/reviewer/dashboard");
        } else {
          router.replace("/admin/dashboard");
        }
      } else {
        router.replace("/auth/login");
      }
    }
  }, [user, isLoading, router]);

  return (
    <div className="flex h-screen w-full flex-col items-center justify-center bg-slate-950 text-white space-y-4">
      <div className="flex items-center gap-3">
        <div className="p-2.5 bg-blue-600/20 border border-blue-500/30 rounded-xl">
          <ShieldCheck className="h-8 w-8 text-blue-400 animate-pulse" />
        </div>
        <span className="text-xl font-bold tracking-tight text-white">ExamSentinel</span>
      </div>
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
        <span>Dispatching to role-based dashboard...</span>
      </div>
    </div>
  );
}
