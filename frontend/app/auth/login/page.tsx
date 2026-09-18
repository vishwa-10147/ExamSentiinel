"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { useAuth } from "@/contexts/AuthContext";
import { Shield, Lock, Mail, AlertCircle, Loader2, KeyRound } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { login, verifyOTP } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  
  // 2FA states
  const [requires2fa, setRequires2fa] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  const [otpCode, setOtpCode] = useState("");

  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Quick credentials for developer & demo testing
  const demoAccounts = [
    { role: "Admin", email: "admin@sentinel.edu", pass: "DemoPass123!" },
    { role: "Proctor", email: "proctor@sentinel.edu", pass: "DemoPass123!" },
    { role: "Reviewer", email: "reviewer@sentinel.edu", pass: "DemoPass123!" },
    { role: "Candidate", email: "candidate@sentinel.edu", pass: "DemoPass123!" },
  ];

  const handleDemoSelect = (account: typeof demoAccounts[0]) => {
    setEmail(account.email);
    setPassword(account.pass);
    setError(null);
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email || !password) {
      setError("Please fill in both email and password.");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await login(email, password);
      if (res?.requires_2fa) {
        setRequires2fa(true);
        setUserId(res.user_id);
      } else {
        router.push("/dashboard");
      }
    } catch (err: any) {
      setError(err?.message || "Invalid email or password. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!otpCode || otpCode.length !== 6) {
      setError("Please enter a valid 6-digit OTP.");
      return;
    }

    if (!userId) {
      setError("User ID missing. Please log in again.");
      return;
    }

    setIsSubmitting(true);
    try {
      await verifyOTP(userId, otpCode);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err?.message || "Invalid OTP code. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center p-4 sm:p-6 lg:p-8">
      <div className="w-full max-w-md space-y-8 rounded-2xl border border-slate-200 bg-white p-6 sm:p-8 shadow-sm">
        <div className="text-center">
          <Image src="/logo.png" alt="ExamSentinel Logo" width={48} height={48} style={{ width: "auto", height: "auto" }} className="mx-auto drop-shadow-sm" />
          <h2 className="mt-4 text-2xl font-bold tracking-tight text-slate-900">
            {requires2fa ? "Two-Factor Authentication" : "Sign in to ExamSentinel"}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            {requires2fa 
              ? "Enter the 6-digit code sent to your authenticator app" 
              : "Access secure examination & integrity review portal"}
          </p>
        </div>

        {error && (
          <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-3.5 text-sm text-red-700">
            <AlertCircle className="h-5 w-5 shrink-0 text-red-500" />
            <span>{error}</span>
          </div>
        )}

        {!requires2fa ? (
          <>
            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700">
                  Email Address
                </label>
                <div className="relative mt-1">
                  <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
                    <Mail className="h-4 w-4" />
                  </div>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@institution.edu"
                    className="block w-full rounded-lg border border-slate-300 py-2.5 pl-10 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700">
                    Password
                  </label>
                  <Link href="/auth/forgot-password" className="text-xs font-semibold text-blue-600 hover:text-blue-500 transition">
                    Forgot password?
                  </Link>
                </div>
                <div className="relative mt-1">
                  <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
                    <Lock className="h-4 w-4" />
                  </div>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="block w-full rounded-lg border border-slate-300 py-2.5 pl-10 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="flex w-full items-center justify-center rounded-lg bg-blue-600 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50 transition"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Authenticating...
                  </>
                ) : (
                  "Sign In"
                )}
              </button>
            </form>

            <div className="mt-4 text-center text-sm text-slate-600">
              Don't have an account?{" "}
              <Link href="/auth/register" className="font-semibold text-blue-600 hover:text-blue-500 transition">
                Register here
              </Link>
            </div>

            {/* Demo Accounts Quick-Fill Section */}
            <div className="border-t border-slate-200 mt-6 pt-5">
              <p className="text-center text-xs font-semibold uppercase tracking-wider text-slate-400">
                Quick Fill Demo Credentials
              </p>
              <div className="mt-3 grid grid-cols-2 gap-2">
                {demoAccounts.map((acc) => (
                  <button
                    key={acc.role}
                    type="button"
                    onClick={() => handleDemoSelect(acc)}
                    className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 hover:border-slate-300 transition text-left"
                  >
                    <span className="font-semibold text-blue-600">{acc.role}:</span> {acc.email.split("@")[0]}
                  </button>
                ))}
              </div>
            </div>
          </>
        ) : (
          <form onSubmit={handleVerifyOTP} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700">
                6-Digit OTP Code
              </label>
              <div className="relative mt-1">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
                  <KeyRound className="h-4 w-4" />
                </div>
                <input
                  type="text"
                  required
                  maxLength={6}
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                  placeholder="123456"
                  className="block w-full rounded-lg border border-slate-300 py-2.5 pl-10 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600 text-center tracking-widest text-lg font-mono"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting || otpCode.length !== 6}
              className="flex w-full items-center justify-center rounded-lg bg-blue-600 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50 transition"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Verifying...
                </>
              ) : (
                "Verify & Sign In"
              )}
            </button>
            <button
              type="button"
              onClick={() => {
                setRequires2fa(false);
                setOtpCode("");
              }}
              disabled={isSubmitting}
              className="w-full mt-2 text-sm text-slate-500 hover:text-slate-700 transition"
            >
              Back to Login
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
