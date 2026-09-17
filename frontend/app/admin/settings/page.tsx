"use client";

import React, { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import {
  Settings,
  Shield,
  Bell,
  Save,
  Globe,
  Sliders,
  CheckCircle2
} from "lucide-react";

export default function SettingsPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  
  const [activeTab, setActiveTab] = useState("general");
  const [isSaving, setIsSaving] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  // Protect route
  if (!authLoading && user && user.role !== "admin") {
    router.push("/admin/dashboard");
    return null;
  }

  const handleSave = () => {
    setIsSaving(true);
    // Simulate API call
    setTimeout(() => {
      setIsSaving(false);
      setShowSuccess(true);
      setTimeout(() => setShowSuccess(false), 3000);
    }, 800);
  };

  return (
    <div className="flex flex-1 min-h-screen bg-slate-50">
      <Sidebar />
      <div className="flex-1 p-6 sm:p-8 max-w-6xl mx-auto">
        
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
              <Settings className="w-7 h-7 text-blue-600" />
              Platform Settings
            </h1>
            <p className="text-slate-500 mt-1">Configure global preferences and AI risk engine parameters.</p>
          </div>
          
          <button 
            onClick={handleSave}
            disabled={isSaving}
            className="flex items-center gap-2 bg-blue-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-blue-700 transition disabled:opacity-70"
          >
            {isSaving ? (
              <span className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
            ) : showSuccess ? (
              <CheckCircle2 className="w-5 h-5" />
            ) : (
              <Save className="w-5 h-5" />
            )}
            {showSuccess ? "Saved!" : "Save Changes"}
          </button>
        </div>

        <div className="flex flex-col md:flex-row gap-8">
          {/* Tabs Sidebar */}
          <div className="w-full md:w-64 flex flex-col gap-1 shrink-0">
            <button 
              onClick={() => setActiveTab("general")}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition ${activeTab === "general" ? "bg-white shadow-sm border border-slate-200 text-blue-600" : "text-slate-600 hover:bg-slate-100"}`}
            >
              <Globe className="w-4 h-4" /> General Preferences
            </button>
            <button 
              onClick={() => setActiveTab("risk")}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition ${activeTab === "risk" ? "bg-white shadow-sm border border-slate-200 text-blue-600" : "text-slate-600 hover:bg-slate-100"}`}
            >
              <Sliders className="w-4 h-4" /> AI Risk Engine
            </button>
            <button 
              onClick={() => setActiveTab("security")}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition ${activeTab === "security" ? "bg-white shadow-sm border border-slate-200 text-blue-600" : "text-slate-600 hover:bg-slate-100"}`}
            >
              <Shield className="w-4 h-4" /> Security & Compliance
            </button>
            <button 
              onClick={() => setActiveTab("notifications")}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition ${activeTab === "notifications" ? "bg-white shadow-sm border border-slate-200 text-blue-600" : "text-slate-600 hover:bg-slate-100"}`}
            >
              <Bell className="w-4 h-4" /> Notifications
            </button>
          </div>

          {/* Content Area */}
          <div className="flex-1 space-y-6">
            
            {activeTab === "general" && (
              <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
                <h3 className="text-lg font-bold text-slate-900 mb-4">General Preferences</h3>
                
                <div className="space-y-5">
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1">Institution Name</label>
                    <input type="text" defaultValue="Sentinel University" className="w-full border border-slate-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1">Support Email</label>
                    <input type="email" defaultValue="support@sentinel.edu" className="w-full border border-slate-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1">Default Timezone</label>
                    <select className="w-full border border-slate-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
                      <option>UTC (Coordinated Universal Time)</option>
                      <option>EST (Eastern Standard Time)</option>
                      <option>PST (Pacific Standard Time)</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "risk" && (
              <div className="space-y-6">
                <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
                  <h3 className="text-lg font-bold text-slate-900 mb-1">AI Risk Engine Calibration</h3>
                  <p className="text-sm text-slate-500 mb-6">Adjust the weight of individual telemetry signals. Higher weights increase the candidate's total risk score faster.</p>
                  
                  <div className="space-y-6">
                    <div>
                      <div className="flex justify-between mb-1">
                        <label className="text-sm font-semibold text-slate-700">Multiple Faces Detected (Webcam)</label>
                        <span className="text-sm font-bold text-blue-600">High Impact (8.0)</span>
                      </div>
                      <input type="range" min="1" max="10" defaultValue="8" className="w-full accent-blue-600" />
                    </div>

                    <div>
                      <div className="flex justify-between mb-1">
                        <label className="text-sm font-semibold text-slate-700">Code Paste Attempt (Clipboard)</label>
                        <span className="text-sm font-bold text-blue-600">Medium Impact (5.0)</span>
                      </div>
                      <input type="range" min="1" max="10" defaultValue="5" className="w-full accent-blue-600" />
                    </div>

                    <div>
                      <div className="flex justify-between mb-1">
                        <label className="text-sm font-semibold text-slate-700">Browser Tab Blur</label>
                        <span className="text-sm font-bold text-blue-600">Low Impact (2.0)</span>
                      </div>
                      <input type="range" min="1" max="10" defaultValue="2" className="w-full accent-blue-600" />
                    </div>
                  </div>
                </div>

                <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
                  <h3 className="text-lg font-bold text-slate-900 mb-4">Risk Thresholds</h3>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="p-4 rounded-lg bg-amber-50 border border-amber-200">
                      <p className="text-xs font-bold text-amber-800 uppercase">Medium Risk</p>
                      <p className="text-2xl font-bold text-amber-900 mt-1">15 pts</p>
                    </div>
                    <div className="p-4 rounded-lg bg-orange-50 border border-orange-200">
                      <p className="text-xs font-bold text-orange-800 uppercase">High Risk</p>
                      <p className="text-2xl font-bold text-orange-900 mt-1">35 pts</p>
                    </div>
                    <div className="p-4 rounded-lg bg-red-50 border border-red-200">
                      <p className="text-xs font-bold text-red-800 uppercase">Critical</p>
                      <p className="text-2xl font-bold text-red-900 mt-1">60 pts</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "security" && (
              <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
                <h3 className="text-lg font-bold text-slate-900 mb-4">Security & Data Retention</h3>
                
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 border border-slate-200 rounded-lg">
                    <div>
                      <p className="font-semibold text-slate-900">Enforce 2FA for Admins</p>
                      <p className="text-sm text-slate-500">Require two-factor authentication for proctors and reviewers.</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" defaultChecked className="sr-only peer" />
                      <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between p-4 border border-slate-200 rounded-lg">
                    <div>
                      <p className="font-semibold text-slate-900">Video Evidence Retention</p>
                      <p className="text-sm text-slate-500">How long to store webcam snapshots for flagged exams.</p>
                    </div>
                    <select className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm outline-none">
                      <option>30 Days</option>
                      <option>90 Days</option>
                      <option>1 Year</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "notifications" && (
              <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
                <h3 className="text-lg font-bold text-slate-900 mb-4">Alert Routing</h3>
                
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 border border-slate-200 rounded-lg">
                    <div>
                      <p className="font-semibold text-slate-900">Critical Risk Email Alerts</p>
                      <p className="text-sm text-slate-500">Email lead proctors immediately when a candidate hits Critical risk.</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" defaultChecked className="sr-only peer" />
                      <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>
                </div>
              </div>
            )}

          </div>
        </div>
      </div>
    </div>
  );
}
