"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import ThemeToggle from "./ThemeToggle";
import { usePathname } from "next/navigation";
import { useSidebar } from "@/contexts/SidebarContext";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient, HealthCheckResponse } from "@/services/apiClient";
import {
  LayoutDashboard,
  Video,
  ClipboardList,
  AlertOctagon,
  FileCheck2,
  Users,
  Settings,
  ScanFace,
  Scale,
  History,
  Mail,
  BookOpen,
  Trophy,
  User,
  Code2,
  Library,
  LogOut,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { isSidebarOpen, toggleSidebar, setSidebarOpen } = useSidebar();

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

  const navItems = [
    // Shared / Role-specific Dashboards
    { label: "Dashboard", href: `/${user?.role || 'candidate'}/dashboard`, icon: LayoutDashboard, roles: ["admin", "proctor", "reviewer", "candidate"] },
    
    // Proctor / Admin routes
    { label: "Live Proctoring", href: `/${user?.role === 'admin' ? 'admin' : 'proctor'}/live`, icon: Video, roles: ["admin", "proctor"] },
    
    // Admin routes
    { label: "Exam Center", href: "/admin/exam", icon: ClipboardList, roles: ["admin"] },
    { label: "Question Bank", href: "/admin/questions", icon: Library, roles: ["admin"] },
    { label: "Results", href: "/admin/results", icon: FileCheck2, roles: ["admin"] },
    { label: "Review Queue", href: "/admin/review", icon: AlertOctagon, roles: ["admin", "reviewer"] },
    { label: "Broadcast", href: "/admin/broadcast", icon: Mail, roles: ["admin"] },
    { label: "Audit Logs", href: "/admin/audit", icon: History, roles: ["admin"] },
    { label: "User Management", href: "/admin/users", icon: Users, roles: ["admin"] },
    { label: "Settings", href: "/admin/settings", icon: Settings, roles: ["admin"] },
    
    // Candidate routes
    { label: "My Exams", href: "/candidate/exams", icon: BookOpen, roles: ["candidate"] },
    { label: "Practice Lab", href: "/candidate/practice", icon: Code2, roles: ["candidate"], badge: "Soon" },
    { label: "Problem Set", href: "/candidate/problems", icon: Library, roles: ["candidate"], badge: "Soon" },
    { label: "My Results", href: "/candidate/results", icon: FileCheck2, roles: ["candidate"] },
    { label: "Leaderboard", href: "/candidate/leaderboard", icon: Trophy, roles: ["candidate"] },
    { label: "My Profile", href: "/candidate/profile", icon: User, roles: ["candidate"] },
  ];

  const currentRole = user?.role || "candidate";
  const filteredItems = navItems.filter((item) =>
    item.roles.includes(currentRole)
  );

  return (
    <>
      <button
        type="button"
        aria-label="Close navigation"
        onClick={() => setSidebarOpen(false)}
        className={`${isSidebarOpen ? "fixed inset-0 top-16 z-30 bg-slate-900/20 md:hidden" : "hidden"}`}
      />
      <aside className={`fixed md:sticky top-16 left-0 z-40 md:z-auto h-[calc(100vh-4rem)] overflow-y-auto border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 flex flex-col justify-between shrink-0 transition-all duration-300 ease-in-out ${isSidebarOpen ? "w-64 p-4 border-r translate-x-0 opacity-100" : "w-0 p-0 border-r-0 -translate-x-full opacity-0 overflow-hidden"}`}>
      <div className="space-y-6">
        <div>
          <h3 className="px-3 text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
            Navigation
          </h3>
          <div className="mt-2 space-y-1">
            {filteredItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href + "/"));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? "bg-blue-500/10 dark:bg-blue-500/15 text-blue-600 dark:text-blue-400 border border-blue-500/25 dark:border-blue-500/30 shadow-sm font-semibold"
                      : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/70 hover:text-slate-900 dark:hover:text-slate-200"
                  }`}
                >
                  <Icon className={`h-4 w-4 transition-colors ${isActive ? "text-blue-600 dark:text-blue-400" : "text-slate-400 dark:text-slate-500"}`} />
                  <span className="flex-1">{item.label}</span>
                  {item.badge && (
                    <span className="px-1.5 py-0.5 text-[10px] font-bold rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-3 pt-4 border-t border-slate-200 dark:border-slate-700 mt-4">
        <div className="flex items-center justify-between gap-2 bg-slate-50 dark:bg-slate-800/50 p-2 rounded-xl border border-slate-200 dark:border-slate-700/50">
          <ThemeToggle />
          
          {user ? (
            <div className="flex items-center gap-2 overflow-hidden flex-1 justify-center">
              <div className="flex flex-col text-center">
                <span className="text-sm font-semibold text-slate-900 dark:text-white leading-tight truncate max-w-[100px]">{user.full_name}</span>
                <span className={`inline-block text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border mt-0.5 mx-auto ${getRoleBadgeClass(user.role)}`}>
                  {user.role}
                </span>
              </div>
            </div>
          ) : (
             <div className="flex-1"></div>
          )}

          {user && (
            <button
              onClick={logout}
              title="Sign out"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 dark:hover:text-red-400 transition"
            >
              <LogOut className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
      </aside>
    </>
  );
}





