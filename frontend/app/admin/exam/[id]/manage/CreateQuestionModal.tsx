"use client";

import React, { useState } from "react";
import { X, Plus, Trash2 } from "lucide-react";
import { apiClient } from "@/services/apiClient";

interface CreateQuestionModalProps {
  examId: string;
  onClose: () => void;
  onSuccess: (keepOpen?: boolean) => void;
  nextOrderIndex: number;
  initialData?: any;
}

export default function CreateQuestionModal({ examId, onClose, onSuccess, nextOrderIndex, initialData }: CreateQuestionModalProps) {
  const [type, setType] = useState(initialData?.type || "MCQ_SINGLE");
  const [title, setTitle] = useState(initialData?.title || "");
  const [points, setPoints] = useState(initialData?.points || 10);
  const [difficulty, setDifficulty] = useState(initialData?.difficulty || "MEDIUM");
  
  // MCQ states
  
  const [options, setOptions] = useState<string[]>(() => {
    if (!initialData?.options) return ["Option 1", "Option 2"];
    if (Array.isArray(initialData.options)) return initialData.options;
    if (typeof initialData.options === 'string') {
      try {
        const parsed = JSON.parse(initialData.options);
        return Array.isArray(parsed) ? parsed : [initialData.options];
      } catch(e) {
        return [initialData.options];
      }
    }
    return ["Option 1", "Option 2"];
  });
  
  const [singleCorrect, setSingleCorrect] = useState<number>(0);
  const [multiCorrect, setMultiCorrect] = useState<number[]>([]);

  
  // Essay/Short Answer state
  const [idealAnswer, setIdealAnswer] = useState(typeof initialData?.correct_answer === 'string' && !["MCQ_SINGLE", "MCQ_MULTI"].includes(initialData?.type) ? initialData.correct_answer : "");

  React.useEffect(() => {
    if (initialData) {
        let parsedOptions = options;
        
        let parsedAnswer = initialData.correct_answer;
        if (typeof parsedAnswer === 'string') {
          try {
            const temp = JSON.parse(parsedAnswer);
            parsedAnswer = temp;
          } catch(e) {}
        }

        if (initialData.type === "MCQ_SINGLE" && parsedAnswer !== undefined) {
            const idx = parsedOptions.indexOf(parsedAnswer);
            if (idx !== -1) setSingleCorrect(idx);
        } else if (initialData.type === "MCQ_MULTI" && Array.isArray(parsedAnswer)) {
            const indices = parsedAnswer.map((ans: any) => parsedOptions.indexOf(ans)).filter((i: number) => i !== -1);
            setMultiCorrect(indices);
        }
    }
  }, [initialData, options]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleAddOption = () => setOptions([...options, `Option ${options.length + 1}`]);
  const handleRemoveOption = (index: number) => {
    if (options.length <= 2) return; // Minimum 2 options
    const newOptions = options.filter((_, i) => i !== index);
    setOptions(newOptions);
    if (singleCorrect === index) setSingleCorrect(0);
    else if (singleCorrect > index) setSingleCorrect(singleCorrect - 1);
    
    setMultiCorrect(prev => prev.filter(i => i !== index).map(i => i > index ? i - 1 : i));
  };

  const handleOptionChange = (index: number, value: string) => {
    const newOptions = [...options];
    newOptions[index] = value;
    setOptions(newOptions);
  };

  const handleSubmit = async (e: React.FormEvent | React.MouseEvent, keepOpen: boolean = false) => {
    e.preventDefault();
    setError("");

    if (!title.trim()) {
      setError("Title is required.");
      return;
    }

    let finalOptions: any = {};
    let finalCorrectAnswer: any = {};

    if (type === "MCQ_SINGLE") {
      finalOptions = options.map((opt) => ({ id: opt, text: opt }));
      finalCorrectAnswer = options[singleCorrect];
    } else if (type === "MCQ_MULTI") {
      if (multiCorrect.length === 0) {
        setError("Please select at least one correct option.");
        return;
      }
      finalOptions = options.map((opt) => ({ id: opt, text: opt }));
      finalCorrectAnswer = multiCorrect.map((i) => options[i]);
    } else if (type === "CODING") {
      finalOptions = { allowed_languages: ["python", "javascript"] };
      finalCorrectAnswer = { test_cases: [] };
    } else {
      finalCorrectAnswer = idealAnswer;
    }

    setLoading(true);

    try {
      const questionPayload = {
        type,
        title,
        content_rich_text: title,
        points,
        difficulty,
        correct_answer: finalCorrectAnswer,
        options: finalOptions
      };

      
      if (initialData) {
        await apiClient.put(`/api/questions/${initialData.id || initialData.question_id}`, questionPayload);
      } else {
        const qRes = await apiClient.post("/api/questions", questionPayload) as any;
        const questionId = qRes.id;
        await apiClient.post(`/api/exams/${examId}/questions`, {
          question_id: questionId,
          order_index: nextOrderIndex
        });
      }


      if (keepOpen) {
        // Reset form for next question
        setTitle("");
        setOptions(["Option 1", "Option 2"]);
        setSingleCorrect(0);
        setMultiCorrect([]);
        setIdealAnswer("");
        setLoading(false);
      }
      
      onSuccess(keepOpen);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to create question");
      setLoading(false);
    }
  };

  const isMCQ = type === "MCQ_SINGLE" || type === "MCQ_MULTI";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-700 bg-slate-900 text-white">
          <h3 className="font-bold text-lg">{initialData ? "Edit Question" : "Add New Question"}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto space-y-5">
          {error && <div className="p-3 bg-red-50 text-red-600 rounded-lg text-sm border border-red-200">{error}</div>}
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-slate-700 dark:text-slate-200 mb-1.5">Question Type</label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              >
                <option value="MCQ_SINGLE">Single Choice (MCQ)</option>
                <option value="MCQ_MULTI">Multiple Choice (MCQ)</option>
                <option value="SHORT_ANSWER">Short Answer</option>
                <option value="ESSAY">Essay</option>
                <option value="CODING">Coding Problem</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 dark:text-slate-200 mb-1.5">Difficulty</label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              >
                <option value="EASY">Easy</option>
                <option value="MEDIUM">Medium</option>
                <option value="HARD">Hard</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 dark:text-slate-200 mb-1.5">Question Prompt</label>
            <textarea
              required
              rows={3}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              placeholder="e.g. What is the time complexity of binary search?"
            />
          </div>

          {isMCQ && (
            <div className="bg-slate-50 dark:bg-slate-900/50 p-4 rounded-xl border border-slate-200 dark:border-slate-700 space-y-3">
              <div className="flex items-center justify-between">
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-200">Options & Correct Answer</label>
                <button type="button" onClick={handleAddOption} className="text-xs font-semibold text-blue-600 flex items-center gap-1 hover:text-blue-700">
                  <Plus className="w-3 h-3" /> Add Option
                </button>
              </div>
              
              <div className="space-y-2">
                {options.map((opt, idx) => (
                  <div key={idx} className="flex items-center gap-3 bg-white dark:bg-slate-800 p-2 rounded-lg border border-slate-200 dark:border-slate-600">
                    {type === "MCQ_SINGLE" ? (
                      <input 
                        type="radio" 
                        name="correctAnswer" 
                        checked={singleCorrect === idx} 
                        onChange={() => setSingleCorrect(idx)}
                        className="w-4 h-4 text-blue-600 focus:ring-blue-500 cursor-pointer"
                      />
                    ) : (
                      <input 
                        type="checkbox" 
                        checked={multiCorrect.includes(idx)} 
                        onChange={(e) => {
                          if (e.target.checked) setMultiCorrect([...multiCorrect, idx]);
                          else setMultiCorrect(multiCorrect.filter(i => i !== idx));
                        }}
                        className="w-4 h-4 text-blue-600 focus:ring-blue-500 cursor-pointer rounded"
                      />
                    )}
                    <input
                      type="text"
                      required
                      value={opt}
                      onChange={(e) => handleOptionChange(idx, e.target.value)}
                      className="flex-1 bg-transparent text-sm focus:outline-none border-b border-transparent focus:border-blue-500 pb-0.5"
                    />
                    <button 
                      type="button" 
                      onClick={() => handleRemoveOption(idx)}
                      disabled={options.length <= 2}
                      className="p-1.5 text-slate-400 hover:text-red-500 disabled:opacity-30 disabled:hover:text-slate-400 transition"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
              {type === "MCQ_MULTI" && multiCorrect.length === 0 && (
                <p className="text-xs text-amber-600 flex items-center gap-1">Select at least one correct option.</p>
              )}
            </div>
          )}

          {(type === "SHORT_ANSWER" || type === "ESSAY") && (
            <div>
              <label className="block text-sm font-semibold text-slate-700 dark:text-slate-200 mb-1.5">Ideal Answer / Grading Rubric (Optional)</label>
              <textarea
                rows={2}
                value={idealAnswer}
                onChange={(e) => setIdealAnswer(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                placeholder="What should the grader look for in a correct response?"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-semibold text-slate-700 dark:text-slate-200 mb-1.5">Points</label>
            <input
              type="number"
              min="0.5"
              step="0.5"
              required
              value={points}
              onChange={(e) => setPoints(parseFloat(e.target.value) || 0)}
              className="w-32 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            />
          </div>

          <div className="pt-4 flex justify-end gap-3 border-t border-slate-200 dark:border-slate-700 mt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={(e) => handleSubmit(e, true)}
              disabled={loading}
              className="px-4 py-2 text-sm font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 disabled:opacity-50 transition cursor-pointer"
            >
              Save & Add Another
            </button>
            <button
              type="button"
              onClick={(e) => handleSubmit(e, false)}
              disabled={loading}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition cursor-pointer"
            >
              {loading ? "Saving..." : "Save & Close"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
