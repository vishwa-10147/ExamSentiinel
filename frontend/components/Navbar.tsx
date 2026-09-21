"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useSidebar } from "@/contexts/SidebarContext";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient, HealthCheckResponse } from "@/services/apiClient";
import { Shield, Activity, User, LogOut, CheckCircle2, AlertTriangle, Menu } from "lucide-react";

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const { isSidebarOpen, toggleSidebar } = useSidebar();
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
    <header className="sticky top-0 z-50 w-full border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-4">
            {isAuthenticated && (
              <button
                onClick={toggleSidebar}
                className="p-2 rounded-md text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-white dark:hover:bg-slate-800 transition-colors"
                aria-label="Toggle Sidebar"
              >
                <Menu className="h-6 w-6" />
              </button>
            )}
          </div>
        </div>
        
        {/* We moved the profile to Sidebar, but we want the logo in the center or right? */}
        {/* "the navbutton should work only for navigation and it should be on tehe navigation side but not examsentinel" */}
        {/* This implies ExamSentinel logo should be separate from the hamburger menu. Let's put ExamSentinel in the center or right. Let's put it on the right! */}
        
        <div className="flex items-center">
          <Link href="/" className="flex items-center gap-2">
            <Image src="/logo.png" alt="ExamSentinel Logo" width={40} height={40} className="h-10 w-auto object-contain drop-shadow-sm" />
            <div>
              <span className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">ExamSentinel</span>
            </div>
          </Link>
        </div>
      </div>
    </header>
  );
}


