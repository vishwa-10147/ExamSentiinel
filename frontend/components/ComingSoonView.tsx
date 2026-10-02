"use client";

import React, { useState } from "react";
import Link from "next/link";
import { 
  Sparkles, 
  Code2, 
  Rocket, 
  Clock, 
  ArrowLeft, 
  BookOpen, 
  Bell, 
  CheckCircle2, 
  Terminal, 
  Cpu, 
  Layers,
  ShieldCheck
} from "lucide-react";
import toast from "react-hot-toast";

interface ComingSoonViewProps {
  title: string;
  subtitle: string;
  badge: string;
  icon?: "code" | "problems";
  features?: { title: string; desc: string; icon: React.ElementType }[];
}

export default function ComingSoonView({
  title,
  subtitle,
  badge,
  icon = "code",
  features
}: ComingSoonViewProps) {
  const [email, setEmail] = useState("");
  const [subscribed, setSubscribed] = useState(false);

  const handleNotify = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !email.includes("@")) {
      toast.error("Please enter a valid email address.");
      return;
    }
    setSubscribed(true);
    toast.success("You're on the list! We will notify you when this feature launches.");
  };

  const defaultFeatures = [
    {
      title: "Interactive Code Sandbox",
      desc: "Multi-language online compiler supporting Python, C++, Java, JS, and SQL with real-time test execution.",
      icon: Terminal,
    },
    {
      title: "AI-Powered Diagnostics",
      desc: "Real-time AI coaching offering automated runtime optimization tips and hints without giving away solutions.",
      icon: Cpu,
    },
    {
      title: "Curated Problem Sets",
      desc: "Categorized DSA, SQL, and system design challenges ordered by difficulty with comprehensive test cases.",
      icon: Layers,
    },
    {
      title: "Performance Benchmarking",
      desc: "Compare your execution time, memory usage, and algorithm efficiency against institution leaderboards.",
      icon: ShieldCheck,
    },
  ];

  const displayFeatures = features || defaultFeatures;

  return (
    <div className="relative min-h-[85vh] w-full flex flex-col items-center justify-center p-4 sm:p-6 lg:p-8 overflow-hidden">
      {/* Background Decorative Glows */}
      <div className="absolute -top-24 -left-24 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-4xl mx-auto space-y-8 relative z-10">
        {/* Back link */}
        <Link
          href="/candidate/dashboard"
          className="inline-flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-blue-600 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Return to Dashboard
        </Link>

        {/* Hero Card */}
        <div className="bg-white border border-slate-200/80 rounded-3xl p-8 sm:p-12 shadow-xl shadow-slate-200/50 text-center relative overflow-hidden">
          {/* Subtle top banner glow */}
          <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600" />

          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200/60 text-xs font-bold uppercase tracking-wider mb-6 shadow-sm">
            <Sparkles className="w-3.5 h-3.5 text-blue-600 animate-pulse" />
            {badge}
          </div>

          {/* Icon Header */}
          <div className="mx-auto w-20 h-20 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/25 mb-6 group hover:scale-105 transition-transform duration-300">
            {icon === "code" ? (
              <Code2 className="w-10 h-10 group-hover:rotate-6 transition-transform" />
            ) : (
              <Rocket className="w-10 h-10 group-hover:rotate-6 transition-transform" />
            )}
          </div>

          {/* Title & Description */}
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate-900 tracking-tight mb-4">
            {title}
          </h1>
          <p className="max-w-2xl mx-auto text-base sm:text-lg text-slate-600 leading-relaxed mb-8">
            {subtitle}
          </p>

          {/* Email Notification Form */}
          <div className="max-w-md mx-auto mb-10">
            {subscribed ? (
              <div className="flex items-center justify-center gap-2 p-3.5 rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold text-sm">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                You'll be notified as soon as this releases!
              </div>
            ) : (
              <form onSubmit={handleNotify} className="flex flex-col sm:flex-row gap-2">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email for early access..."
                  className="flex-1 px-4 py-3 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm text-slate-900 bg-slate-50/50"
                  required
                />
                <button
                  type="submit"
                  className="px-5 py-3 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white rounded-xl text-sm font-bold transition-colors flex items-center justify-center gap-2 shadow-md shadow-blue-600/20 cursor-pointer"
                >
                  <Bell className="w-4 h-4" /> Notify Me
                </button>
              </form>
            )}
          </div>

          {/* Actions */}
          <div className="flex flex-wrap items-center justify-center gap-4 pt-4 border-t border-slate-100">
            <Link
              href="/candidate/exams"
              className="inline-flex items-center gap-2 px-6 py-3 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-sm font-bold transition-all shadow-md cursor-pointer"
            >
              <BookOpen className="w-4 h-4" /> Browse Active Exams
            </Link>
            <Link
              href="/candidate/results"
              className="inline-flex items-center gap-2 px-6 py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-sm font-semibold transition-all cursor-pointer"
            >
              View My Test Results
            </Link>
          </div>
        </div>

        {/* Feature Preview Grid */}
        <div className="space-y-4">
          <div className="text-center">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest">
              What's Coming in this Module
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {displayFeatures.map((feat, idx) => {
              const IconComp = feat.icon;
              return (
                <div
                  key={idx}
                  className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow flex items-start gap-4"
                >
                  <div className="p-3 rounded-xl bg-blue-50 text-blue-600 border border-blue-100 flex-shrink-0">
                    <IconComp className="w-5 h-5" />
                  </div>
                  <div className="space-y-1">
                    <h3 className="font-bold text-slate-900 text-sm">{feat.title}</h3>
                    <p className="text-xs text-slate-500 leading-relaxed">{feat.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
