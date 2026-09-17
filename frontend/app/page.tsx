"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { Shield, Lock, Eye, CheckCircle, ArrowRight, Server, Terminal, Video } from "lucide-react";

export default function HomePage() {
  const { isAuthenticated, user } = useAuth();

  const principles = [
    { title: "No Automated Guilt", desc: "The platform calculates risk scores and surfaces evidence; only human reviewers decide on misconduct." },
    { title: "Signals, Not Verdicts", desc: "Every detector feeds an evidence review queue, never an automated penalty." },
    { title: "No Overclaiming", desc: "The platform never implies monitoring coverage it doesn't actually possess." },
    { title: "Privacy by Design", desc: "Configurable retention, explicit consent capture, and encrypted audit trails." },
    { title: "Human Review at Every Step", desc: "Consequential actions always require human adjudication." },
  ];

  const tracks = [
    { name: "Core Exam Platform", desc: "MCQ, short/long answer, browser & webcam proctoring, risk engine, live dashboard" },
    { name: "Coding Exams", desc: "Monaco editor, sandboxed execution, autograding, large paste & typing cadence analysis" },
    { name: "Interview Exams", desc: "Live WebRTC rooms, panel rubric scoring, async recording, Whisper transcription" },
    { name: "Digital Extensions", desc: "2PL IRT adaptive engine, offline resilience via IndexedDB, whiteboard & diagramming" },
  ];

  return (
    <div className="flex flex-col items-center justify-center">
      {/* Hero Section */}
      <section className="w-full bg-gradient-to-b from-blue-50 to-white py-16 sm:py-24 border-b border-slate-200">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-white px-3 py-1 text-xs font-semibold text-blue-700 shadow-sm mb-6">
            <Shield className="h-3.5 w-3.5" />
            AI-Powered Examination Platform
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight text-slate-900 sm:text-6xl">
            Integrity with <span className="text-blue-600">Human Judgment</span>
          </h1>
          <p className="mt-6 text-lg leading-8 text-slate-600 max-w-2xl mx-auto">
            ExamSentinel lets institutions run secure online exams with intelligent, multi-modal proctoring.
            No AI model ever issues a final verdict; every signal is routed to human review.
          </p>

          <div className="mt-10 flex items-center justify-center gap-x-4">
            {isAuthenticated ? (
              <Link
                href={`/${user?.role || 'candidate'}/dashboard`}
                className="rounded-lg bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 flex items-center gap-2"
              >
                Go to Dashboard
                <ArrowRight className="h-4 w-4" />
              </Link>
            ) : (
              <>
                <Link
                  href="/auth/login"
                  className="rounded-lg bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 flex items-center gap-2"
                >
                  Sign In to Portal
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <a
                  href="/docs"
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-lg border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
                >
                  API Documentation
                </a>
              </>
            )}
          </div>
        </div>
      </section>

      {/* 5 Design Principles */}
      <section className="w-full max-w-7xl px-4 sm:px-6 lg:px-8 py-16">
        <h2 className="text-center text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
          Non-Negotiable Design Principles
        </h2>
        <p className="mt-3 text-center text-sm text-slate-600 max-w-xl mx-auto">
          Built from the ground up for fairness, privacy, and contestability.
        </p>
        <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {principles.map((p, idx) => (
            <div key={idx} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600 font-bold mb-4">
                0{idx + 1}
              </div>
              <h3 className="text-base font-semibold text-slate-900">{p.title}</h3>
              <p className="mt-2 text-sm text-slate-600">{p.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Feature Tracks */}
      <section className="w-full bg-slate-100 py-16 border-t border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-center text-2xl font-bold tracking-tight text-slate-900">
            Comprehensive Assessment Capabilities
          </h2>
          <div className="mt-10 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
            {tracks.map((t, idx) => (
              <div key={idx} className="rounded-xl bg-white p-6 border border-slate-200 shadow-sm">
                <h3 className="font-semibold text-slate-900 text-lg">{t.name}</h3>
                <p className="mt-2 text-sm text-slate-600">{t.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
