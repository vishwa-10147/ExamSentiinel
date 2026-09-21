"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
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
} from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();

  const navItems = [
    { label: "Dashboard", href: `/${user?.role || 'candidate'}/dashboard`, icon: LayoutDashboard, roles: ["admin", "proctor", "reviewer", "candidate"] },
    { label: "Live Proctoring", href: `/${user?.role || 'proctor'}/live`, icon: Video, roles: ["admin", "proctor"] },
    { label: "Exam Center", href: "/admin/exam", icon: ClipboardList, roles: ["admin"] },
    { label: "Question Bank", href: "/admin/questions", icon: Library, roles: ["admin"] },
    { label: "Results", href: "/admin/results", icon: FileCheck2, roles: ["admin"] },
    { label: "Review Queue", href: "/admin/review", icon: AlertOctagon, roles: ["admin", "reviewer"] },

    { label: "Broadcast", href: "/admin/broadcast", icon: Mail, roles: ["admin"] },
    { label: "Audit Logs", href: "/admin/audit", icon: History, roles: ["admin"] },
    { label: "User Management", href: "/admin/users", icon: Users, roles: ["admin"] },
    { label: "Settings", href: "/admin/settings", icon: Settings,
  ScanFace, roles: ["admin"] },
    
    // Candidate routes
    { label: "My Exams", href: "/candidate/exams", icon: BookOpen, roles: ["candidate"] },
    { label: "Practice Problems", href: "/candidate/problems", icon: Code2, roles: ["candidate"] },
    { label: "My Results", href: "/candidate/results", icon: FileCheck2, roles: ["candidate"] },
    { label: "Leaderboard", href: "/candidate/leaderboard", icon: Trophy, roles: ["candidate"] },
    { label: "Code Sandbox", href: "/candidate/practice", icon: Code2, roles: ["candidate", "admin"] },
    { label: "My Profile", href: "/candidate/profile", icon: User, roles: ["candidate"] },
  ];

  const filteredItems = navItems.filter((item) =>
    user?.role ? item.roles.includes(user.role) : false
  );

  return (
    <aside className="sticky top-16 h-[calc(100vh-4rem)] overflow-y-auto w-64 border-r border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4 flex flex-col justify-between shrink-0">
      <div className="space-y-6">
        <div>
          <h3 className="px-3 text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 dark:text-slate-400">
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
                  className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                    isActive
                      ? "bg-blue-50 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300"
                      : "text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:bg-slate-800 hover:text-slate-900"
                  }`}
                >
                  <Icon className={`h-4 w-4 ${isActive ? "text-blue-600" : "text-slate-400 dark:text-slate-500 dark:text-slate-400"}`} />
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 p-3 text-xs text-slate-500 dark:text-slate-400">
        <p className="font-semibold text-slate-700 dark:text-slate-200">ExamSentinel v1.0</p>
        <p className="mt-1">Human-in-the-Loop Integrity Engine</p>
      </div>
    </aside>
  );
}





