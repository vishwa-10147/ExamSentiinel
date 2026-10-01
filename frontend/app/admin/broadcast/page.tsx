"use client";
export const dynamic = "force-dynamic";

import React, { useState, useEffect } from "react";
import { apiClient } from "@/services/apiClient";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { 
  Mail, 
  Send, 
  Loader2, 
  CheckCircle2, 
  AlertCircle, 
  Eye, 
  Edit3, 
  Users, 
  BookOpen, 
  Sparkles, 
  ShieldAlert, 
  FileText, 
  Info,
  Layers,
  ChevronRight
} from "lucide-react";
import toast from "react-hot-toast";

interface ExamOption {
  id: string;
  title: string;
  status: string;
}

interface BroadcastStatus {
  configured: boolean;
  enabled: boolean;
  sender: string;
  smtp_host?: string;
}

export default function BroadcastPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();
  
  useEffect(() => {
    if (!authLoading && (!user || user.role !== "admin")) {
      router.push("/dashboard");
    }
  }, [user, authLoading, router]);

  const [status, setStatus] = useState<BroadcastStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  
  const [recipientCategory, setRecipientCategory] = useState<"role" | "all" | "exam">("role");
  const [targetRole, setTargetRole] = useState<"candidate" | "proctor" | "reviewer" | "admin">("candidate");
  const [selectedExamId, setSelectedExamId] = useState<string>("");
  
  const [exams, setExams] = useState<ExamOption[]>([]);
  const [examsLoading, setExamsLoading] = useState(false);

  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [activeTab, setActiveTab] = useState<"write" | "preview">("write");
  const [sending, setSending] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  // Fetch status on mount
  useEffect(() => {
    fetchStatus();
    fetchExams();
  }, []);

  const fetchStatus = async () => {
    setStatusLoading(true);
    try {
      const data = await apiClient.get<BroadcastStatus>("/api/admin/broadcast/status");
      setStatus(data);
    } catch (err) {
      console.error("Failed to load broadcast status", err);
    } finally {
      setStatusLoading(false);
    }
  };

  const fetchExams = async () => {
    setExamsLoading(true);
    try {
      const data = await apiClient.get<ExamOption[]>("/api/exams");
      setExams(data || []);
      if (data && data.length > 0) {
        setSelectedExamId(data[0].id);
      }
    } catch (err) {
      console.error("Failed to fetch exams list", err);
    } finally {
      setExamsLoading(false);
    }
  };

  const applyTemplate = (tplSubject: string, tplBody: string) => {
    setSubject(tplSubject);
    setBody(tplBody);
    toast.success("Template loaded successfully!");
  };

  const insertVariable = (varName: string) => {
    setBody((prev) => prev + ` {{${varName}}}`);
  };

  const handleOpenConfirm = (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject.trim() || !body.trim()) {
      toast.error("Please provide both a subject line and email body.");
      return;
    }
    if (recipientCategory === "exam" && !selectedExamId) {
      toast.error("Please select a target exam.");
      return;
    }
    setShowConfirmModal(true);
  };

  const executeSendBroadcast = async () => {
    setSending(true);
    setShowConfirmModal(false);

    const payload: any = {
      subject: subject.trim(),
      body: body.trim(),
    };

    if (recipientCategory === "all") {
      payload.all_users = true;
    } else if (recipientCategory === "role") {
      payload.target_role = targetRole;
    } else if (recipientCategory === "exam") {
      payload.exam_id = selectedExamId;
    }

    try {
      const res = await apiClient.post<{ status: string; recipients: number }>(
        "/api/admin/broadcast",
        payload
      );
      toast.success(`Broadcast successfully sent to ${res.recipients} recipient(s)!`);
      setSubject("");
      setBody("");
      setActiveTab("write");
    } catch (error: any) {
      console.error("Broadcast failed:", error);
      toast.error(error?.message || "Failed to send broadcast email.");
    } finally {
      setSending(false);
    }
  };

  const getTargetDescription = () => {
    if (recipientCategory === "all") return "All Registered Users in the System";
    if (recipientCategory === "role") return `All ${targetRole.toUpperCase()} Account Holders`;
    if (recipientCategory === "exam") {
      const selected = exams.find((e) => e.id === selectedExamId);
      return selected ? `Enrolled Candidates for "${selected.title}"` : "Selected Exam Candidates";
    }
    return "Target Audience";
  };

  const wordCount = body.trim() ? body.trim().split(/\s+/).length : 0;
  const estimatedReadTime = Math.ceil(wordCount / 200);

  return (
    <div className="space-y-6 p-6 sm:p-8 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Mail className="h-6 w-6 text-blue-600" />
            Email Broadcast Center
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Dispatch announcements, urgent exam reminders, and automated notices to targeted groups.
          </p>
        </div>

        {/* SMTP Health Badge */}
        <div className="flex items-center gap-3">
          {statusLoading ? (
            <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-100 px-3 py-1.5 rounded-full border border-slate-200">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Checking SMTP Status...
            </div>
          ) : status?.configured ? (
            <div className="flex items-center gap-2 text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-full">
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              <span>SMTP Ready ({status.sender})</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 px-3 py-1.5 rounded-full" title="ENABLE_EMAILS is false or SMTP server settings are unconfigured in environment">
              <AlertCircle className="h-4 w-4 text-amber-600" />
              <span>SMTP Unconfigured (Sandbox Mode)</span>
            </div>
          )}
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Form & Editor (2 Cols) */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            
            {/* Header Tabs */}
            <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 bg-slate-50/50">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setActiveTab("write")}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                    activeTab === "write"
                      ? "bg-white text-blue-600 shadow-sm border border-slate-200"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                  }`}
                >
                  <Edit3 className="h-4 w-4" /> Compose Message
                </button>

                <button
                  type="button"
                  onClick={() => setActiveTab("preview")}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                    activeTab === "preview"
                      ? "bg-white text-blue-600 shadow-sm border border-slate-200"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                  }`}
                >
                  <Eye className="h-4 w-4" /> Live Email Preview
                </button>
              </div>

              <div className="text-xs text-slate-500 hidden sm:block">
                {wordCount} words • ~{estimatedReadTime} min read
              </div>
            </div>

            {/* Form Content */}
            <form onSubmit={handleOpenConfirm} className="p-6 space-y-6">
              
              {/* Recipient Targeting Selector */}
              <div className="space-y-3">
                <label className="block text-sm font-semibold text-slate-900">
                  Target Audience
                </label>
                
                <div className="grid grid-cols-3 gap-3">
                  <button
                    type="button"
                    onClick={() => setRecipientCategory("role")}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      recipientCategory === "role"
                        ? "border-blue-600 bg-blue-50/50 ring-2 ring-blue-500/20"
                        : "border-slate-200 hover:border-slate-300 bg-white"
                    }`}
                  >
                    <Users className={`h-5 w-5 mb-1 ${recipientCategory === "role" ? "text-blue-600" : "text-slate-400"}`} />
                    <div className="text-sm font-medium text-slate-900">User Role</div>
                    <div className="text-xs text-slate-500">Filter by system role</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setRecipientCategory("exam")}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      recipientCategory === "exam"
                        ? "border-blue-600 bg-blue-50/50 ring-2 ring-blue-500/20"
                        : "border-slate-200 hover:border-slate-300 bg-white"
                    }`}
                  >
                    <BookOpen className={`h-5 w-5 mb-1 ${recipientCategory === "exam" ? "text-blue-600" : "text-slate-400"}`} />
                    <div className="text-sm font-medium text-slate-900">Exam Specific</div>
                    <div className="text-xs text-slate-500">Candidates in exam</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setRecipientCategory("all")}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      recipientCategory === "all"
                        ? "border-blue-600 bg-blue-50/50 ring-2 ring-blue-500/20"
                        : "border-slate-200 hover:border-slate-300 bg-white"
                    }`}
                  >
                    <Layers className={`h-5 w-5 mb-1 ${recipientCategory === "all" ? "text-blue-600" : "text-slate-400"}`} />
                    <div className="text-sm font-medium text-slate-900">All System Users</div>
                    <div className="text-xs text-slate-500">Global announcement</div>
                  </button>
                </div>

                {/* Sub-selectors */}
                {recipientCategory === "role" && (
                  <div className="pt-2">
                    <label className="block text-xs font-medium text-slate-600 mb-1">Select Role Group</label>
                    <select
                      value={targetRole}
                      onChange={(e: any) => setTargetRole(e.target.value)}
                      className="w-full border-slate-300 rounded-lg shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
                    >
                      <option value="candidate">Candidates (Students / Test Takers)</option>
                      <option value="proctor">Proctors & Invigilators</option>
                      <option value="reviewer">Reviewers & Evaluators</option>
                      <option value="admin">Administrators</option>
                    </select>
                  </div>
                )}

                {recipientCategory === "exam" && (
                  <div className="pt-2">
                    <label className="block text-xs font-medium text-slate-600 mb-1">Select Target Exam</label>
                    {examsLoading ? (
                      <div className="flex items-center gap-2 text-xs text-slate-500 p-2">
                        <Loader2 className="h-4 w-4 animate-spin text-blue-600" /> Loading active exams...
                      </div>
                    ) : (
                      <select
                        value={selectedExamId}
                        onChange={(e) => setSelectedExamId(e.target.value)}
                        className="w-full border-slate-300 rounded-lg shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
                      >
                        {exams.map((ex) => (
                          <option key={ex.id} value={ex.id}>
                            {ex.title} ({ex.status})
                          </option>
                        ))}
                      </select>
                    )}
                  </div>
                )}
              </div>

              {/* View Active Tab: Write Mode vs Preview Mode */}
              {activeTab === "write" ? (
                <div className="space-y-4">
                  {/* Subject Line */}
                  <div>
                    <label className="block text-sm font-semibold text-slate-900 mb-1">
                      Subject Line
                    </label>
                    <input
                      type="text"
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                      placeholder="e.g. Action Required: Mandatory Midterm Exam Guidelines & System Check"
                      className="w-full border-slate-300 rounded-lg shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm py-2.5"
                      required
                    />
                  </div>

                  {/* Body Field */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="block text-sm font-semibold text-slate-900">
                        Message Content
                      </label>
                      
                      {/* Placeholders Toolbar */}
                      <div className="flex items-center gap-1.5 text-xs text-slate-500">
                        <span className="hidden sm:inline">Dynamic tags:</span>
                        <button
                          type="button"
                          onClick={() => insertVariable("user_name")}
                          className="px-2 py-0.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded font-mono border border-slate-200 transition"
                        >
                          {"{{user_name}}"}
                        </button>
                        <button
                          type="button"
                          onClick={() => insertVariable("exam_title")}
                          className="px-2 py-0.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded font-mono border border-slate-200 transition"
                        >
                          {"{{exam_title}}"}
                        </button>
                      </div>
                    </div>

                    <textarea
                      value={body}
                      onChange={(e) => setBody(e.target.value)}
                      placeholder="Dear Candidate,&#10;&#10;Please be reminded that your upcoming assessment will begin promptly..."
                      rows={10}
                      className="w-full border-slate-300 rounded-lg shadow-sm focus:border-blue-500 focus:ring-blue-500 font-sans text-sm leading-relaxed"
                      required
                    />
                  </div>
                </div>
              ) : (
                /* Email HTML Live Preview Tab */
                <div className="border border-slate-200 rounded-xl overflow-hidden bg-slate-50 p-4">
                  <div className="bg-white rounded-lg shadow border border-slate-200 max-w-xl mx-auto overflow-hidden">
                    {/* Mock Email Header */}
                    <div className="bg-slate-900 text-white p-6 text-center">
                      <div className="text-xl font-bold tracking-tight text-blue-400">ExamSentinel</div>
                      <div className="text-xs text-slate-400 mt-0.5">Secure AI-Powered Assessment Platform</div>
                    </div>

                    {/* Email Meta Bar */}
                    <div className="bg-slate-50 border-b border-slate-200 px-6 py-3 text-xs text-slate-600 space-y-1">
                      <div><strong className="text-slate-900">From:</strong> {status?.sender || "noreply@exams.myuniversity.edu"}</div>
                      <div><strong className="text-slate-900">To:</strong> [Recipient Name] &lt;{getTargetDescription()}&gt;</div>
                      <div><strong className="text-slate-900">Subject:</strong> {subject || "(No subject entered)"}</div>
                    </div>

                    {/* Email Body */}
                    <div className="p-6 text-slate-800 text-sm space-y-4 leading-relaxed whitespace-pre-wrap font-sans">
                      {body ? (
                        body
                      ) : (
                        <p className="text-slate-400 italic">No message body typed yet. Compose your message to see a live preview here.</p>
                      )}
                    </div>

                    {/* Mock Email Footer */}
                    <div className="bg-slate-50 border-t border-slate-200 p-6 text-center text-xs text-slate-500 space-y-2">
                      <p>This is an official automated notification from ExamSentinel Administrative System.</p>
                      <p className="text-slate-400">© {new Date().getFullYear()} ExamSentinel Inc. All rights reserved.</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Submit Section */}
              <div className="flex items-center justify-between pt-4 border-t border-slate-200">
                <div className="text-xs text-slate-500 flex items-center gap-1.5">
                  <Info className="h-4 w-4 text-blue-500" />
                  Sending to <strong className="text-slate-800">{getTargetDescription()}</strong>
                </div>

                <button
                  type="submit"
                  disabled={sending || !subject.trim() || !body.trim()}
                  className="flex items-center gap-2 bg-blue-600 text-white px-6 py-2.5 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-md font-medium text-sm"
                >
                  {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  Review & Broadcast
                </button>
              </div>

            </form>
          </div>
        </div>

        {/* Right Column: Templates & Guide (1 Col) */}
        <div className="space-y-6">
          
          {/* Quick Preset Templates */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5 space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-amber-500" />
              Quick Templates
            </h3>
            <p className="text-xs text-slate-500">
              Click any template to quickly pre-populate subject and formatted text.
            </p>

            <div className="space-y-2">
              <button
                type="button"
                onClick={() =>
                  applyTemplate(
                    "Important: Upcoming Exam Schedule & Proctoring Rules",
                    "Dear Candidate,\n\nPlease review your upcoming scheduled exam details on your dashboard.\n\nKey Requirements:\n1. Ensure a working webcam and microphone.\n2. Use a stable high-speed internet connection.\n3. Keep your photo ID handy for verification.\n\nGood luck with your examination!\n\nBest regards,\nExamSentinel Team"
                  )
                }
                className="w-full p-3 rounded-xl border border-slate-200 hover:border-blue-300 hover:bg-blue-50/50 text-left transition group"
              >
                <div className="text-xs font-semibold text-slate-900 group-hover:text-blue-600 flex items-center justify-between">
                  Exam Schedule Notice
                  <ChevronRight className="h-3.5 w-3.5 text-slate-400 group-hover:text-blue-600" />
                </div>
                <div className="text-[11px] text-slate-500 mt-1 line-clamp-2">
                  Pre-fills exam instructions, webcam requirements, and timing guidelines.
                </div>
              </button>

              <button
                type="button"
                onClick={() =>
                  applyTemplate(
                    "System Maintenance Notice - Scheduled Portal Outage",
                    "Dear Users,\n\nPlease be advised that ExamSentinel will undergo routine system maintenance during the following window:\n\nDate & Time: Saturday 02:00 AM - 04:00 AM UTC\nExpected Downtime: 2 Hours\n\nNo active exams will be scheduled during this window. Thank you for your patience.\n\nExamSentinel Technical Team"
                  )
                }
                className="w-full p-3 rounded-xl border border-slate-200 hover:border-blue-300 hover:bg-blue-50/50 text-left transition group"
              >
                <div className="text-xs font-semibold text-slate-900 group-hover:text-blue-600 flex items-center justify-between">
                  System Maintenance
                  <ChevronRight className="h-3.5 w-3.5 text-slate-400 group-hover:text-blue-600" />
                </div>
                <div className="text-[11px] text-slate-500 mt-1 line-clamp-2">
                  Informs candidates and proctors of upcoming platform maintenance.
                </div>
              </button>

              <button
                type="button"
                onClick={() =>
                  applyTemplate(
                    "Urgent: Exam Security & Anti-Cheating Protocol Enforcement",
                    "Attention Candidates,\n\nOur AI proctoring system enforces strict academic integrity guidelines. During your assessment, the following actions will trigger automatic flag reports:\n\n- Looking away from screen continuously\n- Multiple face detections or unauthorized background voices\n- Switching browser tabs or windows\n\nFailure to comply may result in immediate session termination.\n\nAcademic Integrity Committee"
                  )
                }
                className="w-full p-3 rounded-xl border border-slate-200 hover:border-blue-300 hover:bg-blue-50/50 text-left transition group"
              >
                <div className="text-xs font-semibold text-slate-900 group-hover:text-blue-600 flex items-center justify-between">
                  Proctoring Warning
                  <ChevronRight className="h-3.5 w-3.5 text-slate-400 group-hover:text-blue-600" />
                </div>
                <div className="text-[11px] text-slate-500 mt-1 line-clamp-2">
                  Reminds test takers of anti-cheating guidelines and AI monitoring.
                </div>
              </button>
            </div>
          </div>

          {/* Delivery Tips / Audit Note */}
          <div className="bg-slate-900 rounded-2xl p-5 text-white space-y-3 shadow-sm">
            <div className="flex items-center gap-2 text-xs font-semibold text-blue-400 uppercase tracking-wider">
              <ShieldAlert className="h-4 w-4" /> Broadcast Audit Policy
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              All sent broadcast messages are logged in the System Audit Trail along with your admin ID, timestamp, and recipient counts.
            </p>
            <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
              <span>Security Level:</span>
              <span className="font-mono text-emerald-400">ADMINISTRATOR ONLY</span>
            </div>
          </div>

        </div>
      </div>

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-md w-full p-6 space-y-5">
            <div className="flex items-center gap-3 text-amber-600">
              <div className="p-3 bg-amber-50 rounded-xl">
                <Send className="h-6 w-6 text-amber-600" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Confirm Broadcast Dispatch</h3>
                <p className="text-xs text-slate-500">Please review before sending mass email</p>
              </div>
            </div>

            <div className="bg-slate-50 p-4 rounded-xl space-y-2 border border-slate-200 text-xs">
              <div>
                <span className="text-slate-500">Target Audience:</span>{" "}
                <strong className="text-slate-900">{getTargetDescription()}</strong>
              </div>
              <div>
                <span className="text-slate-500">Subject:</span>{" "}
                <strong className="text-slate-900">{subject}</strong>
              </div>
              <div>
                <span className="text-slate-500">Content Length:</span>{" "}
                <strong className="text-slate-900">{wordCount} words (~{estimatedReadTime} min read)</strong>
              </div>
            </div>

            <p className="text-xs text-slate-500">
              This action will queue emails for dispatch. Make sure all instructions and details are accurate.
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={executeSendBroadcast}
                disabled={sending}
                className="flex items-center gap-2 bg-blue-600 text-white px-5 py-2 rounded-lg hover:bg-blue-700 transition text-xs font-semibold shadow-sm"
              >
                {sending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Confirm & Send Now
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
