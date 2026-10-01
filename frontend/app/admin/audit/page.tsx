"use client";
export const dynamic = "force-dynamic";

import React, { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import { History, Shield, Activity, Download, User as UserIcon, Monitor, Search, X } from "lucide-react";

interface AuditLog {
  id: string;
  timestamp: string;
  action: string;
  user: string;
  role: string;
  ip_address: string;
  status: "success" | "warning" | "error";
  details?: string;
}

export default function AuditPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isLoading || !user || user.role !== "admin") return;

    const fetchLogs = async () => {
      try {
        const data = await apiClient.get<AuditLog[]>("/api/users/audit");
        setLogs(data);
      } catch (err) {
        console.error("Failed to fetch audit logs", err);
        setLogs([]);
        setError("Failed to load audit logs. Please try again later.");
      } finally {
        setLoading(false);
      }
    };

    void fetchLogs();
  }, [isLoading, user]);

  const filteredLogs = useMemo(() => {
    if (!searchQuery.trim()) return logs;
    const query = searchQuery.toLowerCase().trim();
    return logs.filter((log) => {
      return (
        log.user.toLowerCase().includes(query) ||
        log.action.toLowerCase().includes(query) ||
        log.role.toLowerCase().includes(query) ||
        log.ip_address.toLowerCase().includes(query) ||
        (log.details && log.details.toLowerCase().includes(query))
      );
    });
  }, [logs, searchQuery]);

  const handleExportCSV = () => {
    if (filteredLogs.length === 0) return;
    const headers = ["Timestamp", "Action", "User", "Role", "IP Address", "Status", "Details"];
    const rows = filteredLogs.map(log => [
      `"${log.timestamp}"`,
      `"${log.action.replace(/"/g, '""')}"`,
      `"${log.user.replace(/"/g, '""')}"`,
      `"${log.role}"`,
      `"${log.ip_address}"`,
      `"${log.status}"`,
      `"${(log.details || "").replace(/"/g, '""')}"`
    ]);
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `audit_logs_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (isLoading || !user) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center text-slate-500">Loading audit logs...</div>
      </div>
    );
  }

  if (user.role !== "admin") {
    return (
      <div className="flex-1 w-full">
        <div className="flex-1 p-8 text-center text-red-500 font-semibold">
          Access Denied. Admins only.
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 w-full">
      <main className="flex-1 flex flex-col overflow-y-auto">
        <div className="p-6 sm:p-8 max-w-7xl mx-auto w-full">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5 mb-8">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
                <History className="h-6 w-6 text-slate-700" />
                System Audit Logs
              </h1>
              <p className="text-sm text-slate-500 mt-1">
                Immutable record of all system events, user actions, IP addresses, and security alerts.
              </p>
            </div>
            <div className="flex gap-2">
              <button 
                onClick={handleExportCSV}
                disabled={filteredLogs.length === 0}
                className="inline-flex items-center gap-2 rounded-lg bg-white border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 transition-colors disabled:opacity-50"
              >
                <Download className="h-4 w-4" />
                Export CSV
              </button>
            </div>
          </div>

          {error && (
            <div className="mb-6 rounded-lg bg-amber-50 p-4 border border-amber-200 text-sm text-amber-800 flex items-start gap-3">
              <Activity className="h-5 w-5 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-amber-900">Live feed notice</h3>
                <p>{error}</p>
              </div>
            </div>
          )}

          {/* Search bar */}
          <div className="mb-6 flex flex-col sm:flex-row gap-3 items-center justify-between">
            <div className="relative w-full sm:max-w-md">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-4 w-4 text-slate-400" />
              </div>
              <input
                type="text"
                placeholder="Search by user name, action, role, or IP address..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="block w-full pl-9 pr-8 py-2 border border-slate-300 rounded-lg text-sm bg-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              {searchQuery && (
                <button 
                  onClick={() => setSearchQuery("")}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
            <div className="text-xs text-slate-500 font-medium self-end sm:self-auto">
              Showing {filteredLogs.length} of {logs.length} audit entries
            </div>
          </div>

          {/* Table Card */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Timestamp
                    </th>
                    <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Event / Action
                    </th>
                    <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      User / Role
                    </th>
                    <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      IP Address
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 bg-white">
                  {loading ? (
                    <tr>
                      <td colSpan={4} className="px-6 py-12 text-center text-sm text-slate-500">
                        Loading logs...
                      </td>
                    </tr>
                  ) : filteredLogs.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-6 py-12 text-center text-sm text-slate-500">
                        No audit events match your search criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredLogs.map((log) => {
                      const dateObj = new Date(log.timestamp);
                      const dateStr = dateObj.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
                      const timeStr = dateObj.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' });

                      return (
                        <tr key={log.id} className="hover:bg-slate-50/50 transition-colors">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm font-medium text-slate-900">{dateStr}</div>
                            <div className="text-xs text-slate-500">{timeStr}</div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex items-start gap-2">
                              <div className="mt-0.5">
                                {log.status === "success" && <div className="h-2 w-2 rounded-full bg-emerald-500" />}
                                {log.status === "warning" && <div className="h-2 w-2 rounded-full bg-amber-500" />}
                                {log.status === "error" && <div className="h-2 w-2 rounded-full bg-red-500" />}
                              </div>
                              <div>
                                <div className="text-sm font-medium text-slate-900">{log.action}</div>
                                <div className="text-xs text-slate-500 mt-0.5">{log.details || "No additional details"}</div>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center gap-2">
                              <div className="flex items-center justify-center h-8 w-8 rounded bg-slate-100 text-slate-600">
                                {log.role === "system" ? <Monitor className="h-4 w-4" /> : <UserIcon className="h-4 w-4" />}
                              </div>
                              <div>
                                <div className="text-sm text-slate-900 font-medium">{log.user}</div>
                                <div className="text-xs text-slate-500 capitalize flex items-center gap-1">
                                  <Shield className="h-3 w-3" />
                                  {log.role}
                                </div>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 font-mono">
                            {log.ip_address}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
