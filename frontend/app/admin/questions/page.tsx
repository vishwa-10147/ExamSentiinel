"use client";
export const dynamic = "force-dynamic";

import React, { useEffect, useState, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import { Plus, Library, Trash2, Edit, AlertCircle, Type, BarChart, Upload, Search, X, CheckCircle2 } from "lucide-react";
import toast, { Toaster } from "react-hot-toast";

interface Question {
  id: string;
  title: string;
  content_rich_text?: string;
  type: string;
  difficulty: string;
  points?: number;
  options?: string[] | string;
  correct_answer?: any;
}

export default function QuestionsPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string>("All");
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>("All");

  // Modal & Form states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editingQuestionId, setEditingQuestionId] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    title: "",
    content_rich_text: "",
    type: "multiple_choice",
    difficulty: "MEDIUM",
    points: 10,
    optionsStr: "",
    correctAnswer: "",
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploadingCSV, setIsUploadingCSV] = useState(false);

  const fetchQuestions = async () => {
    try {
      setLoading(true);
      const data = await apiClient.get<Question[]>("/api/questions");
      setQuestions(data);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch questions", err);
      setQuestions([]);
      setError("Failed to load questions. Please try again later.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isLoading || !user || user.role !== "admin") return;
    void fetchQuestions();
  }, [isLoading, user]);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setIsUploadingCSV(true);
    const form = new FormData();
    form.append("file", file);
    try {
      await apiClient.upload("/api/questions/bulk", form);
      toast.success("Questions imported successfully!");
      void fetchQuestions();
    } catch (err: any) {
      console.error(err);
      toast.error(err?.message || "Error uploading CSV.");
    } finally {
      setIsUploadingCSV(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const filteredQuestions = useMemo(() => {
    return questions.filter((q) => {
      const matchesSearch =
        !searchQuery.trim() ||
        q.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (q.content_rich_text && q.content_rich_text.toLowerCase().includes(searchQuery.toLowerCase()));

      const normalizedType = (q.type || "").toLowerCase().replace("_", " ");
      const matchesType =
        selectedType === "All" ||
        normalizedType.includes(selectedType.toLowerCase().replace("_", " "));

      const matchesDiff =
        selectedDifficulty === "All" ||
        q.difficulty.toUpperCase() === selectedDifficulty.toUpperCase();

      return matchesSearch && matchesType && matchesDiff;
    });
  }, [questions, searchQuery, selectedType, selectedDifficulty]);

  const handleOpenAddModal = () => {
    setIsEditMode(false);
    setEditingQuestionId(null);
    setFormData({
      title: "",
      content_rich_text: "",
      type: "multiple_choice",
      difficulty: "MEDIUM",
      points: 10,
      optionsStr: "",
      correctAnswer: "",
    });
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (q: Question) => {
    setIsEditMode(true);
    setEditingQuestionId(q.id);

    let optionsVal = "";
    if (Array.isArray(q.options)) {
      optionsVal = q.options.join(", ");
    } else if (typeof q.options === "string") {
      optionsVal = q.options;
    }

    let correctVal = "";
    if (typeof q.correct_answer === "string") {
      correctVal = q.correct_answer;
    } else if (typeof q.correct_answer === "object" && q.correct_answer !== null) {
      correctVal = JSON.stringify(q.correct_answer);
    }

    setFormData({
      title: q.title || "",
      content_rich_text: q.content_rich_text || q.title || "",
      type: (q.type || "multiple_choice").toLowerCase(),
      difficulty: (q.difficulty || "MEDIUM").toUpperCase(),
      points: q.points || 10,
      optionsStr: optionsVal,
      correctAnswer: correctVal,
    });
    setIsModalOpen(true);
  };

  const handleDeleteQuestion = async (q: Question) => {
    if (!window.confirm(`Are you sure you want to delete question "${q.title}"?`)) {
      return;
    }
    try {
      await apiClient.delete(`/api/questions/${q.id}`);
      toast.success("Question deleted successfully");
      void fetchQuestions();
    } catch (err: any) {
      console.error("Failed to delete question", err);
      toast.error(err?.message || "Failed to delete question.");
    }
  };

  const handleSaveQuestion = async () => {
    if (!formData.title.trim()) {
      toast.error("Question title is required.");
      return;
    }

    setIsSubmitting(true);
    try {
      const optionsArray = formData.optionsStr
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

      const payload = {
        title: formData.title,
        content_rich_text: formData.content_rich_text || formData.title,
        type: formData.type,
        difficulty: formData.difficulty,
        points: Number(formData.points) || 10,
        options: optionsArray.length > 0 ? optionsArray : undefined,
        correct_answer: formData.correctAnswer || undefined,
      };

      if (isEditMode && editingQuestionId) {
        await apiClient.put(`/api/questions/${editingQuestionId}`, payload);
        toast.success("Question updated successfully");
      } else {
        await apiClient.post("/api/questions", payload);
        toast.success("Question created successfully");
      }

      setIsModalOpen(false);
      void fetchQuestions();
    } catch (err: any) {
      console.error("Failed to save question", err);
      toast.error(err?.message || "Failed to save question. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading || !user) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center text-slate-500">Loading question bank...</div>
      </div>
    );
  }

  if (user.role !== "admin") {
    return (
      <div className="flex-1 w-full">
        <div className="flex-1 p-8 text-center text-red-500 font-semibold">
          Access Denied. Admins only.
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 w-full">
      <Toaster position="top-right" />
      <main className="flex-1 flex flex-col overflow-y-auto">
        <div className="p-6 sm:p-8 max-w-7xl mx-auto w-full">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5 mb-8">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
                <Library className="h-6 w-6 text-blue-600" />
                Question Bank
              </h1>
              <p className="text-sm text-slate-500 mt-1">
                Manage, organize, and import questions for all online exams.
              </p>
            </div>
            
            <div className="flex items-center gap-3">
              <input type="file" accept=".csv" ref={fileInputRef} className="hidden" onChange={handleFileUpload} />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploadingCSV}
                className="inline-flex items-center gap-2 bg-slate-100 hover:bg-slate-200 text-slate-700 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 border border-slate-200"
              >
                <Upload className="h-4 w-4" />
                {isUploadingCSV ? "Importing..." : "Import CSV"}
              </button>
              <button
                onClick={handleOpenAddModal}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 transition-colors"
              >
                <Plus className="h-4 w-4" />
                Create Question
              </button>
            </div>
          </div>

          {error && (
            <div className="mb-6 flex items-center gap-2 rounded-lg bg-amber-50 p-4 border border-amber-200 text-sm text-amber-800">
              <AlertCircle className="h-5 w-5 text-amber-600" />
              {error}
            </div>
          )}

          {/* Search & Filter Bar */}
          <div className="mb-6 flex flex-col md:flex-row gap-3 items-center justify-between">
            <div className="relative w-full md:max-w-md">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-4 w-4 text-slate-400" />
              </div>
              <input
                type="text"
                placeholder="Search questions by title or description..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="block w-full pl-9 pr-8 py-2 border border-slate-300 rounded-lg text-sm bg-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>

            <div className="flex items-center gap-3 w-full md:w-auto">
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm bg-white text-slate-700 outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="All">All Types</option>
                <option value="multiple_choice">Multiple Choice</option>
                <option value="coding">Coding</option>
                <option value="short_answer">Short Answer</option>
              </select>

              <select
                value={selectedDifficulty}
                onChange={(e) => setSelectedDifficulty(e.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm bg-white text-slate-700 outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="All">All Difficulties</option>
                <option value="EASY">Easy</option>
                <option value="MEDIUM">Medium</option>
                <option value="HARD">Hard</option>
              </select>
            </div>
          </div>

          {/* Table Card */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Title & Description
                    </th>
                    <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Type
                    </th>
                    <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Difficulty & Points
                    </th>
                    <th scope="col" className="px-6 py-4 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 bg-white">
                  {loading ? (
                    <tr>
                      <td colSpan={4} className="px-6 py-12 text-center text-sm text-slate-500">
                        Loading questions...
                      </td>
                    </tr>
                  ) : filteredQuestions.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-6 py-12 text-center text-sm text-slate-500">
                        No questions match your criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredQuestions.map((q) => {
                      const displayDiff = (q.difficulty || "MEDIUM").toUpperCase();
                      const displayType = (q.type || "multiple_choice").replace("_", " ");
                      return (
                        <tr key={q.id} className="hover:bg-slate-50/50 transition-colors">
                          <td className="px-6 py-4">
                            <div className="text-sm font-semibold text-slate-900">{q.title}</div>
                            {q.content_rich_text && q.content_rich_text !== q.title && (
                              <div className="text-xs text-slate-500 truncate max-w-md mt-0.5">
                                {q.content_rich_text}
                              </div>
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center text-sm text-slate-700 capitalize">
                              <Type className="h-4 w-4 mr-2 text-slate-400" />
                              {displayType}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center gap-2 text-sm text-slate-700">
                              <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${
                                displayDiff === 'EASY' ? 'bg-emerald-50 text-emerald-700 ring-emerald-600/20' :
                                displayDiff === 'HARD' ? 'bg-red-50 text-red-700 ring-red-600/10' :
                                'bg-amber-50 text-amber-800 ring-amber-600/20'
                              }`}>
                                {displayDiff}
                              </span>
                              <span className="text-xs text-slate-400">• {q.points || 10} pts</span>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <button 
                              onClick={() => handleOpenEditModal(q)}
                              className="text-slate-400 hover:text-blue-600 transition-colors mr-3" 
                              title="Edit Question"
                            >
                              <Edit className="h-4 w-4" />
                            </button>
                            <button 
                              onClick={() => handleDeleteQuestion(q)}
                              className="text-slate-400 hover:text-red-600 transition-colors" 
                              title="Delete Question"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>

      {/* Create / Edit Question Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-lg font-bold text-slate-900">
                {isEditMode ? "Edit Question" : "Create New Question"}
              </h2>
              <button 
                onClick={() => !isSubmitting && setIsModalOpen(false)} 
                className="text-slate-400 hover:text-slate-500 text-xl font-bold"
                disabled={isSubmitting}
              >
                &times;
              </button>
            </div>
            
            <div className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Question Title</label>
                <input 
                  type="text" 
                  value={formData.title}
                  onChange={(e) => setFormData(prev => ({...prev, title: e.target.value}))}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" 
                  placeholder="e.g. Reverse a Linked List" 
                  disabled={isSubmitting}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Detailed Problem Description</label>
                <textarea 
                  rows={3}
                  value={formData.content_rich_text}
                  onChange={(e) => setFormData(prev => ({...prev, content_rich_text: e.target.value}))}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" 
                  placeholder="Provide full description, constraints, and instructions..." 
                  disabled={isSubmitting}
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Type</label>
                  <select 
                    value={formData.type}
                    onChange={(e) => setFormData(prev => ({...prev, type: e.target.value}))}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white"
                    disabled={isSubmitting}
                  >
                    <option value="multiple_choice">Multiple Choice</option>
                    <option value="coding">Coding</option>
                    <option value="short_answer">Short Answer</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Difficulty</label>
                  <select 
                    value={formData.difficulty}
                    onChange={(e) => setFormData(prev => ({...prev, difficulty: e.target.value}))}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white"
                    disabled={isSubmitting}
                  >
                    <option value="EASY">Easy</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HARD">Hard</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Points</label>
                  <input 
                    type="number"
                    min={1}
                    value={formData.points}
                    onChange={(e) => setFormData(prev => ({...prev, points: Number(e.target.value)}))}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    disabled={isSubmitting}
                  />
                </div>
              </div>

              {formData.type === "multiple_choice" && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Options (comma separated)</label>
                    <input 
                      type="text"
                      value={formData.optionsStr}
                      onChange={(e) => setFormData(prev => ({...prev, optionsStr: e.target.value}))}
                      className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      placeholder="Option A, Option B, Option C, Option D"
                      disabled={isSubmitting}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Correct Answer</label>
                    <input 
                      type="text"
                      value={formData.correctAnswer}
                      onChange={(e) => setFormData(prev => ({...prev, correctAnswer: e.target.value}))}
                      className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      placeholder="e.g. Option A"
                      disabled={isSubmitting}
                    />
                  </div>
                </>
              )}

              {formData.type === "coding" && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Test Cases / Solution Metadata (JSON)</label>
                  <textarea 
                    rows={3}
                    value={formData.correctAnswer}
                    onChange={(e) => setFormData(prev => ({...prev, correctAnswer: e.target.value}))}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    placeholder='{"test_cases": [{"input": "5", "output": "120"}]}'
                    disabled={isSubmitting}
                  />
                </div>
              )}
            </div>

            <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex justify-end gap-3 mt-auto">
              <button 
                onClick={() => setIsModalOpen(false)}
                className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button 
                onClick={handleSaveQuestion}
                disabled={!formData.title.trim() || isSubmitting}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg shadow-sm transition-colors"
              >
                {isSubmitting ? "Saving..." : (isEditMode ? "Save Changes" : "Create Question")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
