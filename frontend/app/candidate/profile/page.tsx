"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import Sidebar from "@/components/Sidebar";
import { User, Mail, Save, Lock, Phone } from "lucide-react";

export default function CandidateProfilePage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  
  const [profileData, setProfileData] = useState({
    full_name: "",
    email: "",
    phone: "",
  });
  const [passwordData, setPasswordData] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/auth/login");
    } else if (user) {
      setProfileData({
        full_name: user.full_name || "",
        email: user.email || "",
        phone: "+1 (555) 000-0000",
      });
    }
  }, [isLoading, isAuthenticated, user, router]);

  if (isLoading || !user) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center text-slate-500">Loading profile...</div>
      </div>
    );
  }

  const handleProfileSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await new Promise(r => setTimeout(r, 500));
      alert("Profile updated successfully (mock)!");
    } catch (err) {
      console.error(err);
      alert("Failed to update profile.");
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (passwordData.new_password !== passwordData.confirm_password) {
      alert("Passwords do not match!");
      return;
    }
    setSaving(true);
    try {
      await new Promise(r => setTimeout(r, 500));
      alert("Password updated successfully (mock)!");
      setPasswordData({ current_password: "", new_password: "", confirm_password: "" });
    } catch (err) {
      console.error(err);
      alert("Failed to update password.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-1 h-screen overflow-hidden bg-slate-50">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-y-auto">
        <div className="p-6 sm:p-8 max-w-4xl mx-auto w-full">
          <div className="mb-8">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
              <User className="h-6 w-6 text-blue-600" />
              My Profile
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Manage your personal information and account security.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-3 mb-8">
            <div className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col items-center justify-center text-center shadow-sm">
              <div className="h-20 w-20 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 text-2xl font-bold uppercase mb-4">
                {user.full_name?.charAt(0) || "U"}
              </div>
              <h3 className="font-semibold text-lg text-slate-900">{user.full_name}</h3>
              <p className="text-sm text-slate-500 capitalize">{user.role}</p>
            </div>
            
            <div className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col justify-center shadow-sm md:col-span-2">
              <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Account Stats</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                  <div className="text-2xl font-bold text-slate-900 mb-1">12</div>
                  <div className="text-sm text-slate-500">Total Exams Taken</div>
                </div>
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                  <div className="text-2xl font-bold text-slate-900 mb-1">82%</div>
                  <div className="text-sm text-slate-500">Average Score</div>
                </div>
              </div>
            </div>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
              <div className="px-6 py-4 border-b border-slate-200 bg-slate-50/50">
                <h2 className="font-semibold text-slate-900">Personal Information</h2>
              </div>
              <form onSubmit={handleProfileSave} className="p-6 flex-1 flex flex-col">
                <div className="space-y-4 flex-1">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Full Name</label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                      <input 
                        type="text" 
                        value={profileData.full_name}
                        onChange={(e) => setProfileData({...profileData, full_name: e.target.value})}
                        className="w-full pl-10 pr-3 py-2 rounded-lg border border-slate-300 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" 
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Email Address</label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                      <input 
                        type="email" 
                        disabled
                        value={profileData.email}
                        className="w-full pl-10 pr-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-500 text-sm cursor-not-allowed" 
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Phone Number</label>
                    <div className="relative">
                      <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                      <input 
                        type="text" 
                        value={profileData.phone}
                        onChange={(e) => setProfileData({...profileData, phone: e.target.value})}
                        className="w-full pl-10 pr-3 py-2 rounded-lg border border-slate-300 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" 
                      />
                    </div>
                  </div>
                </div>
                <div className="mt-6 pt-4 border-t border-slate-100">
                  <button 
                    type="submit" 
                    disabled={saving}
                    className="flex items-center justify-center gap-2 w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 transition-colors disabled:opacity-70"
                  >
                    <Save className="h-4 w-4" />
                    Save Changes
                  </button>
                </div>
              </form>
            </div>

            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
              <div className="px-6 py-4 border-b border-slate-200 bg-slate-50/50">
                <h2 className="font-semibold text-slate-900">Security</h2>
              </div>
              <form onSubmit={handlePasswordSave} className="p-6 flex-1 flex flex-col">
                <div className="space-y-4 flex-1">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Current Password</label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                      <input 
                        type="password"
                        required
                        value={passwordData.current_password}
                        onChange={(e) => setPasswordData({...passwordData, current_password: e.target.value})}
                        className="w-full pl-10 pr-3 py-2 rounded-lg border border-slate-300 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" 
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">New Password</label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                      <input 
                        type="password"
                        required
                        value={passwordData.new_password}
                        onChange={(e) => setPasswordData({...passwordData, new_password: e.target.value})}
                        className="w-full pl-10 pr-3 py-2 rounded-lg border border-slate-300 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" 
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Confirm New Password</label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                      <input 
                        type="password"
                        required
                        value={passwordData.confirm_password}
                        onChange={(e) => setPasswordData({...passwordData, confirm_password: e.target.value})}
                        className="w-full pl-10 pr-3 py-2 rounded-lg border border-slate-300 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" 
                      />
                    </div>
                  </div>
                </div>
                <div className="mt-6 pt-4 border-t border-slate-100">
                  <button 
                    type="submit" 
                    disabled={saving}
                    className="flex items-center justify-center gap-2 w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-slate-800 transition-colors disabled:opacity-70"
                  >
                    <Save className="h-4 w-4" />
                    Update Password
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
