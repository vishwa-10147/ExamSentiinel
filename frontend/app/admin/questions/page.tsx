"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/apiClient";
import { Plus, Library, Trash2, Edit, AlertCircle, Type, BarChart, Upload } from "lucide-react";
import { useRef } from "react";
import toast from "react-hot-toast";

interface Question {
  id: string;
  title: string;
  difficulty: string;
  type: string;
}

export default function QuestionsPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Form states
  const [newTitle, setNewTitle] = useState("");
  const [newDifficulty, setNewDifficulty] = useState("Medium");
  const [newType, setNewType] = useState("Multiple Choice");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploadingCSV, setIsUploadingCSV] = useState(false);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setIsUploadingCSV(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/questions/bulk`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
        body: formData,
      });
      if (res.ok) {
        toast.success("Questions imported successfully!");
        const data = await apiClient.get("/api/questions");
        setQuestions(data);
      } else {
        toast.error("Failed to import CSV.");
      }
    } catch (err) {
      console.error(err);
      toast.error("Error uploading CSV.");
    } finally {
      setIsUploadingCSV(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };


  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isLoading || !user || user.role !== "admin") return;

    const fetchQuestions = async () => {
      try {
        const data = await apiClient.get<Question[]>("/api/questions");
        setQuestions(data);
      } catch (err) {
        console.error("Failed to fetch questions", err);
        setQuestions([]);
        setError("Failed to load questions. Please try again later.");
      } finally {
        setLoading(false);
      }
    };

    void fetchQuestions();
  }, [isLoading, user]);

  const handleCreateQuestion = async () => {
    if (!newTitle.trim()) return;
    
    setIsSubmitting(true);
    try {
      const createdQuestion = await apiClient.post<Question>("/api/questions", {
        title: newTitle,
        difficulty: newDifficulty,
        type: newType,
      });
      setQuestions((prev) => [...prev, createdQuestion]);
      setIsModalOpen(false);
      setNewTitle("");
      setNewDifficulty("Medium");
      setNewType("Multiple Choice");
    } catch (err) {
      console.error("Failed to create question", err);
      alert("Failed to create question. Please try again.");
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
                Manage and organize all questions for exams.
              </p>
            </div>
            
            <div className="flex items-center gap-3">
              <input type="file" accept=".csv" ref={fileInputRef} className="hidden" onChange={handleFileUpload} />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploadingCSV}
                className="inline-flex items-center gap-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                <Upload className="h-4 w-4" />
                {isUploadingCSV ? "Importing..." : "Import CSV"}
              </button>
              <button
                onClick={() => setIsModalOpen(true)}

              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 transition-colors"
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

          {/* Table Card */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Title
                    </th>
                    <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Type
                    </th>
                    <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Difficulty
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
                  ) : questions.length === 0 && !error ? (
                    <tr>
                      <td colSpan={4} className="px-6 py-12 text-center text-sm text-slate-500">
                        No questions found.
                      </td>
                    </tr>
                  ) : (
                    questions.map((q) => (
                      <tr key={q.id} className="hover:bg-slate-50/50 transition-colors">
                        <td className="px-6 py-4">
                          <div className="text-sm font-medium text-slate-900">{q.title}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center text-sm text-slate-700">
                            <Type className="h-4 w-4 mr-2 text-slate-400" />
                            {q.type}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center text-sm text-slate-700">
                            <BarChart className="h-4 w-4 mr-2 text-slate-400" />
                            <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${
                              q.difficulty === 'Easy' ? 'bg-green-50 text-green-700 ring-green-600/20' :
                              q.difficulty === 'Hard' ? 'bg-red-50 text-red-700 ring-red-600/10' :
                              'bg-yellow-50 text-yellow-800 ring-yellow-600/20'
                            }`}>
                              {q.difficulty}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <button className="text-slate-400 hover:text-blue-600 transition-colors mr-3" title="Edit">
                            <Edit className="h-4 w-4" />
                          </button>
                          <button className="text-slate-400 hover:text-red-600 transition-colors" title="Delete">
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>

      {/* Create Question Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-lg font-bold text-slate-900">Create New Question</h2>
              <button 
                onClick={() => !isSubmitting && setIsModalOpen(false)} 
                className="text-slate-400 hover:text-slate-500"
                disabled={isSubmitting}
              >
                &times;
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Title</label>
                <input 
                  type="text" 
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" 
                  placeholder="e.g. Reverse a Linked List" 
                  disabled={isSubmitting}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Type</label>
                <select 
                  value={newType}
                  onChange={(e) => setNewType(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white"
                  disabled={isSubmitting}
                >
                  <option value="Multiple Choice">Multiple Choice</option>
                  <option value="Coding">Coding</option>
                  <option value="Short Answer">Short Answer</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Difficulty</label>
                <select 
                  value={newDifficulty}
                  onChange={(e) => setNewDifficulty(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white"
                  disabled={isSubmitting}
                >
                  <option value="Easy">Easy</option>
                  <option value="Medium">Medium</option>
                  <option value="Hard">Hard</option>
                </select>
              </div>
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
                onClick={handleCreateQuestion}
                disabled={!newTitle.trim() || isSubmitting}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg shadow-sm transition-colors"
              >
                {isSubmitting ? "Creating..." : "Create"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
