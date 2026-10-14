"use client";
export const dynamic = "force-dynamic";

import React, { useState, useEffect } from "react";
import { apiClient } from "@/services/apiClient";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { UserPlus, Loader2, ArrowLeft, Copy, KeyRound } from "lucide-react";
import Link from "next/link";
import toast from "react-hot-toast";

export default function CreateUserPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();
  
  useEffect(() => {
    if (!authLoading && (!user || user.role !== "admin")) {
      router.push("/dashboard");
    }
  }, [user, authLoading, router]);

  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    fullName: "",
    email: "",
    role: "candidate",
    department: "",
    batchYear: "",
    rollNumber: "",
  });
  const [generatePassword, setGeneratePassword] = useState(true);
  const [password, setPassword] = useState("");
  // Shown once after creation when the server generated the password.
  const [created, setCreated] = useState<{ email: string; temporary_password: string } | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const res = await apiClient.post<{ email: string; temporary_password?: string | null }>("/api/users", {
        full_name: formData.fullName,
        email: formData.email,
        role: formData.role,
        department: formData.department || undefined,
        batch_year: formData.batchYear ? Number(formData.batchYear) : undefined,
        roll_no: formData.rollNumber || undefined,
        password: generatePassword ? undefined : password,
      });
      toast.success("User created successfully!");
      if (res.temporary_password) {
        setCreated({ email: res.email, temporary_password: res.temporary_password });
      } else {
        router.push("/admin/users");
      }
    } catch (error) {
      console.error(error);
      toast.error(error instanceof Error ? error.message : "Failed to create user.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 p-6 sm:p-8 max-w-7xl mx-auto">
      <div className="flex items-center gap-4">
        <Link href="/admin/users" className="p-2 hover:bg-slate-100 rounded-full transition text-slate-500">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <UserPlus className="h-6 w-6 text-blue-600" />
            Create User
          </h1>
          <p className="text-slate-500 text-sm mt-1">Add a new user to the system.</p>
        </div>
      </div>

      {created && (
        <div className="max-w-2xl rounded-2xl border border-emerald-200 bg-emerald-50 p-6" role="status">
          <h2 className="flex items-center gap-2 font-semibold text-emerald-900">
            <KeyRound className="h-5 w-5" /> Account created for {created.email}
          </h2>
          <p className="mt-1 text-sm text-emerald-800">
            Share this temporary password securely. It is shown only once; the user can change it from their profile.
          </p>
          <div className="mt-3 flex items-center gap-2">
            <code className="flex-1 rounded-lg border border-emerald-200 bg-white px-3 py-2 font-mono text-sm text-slate-900">
              {created.temporary_password}
            </code>
            <button
              type="button"
              onClick={() => {
                void navigator.clipboard?.writeText(created.temporary_password);
                toast.success("Copied");
              }}
              className="inline-flex items-center gap-1 rounded-lg border border-emerald-300 bg-white px-3 py-2 text-sm font-medium text-emerald-800 hover:bg-emerald-100"
            >
              <Copy className="h-4 w-4" /> Copy
            </button>
          </div>
          <button
            type="button"
            onClick={() => router.push("/admin/users")}
            className="mt-4 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
          >
            Done
          </button>
        </div>
      )}

      <div className={`bg-white rounded-2xl shadow-sm border border-slate-200 p-6 max-w-2xl ${created ? "hidden" : ""}`}>
        <form onSubmit={handleSubmit} className="space-y-6">
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div className="col-span-1 sm:col-span-2">
              <label className="block text-sm font-medium text-slate-700 mb-1">Full Name</label>
              <input
                type="text"
                name="fullName"
                value={formData.fullName}
                onChange={handleChange}
                placeholder="John Doe"
                className="w-full border-slate-300 rounded-lg shadow-sm focus:border-blue-500 focus:ring-blue-500"
                required
              />
            </div>

            <div className="col-span-1 sm:col-span-2">
              <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="john.doe@example.com"
                className="w-full border-slate-300 rounded-lg shadow-sm focus:border-blue-500 focus:ring-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Role</label>
              <select
                name="role"
                value={formData.role}
                onChange={handleChange}
                className="w-full border-slate-300 rounded-lg shadow-sm focus:border-blue-500 focus:ring-blue-500"
              >
                <option value="candidate">Candidate</option>
                <option value="proctor">Proctor</option>
                <option value="reviewer">Reviewer</option>
                <option value="admin">Admin</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Department</label>
              <input
                type="text"
                name="department"
                value={formData.department}
                onChange={handleChange}
                placeholder="e.g. Computer Science"
                className="w-full border-slate-300 rounded-lg shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>

            {formData.role === "candidate" && (
              <>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Batch Year</label>
                  <input
                    type="text"
                    name="batchYear"
                    value={formData.batchYear}
                    onChange={handleChange}
                    placeholder="e.g. 2024"
                    className="w-full border-slate-300 rounded-lg shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Roll Number</label>
                  <input
                    type="text"
                    name="rollNumber"
                    value={formData.rollNumber}
                    onChange={handleChange}
                    placeholder="e.g. CS24001"
                    className="w-full border-slate-300 rounded-lg shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>
              </>
            )}
          </div>

          <div className="space-y-3 pt-2">
            <div className="flex items-center">
              <input
                id="generatePassword"
                type="checkbox"
                checked={generatePassword}
                onChange={(e) => setGeneratePassword(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              <label htmlFor="generatePassword" className="ml-2 block text-sm text-slate-700">
                Generate a secure temporary password (shown once after creating)
              </label>
            </div>
            {!generatePassword && (
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-1">Password</label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  minLength={8}
                  autoComplete="new-password"
                  placeholder="At least 8 characters"
                  className="w-full border-slate-300 rounded-lg shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  required
                />
              </div>
            )}
          </div>

          <div className="flex justify-end pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={() => router.push("/admin/users")}
              className="px-4 py-2 text-sm font-medium text-slate-700 hover:text-slate-900 mr-4"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !formData.fullName || !formData.email || (!generatePassword && password.length < 8)}
              className="flex items-center gap-2 bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-sm"
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              Create User
            </button>
          </div>
          
        </form>
      </div>
    </div>
  );
}
