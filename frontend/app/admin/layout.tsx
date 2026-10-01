"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

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

  return children;
}
