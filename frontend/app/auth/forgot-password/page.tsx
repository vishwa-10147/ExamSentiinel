"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ShieldCheck,
  Mail,
  AlertCircle,
  Loader2,
  KeyRound,
  Lock,
  Eye,
  EyeOff,
  CheckCircle2,
} from "lucide-react";
import { toast } from "react-hot-toast";
import { apiClient } from "@/services/apiClient";

export default function ForgotPasswordPage() {
  const router = useRouter();

  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [email, setEmail] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Step 1: Request OTP for registered email
  const handleRequestOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email.trim()) {
      setError("Please enter your registered email address.");
      return;
    }

    setIsSubmitting(true);
    try {
      await apiClient.post("/api/auth/forgot-password", { email: email.trim() });
      toast.success("Verification OTP code sent to your email address!");
      setStep(2);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || "Failed to send OTP code. Please verify email address.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Step 2: Verify 6-digit PIN/OTP Code
  const handleVerifyPIN = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!otpCode || otpCode.length !== 6) {
      setError("Please enter a valid 6-digit OTP passcode.");
      return;
    }

    setIsSubmitting(true);
    try {
      await apiClient.post("/api/auth/verify-forgot-otp", {
        email: email.trim(),
        otp_code: otpCode,
      });
      toast.success("Security PIN verified! Please set your new password.");
      setStep(3);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || "Invalid or expired OTP code.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Step 3: Set New Password
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!newPassword || newPassword.length < 8) {
      setError("New password must be at least 8 characters long.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match. Please ensure both password fields match.");
      return;
    }

    setIsSubmitting(true);
    try {
      await apiClient.post("/api/auth/reset-password", {
        email: email.trim(),
        otp_code: otpCode,
        new_password: newPassword,
      });
      toast.success("Password reset successfully! Please log in.");
      router.push("/auth/login");
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || "Failed to reset password.");
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
                Account Recovery & Reset
              </h2>
              <p className="text-slate-300 text-xs sm:text-sm mt-2 leading-relaxed">
                Secure multi-factor password reset workflow for institutional candidates and administrators.
              </p>
            </div>

            <div className="space-y-3 pt-2">
              <div className="flex items-center gap-2.5 text-xs text-slate-200">
                <CheckCircle2 className={`h-4 w-4 shrink-0 ${step >= 1 ? "text-emerald-400" : "text-slate-500"}`} />
                <span>Step 1: Verify Registered Email</span>
              </div>
              <div className="flex items-center gap-2.5 text-xs text-slate-200">
                <CheckCircle2 className={`h-4 w-4 shrink-0 ${step >= 2 ? "text-emerald-400" : "text-slate-500"}`} />
                <span>Step 2: Verify 6-Digit PIN Code</span>
              </div>
              <div className="flex items-center gap-2.5 text-xs text-slate-200">
                <CheckCircle2 className={`h-4 w-4 shrink-0 ${step >= 3 ? "text-emerald-400" : "text-slate-500"}`} />
                <span>Step 3: Set New Encrypted Password</span>
              </div>
            </div>
          </div>

          <div className="relative z-10 pt-8 border-t border-slate-800/80 text-[11px] text-slate-400">
            Account Security & Recovery System
          </div>
        </div>

        {/* Right Side: Form Card (7 Cols) */}
        <div className="lg:col-span-7 p-8 sm:p-10 flex flex-col justify-between">
          <div>
            <div className="mb-6">
              <h3 className="text-2xl font-bold text-slate-900">
                {step === 1 ? "Forgot Password" : step === 2 ? "Verify Security PIN" : "Set New Password"}
              </h3>
              <p className="text-slate-500 text-xs sm:text-sm mt-1">
                {step === 1
                  ? "Provide your email address to receive an authentication OTP code."
                  : step === 2
                  ? `Enter the 6-digit PIN / OTP code sent to ${email}`
                  : `PIN verified! Enter your new account password for ${email}`}
              </p>
            </div>

            {error && (
              <div className="mb-6 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-xs sm:text-sm text-red-700">
                <AlertCircle className="h-5 w-5 shrink-0 text-red-500 mt-0.5" />
                <span className="leading-relaxed">{error}</span>
              </div>
            )}

            {step === 1 && (
              /* Step 1 Form */
              <form onSubmit={handleRequestOTP} className="space-y-4">
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
                      placeholder="name@institution.edu"
                      className="block w-full rounded-xl border border-slate-300 py-2.5 pl-10 pr-3.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 outline-none transition"
                    />
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
                      Requesting OTP...
                    </>
                  ) : (
                    "Send Verification OTP"
                  )}
                </button>
              </form>
            )}

            {step === 2 && (
              /* Step 2 Form: PIN Code Only */
              <form onSubmit={handleVerifyPIN} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                    6-Digit PIN Code
                  </label>
                  <div className="relative">
                    <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
                      <KeyRound className="h-4 w-4" />
                    </div>
                    <input
                      type="text"
                      required
                      maxLength={6}
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ""))}
                      placeholder="Enter 6-digit code"
                      className="block w-full rounded-xl border border-slate-300 py-2.5 pl-10 pr-3.5 text-slate-900 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 outline-none text-center tracking-[0.4em] text-lg font-mono font-bold"
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
                      Verifying PIN...
                    </>
                  ) : (
                    "Verify PIN Code"
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setStep(1);
                    setOtpCode("");
                  }}
                  disabled={isSubmitting}
                  className="w-full text-xs font-semibold text-slate-500 hover:text-slate-800 transition"
                >
                  ← Back to Email Step
                </button>
              </form>
            )}

            {step === 3 && (
              /* Step 3 Form: New Password & Confirm Password */
              <form onSubmit={handleResetPassword} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                    New Password
                  </label>
                  <div className="relative">
                    <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
                      <Lock className="h-4 w-4" />
                    </div>
                    <input
                      type={showPassword ? "text" : "password"}
                      required
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Minimum 8 characters"
                      className="block w-full rounded-xl border border-slate-300 py-2.5 pl-10 pr-10 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 outline-none transition"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-0 flex items-center pr-3.5 text-slate-400 hover:text-slate-600 transition"
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                    Confirm New Password
                  </label>
                  <div className="relative">
                    <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
                      <Lock className="h-4 w-4" />
                    </div>
                    <input
                      type={showConfirmPassword ? "text" : "password"}
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Re-enter new password"
                      className="block w-full rounded-xl border border-slate-300 py-2.5 pl-10 pr-10 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 outline-none transition"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute inset-y-0 right-0 flex items-center pr-3.5 text-slate-400 hover:text-slate-600 transition"
                    >
                      {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting || newPassword.length < 8 || confirmPassword.length < 8}
                  className="w-full flex items-center justify-center gap-2 rounded-xl bg-blue-600 py-2.5 text-sm font-bold text-white shadow-md hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 transition"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Resetting Password...
                    </>
                  ) : (
                    "Reset Password & Sign In"
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setStep(2);
                    setNewPassword("");
                    setConfirmPassword("");
                  }}
                  disabled={isSubmitting}
                  className="w-full text-xs font-semibold text-slate-500 hover:text-slate-800 transition"
                >
                  ← Back to PIN Verification
                </button>
              </form>
            )}

          </div>

          <div className="mt-6 text-center text-xs text-slate-500">
            Remember your password?{" "}
            <Link href="/auth/login" className="font-bold text-blue-600 hover:underline">
              Sign in to portal
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
}

