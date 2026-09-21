import ThemeToggle from "./ThemeToggle";
"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient, HealthCheckResponse } from "@/services/apiClient";
import { Shield, Activity, User, LogOut, CheckCircle2, AlertTriangle } from "lucide-react";

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const h = await apiClient.getHealth();
        setHealth(h);
      } catch {
        setHealth(null);
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const getRoleBadgeClass = (role?: string) => {
    switch (role) {
      case "admin":
        return "bg-purple-100 text-purple-800 border-purple-200";
      case "proctor":
        return "bg-blue-100 text-blue-800 border-blue-200";
      case "reviewer":
        return "bg-amber-100 text-amber-800 border-amber-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2">
            <Image src="/logo.png" alt="ExamSentinel Logo" width={40} height={40}  className="h-10 w-auto object-contain drop-shadow-sm" />
            <div>
              <span className="text-xl font-bold tracking-tight text-slate-900">ExamSentinel</span>
            </div>
          </Link>


        </div>

        <div className="flex items-center gap-4">
          {/* Health status indicator */}
          <div className="hidden sm:flex items-center gap-1.5 text-xs font-medium text-slate-500 bg-slate-50 px-2.5 py-1 rounded-full border border-slate-200">
            {health?.status === "healthy" ? (
              <>
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                <span>Backend Online</span>
              </>
            ) : (
              <>
                <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
                <span>Service Degraded</span>
              </>
            )}
          </div>

          {isAuthenticated && user ? (
            <div className="flex items-center gap-3">
              <div className="flex flex-col text-right">
                <span className="text-sm font-semibold text-slate-900 leading-tight">{user.full_name}</span>
                <span className={`inline-block text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border self-end ${getRoleBadgeClass(user.role)}`}>
                  {user.role}
                </span>
              </div>
              <button
                onClick={logout}
                title="Sign out"
                className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 hover:text-red-600 transition"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <Link
              href="/auth/login"
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 transition"
            >
              <User className="h-4 w-4" />
              Sign In
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
