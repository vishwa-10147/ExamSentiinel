"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import Sidebar from "@/components/Sidebar";

/**
 * Sidebar layout for a role area that redirects users who aren't signed in
 * (to login) or don't have one of `roles` (to their own dashboard).
 * This is UX only — every API endpoint enforces roles server-side.
 */
export default function RoleAreaLayout({ roles, children }: { roles: string[]; children: React.ReactNode }) {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const allowed = !!user && roles.includes(user.role);

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) router.replace("/auth/login");
    else if (!allowed) router.replace("/dashboard");
  }, [isLoading, isAuthenticated, allowed, router]);

  if (isLoading || !allowed) {
    return <main className="flex min-h-screen items-center justify-center text-slate-500">Checking access...</main>;
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden bg-slate-50 dark:bg-slate-900">
      <Sidebar />
      <div className="min-w-0 flex-1 overflow-y-auto overflow-x-hidden">{children}</div>
    </div>
  );
}
