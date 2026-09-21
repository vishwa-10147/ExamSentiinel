import { ThemeProvider } from "@/components/ThemeProvider";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { SidebarProvider } from "@/contexts/SidebarContext";
import { AuthProvider } from "@/contexts/AuthContext";
import Navbar from "@/components/Navbar";
import CookieBanner from "@/components/CookieBanner";
import { Toaster } from "react-hot-toast";

export const metadata: Metadata = {
  title: {
    template: "%s | ExamSentinel",
    default: "ExamSentinel â€” AI-Powered Examination Platform",
  },
  description: "Secure online exams with intelligent, human-reviewed integrity monitoring.",
  keywords: ["ExamSentinel", "Online Exams", "Proctoring", "AI Proctoring", "Secure Exams", "Education"],
  authors: [{ name: "ExamSentinel Team" }],
  creator: "ExamSentinel",
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://examsentinel.com/",
    title: "ExamSentinel â€” AI-Powered Examination Platform",
    description: "Secure online exams with intelligent, human-reviewed integrity monitoring.",
    siteName: "ExamSentinel",
  },
  twitter: {
    card: "summary_large_image",
    title: "ExamSentinel â€” AI-Powered Examination Platform",
    description: "Secure online exams with intelligent, human-reviewed integrity monitoring.",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-slate-50 dark:bg-slate-900 min-h-screen text-slate-900 dark:text-slate-50 antialiased font-sans transition-colors duration-200 overflow-x-hidden">
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
          <AuthProvider>
          <SidebarProvider>
          <div className="flex min-h-screen flex-col">
            <Navbar />
            <main className="flex-1 flex flex-col">{children}</main>
          </div>
        </SidebarProvider>
        </AuthProvider>
        <CookieBanner />
        <Toaster position="top-right" />
        </ThemeProvider>
      </body>
    </html>
  );
}

