"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

import Sidebar from "@/components/Sidebar";

const STAFF_ROLES = ["admin", "proctor", "reviewer"];

export default function AdminAreaLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.replace("/auth/login");
    } else if (!user || !STAFF_ROLES.includes(user.role)) {
      router.replace("/dashboard");
    }
  }, [isLoading, isAuthenticated, user, router]);

  if (isLoading || !user || !STAFF_ROLES.includes(user.role)) {
    return <main className="flex min-h-screen items-center justify-center text-slate-500">Checking access...</main>;
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-slate-50 dark:bg-slate-900 overflow-hidden">
      <Sidebar />
      <div className="min-w-0 flex-1 overflow-x-hidden overflow-y-auto">
        {children}
      </div>
    </div>
  );
}

