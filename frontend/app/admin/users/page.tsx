"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient, UserProfile } from "@/services/apiClient";
import Sidebar from "@/components/Sidebar";
import { Users, Plus, Shield, Mail, Activity, Trash2, Edit } from "lucide-react";

export default function UsersPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isLoading || !user || user.role !== "admin") return;

    const fetchUsers = async () => {
      try {
        const data = await apiClient.get<UserProfile[]>("/api/users");
        setUsers(data);
      } catch (err) {
        // Fallback mock data if endpoint fails
        console.error("Failed to fetch users, using mock data", err);
        setUsers([
          { id: "1", email: "admin@examsentinel.com", full_name: "System Admin", role: "admin", is_active: true },
          { id: "2", email: "proctor@examsentinel.com", full_name: "Lead Proctor", role: "proctor", is_active: true },
          { id: "3", email: "reviewer@examsentinel.com", full_name: "Senior Reviewer", role: "reviewer", is_active: true },
          { id: "4", email: "student@university.edu", full_name: "Alice Smith", role: "candidate", is_active: true },
        ]);
        setError("Could not fetch real users. Showing mock data.");
      } finally {
        setLoading(false);
      }
    };

    void fetchUsers();
  }, [isLoading, user]);

  if (isLoading || !user) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center text-slate-500">Loading user management...</div>
      </div>
    );
  }

  if (user.role !== "admin") {
    return (
      <div className="flex flex-1">
        <Sidebar />
        <div className="flex-1 p-8 text-center text-red-500 font-semibold">
          Access Denied. Admins only.
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 h-screen overflow-hidden bg-slate-50">
      <Sidebar />

      <main className="flex-1 flex flex-col overflow-y-auto">
        <div className="p-6 sm:p-8 max-w-7xl mx-auto w-full">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5 mb-8">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
                <Users className="h-6 w-6 text-blue-600" />
                User Management
              </h1>
              <p className="text-sm text-slate-500 mt-1">
                Manage system access, roles, and user accounts.
              </p>
            </div>
            <button
              onClick={() => setIsModalOpen(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 transition-colors"
            >
              <Plus className="h-4 w-4" />
              Add User
            </button>
          </div>

          {error && (
            <div className="mb-6 rounded-lg bg-amber-50 p-4 border border-amber-200 text-sm text-amber-800">
              {error}
            </div>
          )}

          {/* Table Card */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      User
                    </th>
                    <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Role
                    </th>
                    <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th scope="col" className="px-6 py-4 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 bg-white">
                  {loading ? (
                    <tr>
                      <td colSpan={4} className="px-6 py-12 text-center text-sm text-slate-500">
                        Loading users...
                      </td>
                    </tr>
                  ) : users.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-6 py-12 text-center text-sm text-slate-500">
                        No users found.
                      </td>
                    </tr>
                  ) : (
                    users.map((u) => (
                      <tr key={u.id} className="hover:bg-slate-50/50 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <div className="h-10 w-10 flex-shrink-0 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold uppercase">
                              {u.full_name.charAt(0)}
                            </div>
                            <div className="ml-4">
                              <div className="text-sm font-medium text-slate-900">{u.full_name}</div>
                              <div className="text-sm text-slate-500 flex items-center gap-1 mt-0.5">
                                <Mail className="h-3 w-3" /> {u.email}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center text-sm text-slate-700">
                            <Shield className="h-4 w-4 mr-2 text-slate-400" />
                            <span className="capitalize font-medium">{u.role}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
                            u.is_active 
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : "bg-slate-100 text-slate-600 border border-slate-200"
                          }`}>
                            <span className={`h-1.5 w-1.5 rounded-full ${u.is_active ? "bg-emerald-500" : "bg-slate-400"}`}></span>
                            {u.is_active ? "Active" : "Inactive"}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <button className="text-slate-400 hover:text-blue-600 transition-colors mr-3" title="Edit">
                            <Edit className="h-4 w-4" />
                          </button>
                          <button className="text-slate-400 hover:text-red-600 transition-colors" title="Delete">
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>

      {/* Simple Add User Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-lg font-bold text-slate-900">Add New User</h2>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-slate-500">
                &times;
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Full Name</label>
                <input type="text" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" placeholder="John Doe" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Email Address</label>
                <input type="email" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" placeholder="john@example.com" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Role</label>
                <select className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white">
                  <option value="admin">Admin</option>
                  <option value="proctor">Proctor</option>
                  <option value="reviewer">Reviewer</option>
                  <option value="candidate">Candidate</option>
                </select>
              </div>
            </div>
            <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex justify-end gap-3">
              <button 
                onClick={() => setIsModalOpen(false)}
                className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button 
                onClick={() => setIsModalOpen(false)}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-500 rounded-lg shadow-sm transition-colors"
              >
                Create User
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
