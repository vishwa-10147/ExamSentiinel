"use client";
export const dynamic = "force-dynamic";

import React, { useEffect, useState, useMemo, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient, UserProfile } from "@/services/apiClient";
import { 
  Users, 
  Plus, 
  Shield, 
  Mail, 
  Search, 
  Trash2, 
  Edit, 
  CheckCircle, 
  XCircle,
  Loader2,
  ShieldAlert,
  Eye,
  FileCheck,
  GraduationCap,
  UserCheck,
  ChevronDown,
  Filter,
  AlertTriangle,
  AlertCircle,
  X
} from "lucide-react";
import { toast, Toaster } from "react-hot-toast";

const ROLE_OPTIONS = [
  { value: "admin", label: "Admin", icon: ShieldAlert, bgClass: "bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100" },
  { value: "proctor", label: "Proctor", icon: Eye, bgClass: "bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100" },
  { value: "reviewer", label: "Reviewer", icon: FileCheck, bgClass: "bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100" },
  { value: "candidate", label: "Candidate", icon: GraduationCap, bgClass: "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100" },
];

export default function UsersPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedRoleFilter, setSelectedRoleFilter] = useState<string>("all");

  const [updatingUserRoleId, setUpdatingUserRoleId] = useState<string | null>(null);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [deletingUser, setDeletingUser] = useState<UserProfile | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  
  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    role: "candidate",
    password: "",
    is_active: true,
  });
  
  const [isSaving, setIsSaving] = useState(false);

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiClient.get<UserProfile[]>("/api/users");
      setUsers(data);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch users", err);
      setUsers([]);
      setError("Failed to load users. Please try again later.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isLoading || !user || user.role !== "admin") return;
    void fetchUsers();
  }, [isLoading, user, fetchUsers]);

  const roleCounts = useMemo(() => {
    const counts: Record<string, number> = { all: users.length, admin: 0, proctor: 0, reviewer: 0, candidate: 0 };
    users.forEach(u => {
      const r = u.role.toLowerCase();
      if (counts[r] !== undefined) counts[r]++;
    });
    return counts;
  }, [users]);

  const filteredUsers = useMemo(() => {
    return users.filter(u => {
      const matchesSearch = !searchQuery || 
        u.full_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
        u.email.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesRole = selectedRoleFilter === "all" || u.role.toLowerCase() === selectedRoleFilter;
      return matchesSearch && matchesRole;
    });
  }, [users, searchQuery, selectedRoleFilter]);

  const handleRoleChange = async (targetUser: UserProfile, newRole: string) => {
    if (targetUser.role === newRole) return;

    if (user?.id === targetUser.id && newRole !== "admin") {
      const confirmed = window.confirm(
        "Warning: Changing your own role from Admin will revoke your access to Admin Management. Are you sure?"
      );
      if (!confirmed) return;
    }

    setUpdatingUserRoleId(targetUser.id);
    try {
      const typedRole = newRole as UserProfile["role"];
      await apiClient.put(`/api/users/${targetUser.id}`, { role: typedRole });
      setUsers(prev => prev.map(u => u.id === targetUser.id ? { ...u, role: typedRole } : u));
      toast.success(`Role updated to ${newRole.toUpperCase()} for ${targetUser.full_name}`);
    } catch (err: any) {
      console.error("Failed to update user role", err);
      toast.error(err.response?.data?.detail || "Failed to update user role");
    } finally {
      setUpdatingUserRoleId(null);
    }
  };

  const handleOpenAddModal = () => {
    setIsEditMode(false);
    setEditingUserId(null);
    setFormData({
      full_name: "",
      email: "",
      role: "candidate",
      password: "",
      is_active: true,
    });
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (u: UserProfile) => {
    setIsEditMode(true);
    setEditingUserId(u.id);
    setFormData({
      full_name: u.full_name,
      email: u.email,
      role: u.role,
      password: "",
      is_active: u.is_active ?? true,
    });
    setIsModalOpen(true);
  };

  const handleToggleStatus = async (u: UserProfile) => {
    try {
      const updatedStatus = !u.is_active;
      await apiClient.put(`/api/users/${u.id}`, { is_active: updatedStatus });
      setUsers(prev => prev.map(item => item.id === u.id ? { ...item, is_active: updatedStatus } : item));
      toast.success(`User state changed to ${updatedStatus ? "Active" : "Inactive"}`);
    } catch (err: any) {
      console.error("Failed to toggle status", err);
      toast.error(err.response?.data?.detail || "Failed to update user status");
    }
  };

  const handleOpenDeleteModal = (u: UserProfile) => {
    if (user?.id === u.id) {
      toast.error("You cannot delete your own admin account");
      return;
    }
    setDeletingUser(u);
  };

  const handleConfirmDelete = async () => {
    if (!deletingUser) return;
    setIsDeleting(true);
    try {
      await apiClient.delete(`/api/users/${deletingUser.id}`);
      toast.success(`User ${deletingUser.full_name || deletingUser.email} deleted successfully!`);
      setDeletingUser(null);
      void fetchUsers();
    } catch (err: any) {
      console.error("Failed to delete user", err);
      toast.error(err.response?.data?.detail || err.message || "Failed to delete user");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleSave = async () => {
    if (!formData.full_name || !formData.email) {
      toast.error("Name and email are required");
      return;
    }
    
    setIsSaving(true);
    try {
      if (isEditMode && editingUserId) {
        const payload: any = {
          full_name: formData.full_name,
          email: formData.email,
          role: formData.role,
          is_active: formData.is_active,
        };
        if (formData.password.trim() !== "") {
          payload.password = formData.password;
        }

        await apiClient.put(`/api/users/${editingUserId}`, payload);
        toast.success("User updated successfully");
      } else {
        if (!formData.password) {
          toast.error("Password is required for new users");
          setIsSaving(false);
          return;
        }
        await apiClient.post("/api/users", formData);
        toast.success("User created successfully");
      }
      setIsModalOpen(false);
      void fetchUsers();
    } catch (err: any) {
      console.error("Failed to save user", err);
      toast.error(err.response?.data?.detail || "Failed to save user");
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading || !user) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <div className="text-center text-slate-500">Loading user management...</div>
      </div>
    );
  }

  if (user.role !== "admin") {
    return (
      <div className="flex-1 w-full">
        <div className="flex-1 p-8 text-center text-red-500 font-semibold mt-10">
          Access Denied. Admins only.
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 w-full">
      <Toaster position="top-right" />
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
                Assign and update user roles, toggle account statuses, and manage administrative access.
              </p>
            </div>
            <button
              onClick={handleOpenAddModal}
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 active:bg-blue-700 transition"
            >
              <Plus className="h-4 w-4" />
              Add New User
            </button>
          </div>

          {error && (
            <div className="mb-6 rounded-xl bg-amber-50 p-4 border border-amber-200 text-sm text-amber-800 flex items-center gap-2">
              <XCircle className="h-5 w-5 text-amber-600 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Controls Bar: Search & Role Filter Tabs */}
          <div className="mb-6 space-y-4 sm:space-y-0 sm:flex sm:items-center sm:justify-between gap-4">
            
            {/* Search bar */}
            <div className="relative w-full sm:max-w-md">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Search className="h-4 w-4" />
              </div>
              <input
                type="text"
                placeholder="Search users by name or email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="block w-full pl-10 pr-4 py-2 text-sm border border-slate-300 rounded-xl bg-white text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600/20 focus:border-blue-600 transition"
              />
            </div>

            {/* Role Filter Tabs */}
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200/80 overflow-x-auto">
              <button
                onClick={() => setSelectedRoleFilter("all")}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition whitespace-nowrap ${
                  selectedRoleFilter === "all"
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                All ({roleCounts.all})
              </button>
              {ROLE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setSelectedRoleFilter(opt.value)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 whitespace-nowrap ${
                    selectedRoleFilter === opt.value
                      ? "bg-white text-slate-900 shadow-sm"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  <opt.icon className="h-3.5 w-3.5" />
                  <span>{opt.label} ({roleCounts[opt.value] || 0})</span>
                </button>
              ))}
            </div>

          </div>

          {/* User Table Card */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      User Profile
                    </th>
                    <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Assigned Role (Instant Change)
                    </th>
                    <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Account Status
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
                        <div className="flex items-center justify-center gap-2">
                          <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
                          <span>Fetching users from system...</span>
                        </div>
                      </td>
                    </tr>
                  ) : filteredUsers.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-6 py-12 text-center text-sm text-slate-500">
                        No users found matching your criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredUsers.map((u) => {
                      const currentRoleConfig = ROLE_OPTIONS.find(r => r.value === u.role.toLowerCase()) || ROLE_OPTIONS[3];
                      const IconComp = currentRoleConfig.icon;
                      const isUpdatingThisRole = updatingUserRoleId === u.id;

                      return (
                        <tr key={u.id} className="hover:bg-slate-50/60 transition-colors">
                          
                          {/* User Column */}
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center">
                              <div className="h-10 w-10 flex-shrink-0 rounded-full bg-slate-900 text-white flex items-center justify-center font-bold text-sm uppercase shadow-sm">
                                {u.full_name ? u.full_name.charAt(0) : "U"}
                              </div>
                              <div className="ml-4">
                                <div className="text-sm font-semibold text-slate-900">{u.full_name}</div>
                                <div className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
                                  <Mail className="h-3 w-3 text-slate-400" /> {u.email}
                                </div>
                              </div>
                            </div>
                          </td>

                          {/* Role Assign / Change Dropdown Column */}
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="relative inline-flex items-center">
                              {isUpdatingThisRole ? (
                                <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-blue-200 bg-blue-50 text-blue-700 text-xs font-semibold">
                                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                  Updating Role...
                                </div>
                              ) : (
                                <div className="relative">
                                  <select
                                    value={u.role.toLowerCase()}
                                    onChange={(e) => handleRoleChange(u, e.target.value)}
                                    className={`appearance-none rounded-xl border px-3 py-1.5 pr-8 text-xs font-bold transition cursor-pointer outline-none ${currentRoleConfig.bgClass}`}
                                    title="Click to change this user's role"
                                  >
                                    {ROLE_OPTIONS.map((opt) => (
                                      <option key={opt.value} value={opt.value} className="bg-white text-slate-900 font-semibold py-1">
                                        {opt.label} Role
                                      </option>
                                    ))}
                                  </select>
                                  <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 pointer-events-none opacity-60" />
                                </div>
                              )}
                            </div>
                          </td>

                          {/* Account Status Column */}
                          <td className="px-6 py-4 whitespace-nowrap">
                            <button
                              onClick={() => handleToggleStatus(u)}
                              title="Click to toggle Active / Inactive state"
                              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold transition cursor-pointer hover:opacity-80 ${
                                u.is_active 
                                  ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                  : "bg-slate-100 text-slate-600 border border-slate-200"
                              }`}
                            >
                              <span className={`h-1.5 w-1.5 rounded-full ${u.is_active ? "bg-emerald-500" : "bg-slate-400"}`}></span>
                              {u.is_active ? "Active" : "Inactive"}
                            </button>
                          </td>

                          {/* Actions Column */}
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <button 
                              onClick={() => handleOpenEditModal(u)}
                              className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors mr-1" 
                              title="Edit User Details"
                            >
                              <Edit className="h-4 w-4" />
                            </button>
                            <button 
                              onClick={() => handleOpenDeleteModal(u)}
                              className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer" 
                              title="Delete User"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
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

      {/* Edit / Add User Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden border border-slate-200">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
              <h2 className="text-base font-bold text-slate-900">{isEditMode ? "Edit User Details" : "Add New User Account"}</h2>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-slate-600 text-xl font-bold leading-none">
                &times;
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">Full Name</label>
                <input 
                  type="text" 
                  value={formData.full_name}
                  onChange={(e) => setFormData(prev => ({...prev, full_name: e.target.value}))}
                  className="w-full rounded-xl border border-slate-300 px-3.5 py-2 text-sm text-slate-900 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20 transition" 
                  placeholder="John Doe" 
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">Email Address</label>
                <input 
                  type="email" 
                  value={formData.email}
                  onChange={(e) => setFormData(prev => ({...prev, email: e.target.value}))}
                  className="w-full rounded-xl border border-slate-300 px-3.5 py-2 text-sm text-slate-900 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20 transition" 
                  placeholder="john@institution.edu" 
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">Assign Role</label>
                  <select 
                    value={formData.role}
                    onChange={(e) => setFormData(prev => ({...prev, role: e.target.value}))}
                    className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-900 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20 bg-white transition"
                  >
                    {ROLE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">Status</label>
                  <select 
                    value={formData.is_active ? "active" : "inactive"}
                    onChange={(e) => setFormData(prev => ({...prev, is_active: e.target.value === "active"}))}
                    className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-900 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20 bg-white transition"
                  >
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                  {isEditMode ? "New Password (leave blank to keep current)" : "Account Password"}
                </label>
                <input 
                  type="password" 
                  value={formData.password}
                  onChange={(e) => setFormData(prev => ({...prev, password: e.target.value}))}
                  className="w-full rounded-xl border border-slate-300 px-3.5 py-2 text-sm text-slate-900 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20 transition" 
                  placeholder={isEditMode ? "Leave blank to keep unchanged" : "Set initial password"} 
                />
              </div>
            </div>

            <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex justify-end gap-3">
              <button 
                onClick={() => setIsModalOpen(false)}
                disabled={isSaving}
                className="px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200/60 rounded-xl transition disabled:opacity-50"
              >
                Cancel
              </button>
              <button 
                onClick={handleSave}
                disabled={isSaving}
                className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl shadow-sm transition disabled:opacity-50"
              >
                {isSaving ? "Saving..." : (isEditMode ? "Save Changes" : "Create User")}
              </button>
            </div>

          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deletingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl max-w-md w-full border border-slate-200 shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            
            <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between bg-red-50/50">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-red-100 text-red-600">
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 text-base">Confirm Permanent Deletion</h3>
                  <p className="text-xs text-red-600 font-medium">Irreversible database action</p>
                </div>
              </div>
              <button
                onClick={() => setDeletingUser(null)}
                disabled={isDeleting}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <p className="text-sm text-slate-600 leading-relaxed">
                Are you sure you want to permanently delete this user account from the system?
              </p>

              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 space-y-2 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 font-medium">Full Name:</span>
                  <span className="font-bold text-slate-900">{deletingUser.full_name || "N/A"}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 font-medium">Email Address:</span>
                  <span className="font-mono font-semibold text-slate-800">{deletingUser.email}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 font-medium">Account Role:</span>
                  <span className="font-bold uppercase tracking-wider text-blue-600">{deletingUser.role}</span>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-800 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <span>This will purge all exam sessions, test responses, roster enrollments, and audit logs linked to this user.</span>
              </div>
            </div>

            <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex justify-end gap-3">
              <button
                onClick={() => setDeletingUser(null)}
                disabled={isDeleting}
                className="px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200/60 rounded-xl transition disabled:opacity-50 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDelete}
                disabled={isDeleting}
                className="inline-flex items-center justify-center gap-2 px-5 py-2 text-sm font-bold text-white bg-red-600 hover:bg-red-700 active:bg-red-800 rounded-xl shadow-md transition disabled:opacity-50 cursor-pointer"
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Deleting User...
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    Yes, Delete User
                  </>
                )}
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
