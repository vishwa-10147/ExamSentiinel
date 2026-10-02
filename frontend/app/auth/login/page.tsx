"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { useAuth } from "@/contexts/AuthContext";
import {
  ShieldCheck,
  Lock,
  Mail,
  AlertCircle,
  Loader2,
  KeyRound,
  Eye,
  EyeOff,
  CheckCircle2,
  ArrowRight
} from "lucide-react";
import toast from "react-hot-toast";

export default function LoginPage() {
  const router = useRouter();
  const { login, verifyOTP } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  // 2FA states
  const [requires2fa, setRequires2fa] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  const [otpCode, setOtpCode] = useState("");

  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("reason") === "session_terminated") {
        setError("Your session was ended because another active login was initiated for this account.");
      } else if (params.get("error") === "sso_failed") {
        setError("Single Sign-On authentication failed. Please sign in with your email and password.");
      }
    }
  }, []);


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
        toast.success("Security verification required. Check your email for OTP.");
      } else {
        toast.success("Welcome back!");
        router.push("/dashboard");
      }
    } catch (err: any) {
      setError(err?.message || "Invalid email or password. Please check credentials.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!otpCode || otpCode.length !== 6) {
      setError("Please enter a valid 6-digit OTP code.");
      return;
    }

    if (!userId) {
      setError("User session expired. Please log in again.");
      return;
    }

    setIsSubmitting(true);
    try {
      await verifyOTP(userId, otpCode);
      toast.success("Two-Factor Authentication verified!");
      router.push("/dashboard");
    } catch (err: any) {
      setError(err?.message || "Invalid OTP verification code. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4 sm:p-6 lg:p-8 bg-slate-950/5 relative overflow-hidden">
      
      {/* Container Box */}
      <div className="w-full max-w-4xl bg-white rounded-3xl shadow-xl border border-slate-200 overflow-hidden grid grid-cols-1 lg:grid-cols-12 my-auto">
        
        {/* Left Side: Product Showcase Banner (5 Cols) */}
        <div className="lg:col-span-5 bg-gradient-to-br from-slate-900 via-slate-850 to-blue-950 p-8 sm:p-10 text-white flex flex-col justify-between relative overflow-hidden">
          {/* Subtle Background Glow */}
          <div className="absolute -top-24 -left-24 w-60 h-60 bg-blue-500/20 rounded-full blur-3xl" />
          <div className="absolute -bottom-24 -right-24 w-60 h-60 bg-indigo-500/20 rounded-full blur-3xl" />

          <div className="relative z-10 space-y-6">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-blue-600/30 border border-blue-400/30 rounded-xl backdrop-blur">
                <ShieldCheck className="h-7 w-7 text-blue-400" />
              </div>
              <span className="text-xl font-bold tracking-tight text-white">ExamSentinel</span>
            </div>

            <div>
              <h2 className="text-2xl font-extrabold text-white leading-tight">
                Secure AI Assessment Platform
              </h2>
              <p className="text-slate-300 text-xs sm:text-sm mt-2 leading-relaxed">
                Institutional examination environment with automated AI proctoring, risk calibration, and active session protection.
              </p>
            </div>

            {/* Feature Bullets */}
            <div className="space-y-3 pt-2">
              <div className="flex items-center gap-2.5 text-xs text-slate-200">
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                <span>Multi-Factor AI Face & Audio Detection</span>
              </div>
              <div className="flex items-center gap-2.5 text-xs text-slate-200">
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                <span>Single Active Session Lock & Token Security</span>
              </div>
              <div className="flex items-center gap-2.5 text-xs text-slate-200">
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                <span>Real-Time Instructor Proctoring Dashboard</span>
              </div>
            </div>
          </div>

          {/* Bottom Institutional Trust */}
          <div className="relative z-10 pt-8 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
            <span>ISO 27001 & FERPA Compliant</span>
            <span className="font-mono text-blue-400">v2.4.0</span>
          </div>
        </div>

        {/* Right Side: Form Credentials Card (7 Cols) */}
        <div className="lg:col-span-7 p-8 sm:p-10 flex flex-col justify-between">
          <div>
            <div className="mb-6">
              <h3 className="text-2xl font-bold text-slate-900">
                {requires2fa ? "Security Verification" : "Sign In to Portal"}
              </h3>
              <p className="text-slate-500 text-xs sm:text-sm mt-1">
                {requires2fa
                  ? "Enter the 6-digit OTP code dispatched to your registered email address."
                  : "Enter your institutional credentials to continue."}
              </p>
            </div>

            {/* Error Message */}
            {error && (
              <div className="mb-6 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-xs sm:text-sm text-red-700">
                <AlertCircle className="h-5 w-5 shrink-0 text-red-500 mt-0.5" />
                <span className="leading-relaxed">{error}</span>
              </div>
            )}

            {/* Standard Login Form */}
            {!requires2fa ? (
              <form onSubmit={handleLoginSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                    Email Address
                  </label>
                  <div className="relative">
                    <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
                      <Mail className="h-4 w-4" />
                    </div>
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="e.g. professor@university.edu"
                      className="block w-full rounded-xl border border-slate-300 py-2.5 pl-10 pr-3.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 outline-none transition"
                    />
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700">
                      Password
                    </label>
                    <Link
                      href="/auth/forgot-password"
                      className="text-xs font-semibold text-blue-600 hover:text-blue-700 transition"
                    >
                      Forgot password?
                    </Link>
                  </div>
                  <div className="relative">
                    <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
                      <Lock className="h-4 w-4" />
                    </div>
                    <input
                      type={showPassword ? "text" : "password"}
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="block w-full rounded-xl border border-slate-300 py-2.5 pl-10 pr-10 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 outline-none transition"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-0 flex items-center pr-3.5 text-slate-400 hover:text-slate-600 transition"
                      title={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full flex items-center justify-center gap-2 rounded-xl bg-blue-600 py-2.5 text-sm font-bold text-white shadow-md hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 transition"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Authenticating...
                    </>
                  ) : (
                    <>
                      Sign In to Account <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </button>
              </form>
            ) : (
              /* 2FA OTP Form */
              <form onSubmit={handleVerifyOTP} className="space-y-5">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1 text-center">
                    6-Digit Passcode
                  </label>
                  <div className="relative mt-2">
                    <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
                      <KeyRound className="h-4 w-4" />
                    </div>
                    <input
                      type="text"
                      required
                      maxLength={6}
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ""))}
                      placeholder="123456"
                      className="block w-full rounded-xl border border-slate-300 py-3 pl-10 pr-4 text-slate-900 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 outline-none text-center tracking-[0.4em] text-xl font-mono font-bold"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting || otpCode.length !== 6}
                  className="w-full flex items-center justify-center gap-2 rounded-xl bg-blue-600 py-2.5 text-sm font-bold text-white shadow-md hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 transition"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    "Confirm & Continue"
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setRequires2fa(false);
                    setOtpCode("");
                  }}
                  disabled={isSubmitting}
                  className="w-full text-xs font-semibold text-slate-500 hover:text-slate-800 transition"
                >
                  ← Return to email login
                </button>
              </form>
            )}

          </div>

          <div className="mt-6 text-center text-xs text-slate-500">
            Don&apos;t have an institutional candidate account?{" "}
            <Link href="/auth/register" className="font-bold text-blue-600 hover:underline">
              Register here
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
}
