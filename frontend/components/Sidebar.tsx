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
  Scale,
  History,
} from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();

  const navItems = [
    { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard, roles: ["admin", "proctor", "reviewer", "candidate"] },
    { label: "Live Proctoring", href: "/dashboard/live", icon: Video, roles: ["admin", "proctor"] },
    { label: "Exam Center", href: "/exam", icon: ClipboardList, roles: ["admin", "candidate"] },
    { label: "Review Queue", href: "/review", icon: AlertOctagon, roles: ["admin", "reviewer"] },
    { label: "Appeals Center", href: "/appeals", icon: Scale, roles: ["admin", "reviewer", "candidate"] },
    { label: "Audit Logs", href: "/audit", icon: History, roles: ["admin"] },
    { label: "User Management", href: "/users", icon: Users, roles: ["admin"] },
    { label: "Settings", href: "/settings", icon: Settings, roles: ["admin"] },
  ];

  const filteredItems = navItems.filter((item) =>
    user?.role ? item.roles.includes(user.role) : false
  );

  return (
    <aside className="w-64 border-r border-slate-200 bg-white p-4 hidden md:flex flex-col justify-between shrink-0">
      <div className="space-y-6">
        <div>
          <h3 className="px-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Navigation
          </h3>
          <div className="mt-2 space-y-1">
            {filteredItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                    isActive
                      ? "bg-blue-50 text-blue-700"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                  }`}
                >
                  <Icon className={`h-4 w-4 ${isActive ? "text-blue-600" : "text-slate-400"}`} />
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-500">
        <p className="font-semibold text-slate-700">ExamSentinel v1.0</p>
        <p className="mt-1">Human-in-the-Loop Integrity Engine</p>
      </div>
    </aside>
  );
}
