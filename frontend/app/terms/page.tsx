import React from "react";
import { Metadata } from "next";
import Link from "next/link";
import { FileText, Shield, UserCheck, Lock, AlertCircle, ArrowLeft, Mail } from "lucide-react";

export const metadata: Metadata = {
  title: "Terms & Conditions | ExamSentinel",
  description: "Terms and conditions of service for the ExamSentinel platform.",
};

export default function TermsConditionsPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Navigation */}
        <Link 
          href="/" 
          className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Home
        </Link>

        {/* Header Card */}
        <div className="bg-gradient-to-r from-slate-900 to-blue-950 border border-slate-800 rounded-3xl p-8 shadow-2xl flex items-start justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <FileText className="w-3.5 h-3.5" /> Legal Governance
            </div>
            <h1 className="text-3xl font-extrabold text-white">Terms & Conditions of Service</h1>
            <p className="text-sm text-slate-400">
              Effective Date: {new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
            </p>
          </div>
          <div className="hidden sm:flex h-14 w-14 rounded-2xl bg-blue-600/20 border border-blue-500/30 items-center justify-center text-blue-400 shrink-0">
            <Shield className="w-7 h-7" />
          </div>
        </div>

        {/* Terms Sections */}
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 space-y-8 shadow-xl text-slate-300 text-sm leading-relaxed">
          
          <section className="space-y-3">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-600/20 text-blue-400 text-xs font-extrabold">1</span>
              Agreement to Terms
            </h2>
            <p>
              By accessing or using the ExamSentinel platform, you agree to be bound by these Terms and Conditions and our Privacy Policy. If you do not agree to these terms, you are not authorized to use or access our examination and proctoring services.
            </p>
          </section>

          <section className="space-y-3 pt-6 border-t border-slate-800/80">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-600/20 text-blue-400 text-xs font-extrabold">2</span>
              Description of Service
            </h2>
            <p>
              ExamSentinel provides an online examination and assessment platform featuring automated face tracking, browser focus telemetry, code execution sandboxes, and human-in-the-loop proctoring capabilities (&quot;Service&quot;). The Service includes web applications, algorithms, security frameworks, and evaluator dashboards.
            </p>
          </section>

          <section className="space-y-3 pt-6 border-t border-slate-800/80">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-600/20 text-blue-400 text-xs font-extrabold">3</span>
              User Responsibilities & Integrity Commitments
            </h2>
            <p>As a candidate or user of the Service, you agree to:</p>
            <ul className="list-disc pl-5 space-y-2 text-slate-300">
              <li>Provide accurate, truthful, and complete identity credentials during registration and examination check-in.</li>
              <li>Maintain strict confidentiality of your account credentials and one-time access keys.</li>
              <li>Comply with all exam integrity policies set by your institution or examination body.</li>
              <li>Not tamper with, bypass, or attempt to disable proctoring telemetry scripts or fullscreen browser locks.</li>
              <li>Not attempt unauthorized access to restricted endpoints, question banks, or evaluator dashboards.</li>
            </ul>
          </section>

          <section className="space-y-3 pt-6 border-t border-slate-800/80">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-600/20 text-blue-400 text-xs font-extrabold">4</span>
              Intellectual Property Rights
            </h2>
            <p>
              The Service, including its algorithms, user interface designs, code sandbox engine, brand assets, and original content, is the exclusive property of ExamSentinel and its licensors. You may not copy, modify, distribute, or reverse-engineer any part of the system without explicit written consent.
            </p>
          </section>

          <section className="space-y-3 pt-6 border-t border-slate-800/80">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-600/20 text-blue-400 text-xs font-extrabold">5</span>
              Limitation of Liability
            </h2>
            <p>
              In no event shall ExamSentinel or its directors, officers, or partners be liable for any indirect, incidental, special, or consequential damages resulting from network connectivity failures on candidate devices, unexcused hardware disconnects, or unauthorized breaches of user credentials.
            </p>
          </section>

          <section className="pt-6 border-t border-slate-800/80 bg-slate-950 p-6 rounded-2xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <h3 className="font-bold text-white text-sm">Questions Regarding Our Terms?</h3>
              <p className="text-xs text-slate-400 mt-1">Contact our legal and compliance department.</p>
            </div>
            <a
              href="mailto:legal@examsentinel.com"
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-blue-600/20"
            >
              <Mail className="w-4 h-4" /> legal@examsentinel.com
            </a>
          </section>

        </div>
      </div>
    </div>
  );
}
