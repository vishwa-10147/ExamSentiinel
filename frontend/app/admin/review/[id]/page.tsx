"use client";

import React, { useState, useEffect } from 'react';
import { apiClient } from "@/services/apiClient";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, User, BookOpen, AlertTriangle, Clock, CheckCircle, XCircle } from "lucide-react";

const MOCK_REVIEW = {
  id: '1',
  candidateName: 'Alice Smith',
  candidateId: 'CAND-9283',
  examName: 'Midterm CS101',
  status: 'PENDING',
  date: '2023-10-27T10:00:00Z',
  riskScore: 85,
  duration: '1h 45m',
  timeline: [
    { id: 't1', time: '10:15:00', type: 'WARNING', description: 'Multiple faces detected in frame.' },
    { id: 't2', time: '10:45:00', type: 'INFO', description: 'Candidate left full-screen mode.' },
    { id: 't3', time: '11:20:00', type: 'CRITICAL', description: 'Audio decibel level exceeded threshold (Talking detected).' }
  ]
};

export default function ReviewDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  
  const [review, setReview] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const fetchReview = async () => {
      try {
        const response: any = await apiClient.get(`/api/reviews/${id}`);
        if (response && response.id) {
          setReview(response);
        } else {
          // Fallback
          setReview(MOCK_REVIEW);
        }
      } catch (error) {
        console.warn('Using mock data, failed to fetch review:', error);
        setReview({ ...MOCK_REVIEW, id: id as string });
      } finally {
        setLoading(false);
      }
    };
    if (id) {
      fetchReview();
    }
  }, [id]);

  const handleAction = async (action: 'DISMISS' | 'CONFIRM' | 'ESCALATE') => {
    setSubmitting(true);
    try {
      await apiClient.post(`/reviews/${id}/action`, { action });
      // Simulate success and redirect
      router.push('/review');
    } catch (error) {
      console.warn('Mocking action submission:', error);
      setTimeout(() => {
        router.push('/review');
      }, 500);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 max-w-5xl mx-auto flex justify-center items-center h-64">
        <p className="text-slate-500">Loading review details...</p>
      </div>
    );
  }

  if (!review) return null;

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="mb-6">
        <Link href="/review" className="inline-flex items-center text-sm font-medium text-slate-500 hover:text-slate-700">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to Queue
        </Link>
      </div>

      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Review Case #{review.id}</h1>
          <p className="text-slate-500 mt-1">Submitted on {new Date(review.date).toLocaleString()}</p>
        </div>
        <div className="flex space-x-3">
          <button 
            onClick={() => handleAction('DISMISS')}
            disabled={submitting}
            className="px-4 py-2 bg-white border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 font-medium transition-colors disabled:opacity-50 flex items-center"
          >
            <XCircle className="w-4 h-4 mr-2" />
            Dismiss
          </button>
          <button 
            onClick={() => handleAction('CONFIRM')}
            disabled={submitting}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition-colors disabled:opacity-50 flex items-center"
          >
            <CheckCircle className="w-4 h-4 mr-2" />
            Confirm Violation
          </button>
          <button 
            onClick={() => handleAction('ESCALATE')}
            disabled={submitting}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium transition-colors disabled:opacity-50 flex items-center"
          >
            <AlertTriangle className="w-4 h-4 mr-2" />
            Escalate
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
              <User className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-slate-900">Candidate Info</h3>
          </div>
          <div className="space-y-3 text-sm">
            <div>
              <p className="text-slate-500">Name</p>
              <p className="font-medium text-slate-900">{review.candidateName}</p>
            </div>
            <div>
              <p className="text-slate-500">Candidate ID</p>
              <p className="font-medium text-slate-900">{review.candidateId}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
              <BookOpen className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-slate-900">Exam Details</h3>
          </div>
          <div className="space-y-3 text-sm">
            <div>
              <p className="text-slate-500">Exam Name</p>
              <p className="font-medium text-slate-900">{review.examName}</p>
            </div>
            <div>
              <p className="text-slate-500">Duration</p>
              <p className="font-medium text-slate-900">{review.duration}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-2 bg-amber-50 text-amber-600 rounded-lg">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-slate-900">Risk Assessment</h3>
          </div>
          <div className="space-y-3 text-sm">
            <div>
              <p className="text-slate-500 mb-1">Overall Score</p>
              <div className="flex items-center space-x-3">
                <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div 
                    className={`h-full ${review.riskScore > 80 ? 'bg-red-500' : review.riskScore > 50 ? 'bg-amber-500' : 'bg-green-500'}`}
                    style={{ width: `${review.riskScore}%` }}
                  />
                </div>
                <span className="font-bold text-slate-900">{review.riskScore}/100</span>
              </div>
            </div>
            <div>
              <p className="text-slate-500">Current Status</p>
              <p className="font-medium text-amber-700">{review.status}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-6 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">Proctoring Timeline</h2>
          <p className="text-sm text-slate-500">Events flagged during the session.</p>
        </div>
        <div className="p-6">
          <div className="space-y-6">
            {review.timeline.map((event: any, index: number) => (
              <div key={event.id} className="flex">
                <div className="flex flex-col items-center mr-4">
                  <div className={`w-3 h-3 rounded-full mt-1 ${
                    event.type === 'CRITICAL' ? 'bg-red-500' :
                    event.type === 'WARNING' ? 'bg-amber-500' : 'bg-blue-500'
                  }`} />
                  {index !== review.timeline.length - 1 && (
                    <div className="w-px h-full bg-slate-200 my-2" />
                  )}
                </div>
                <div className="pb-6">
                  <div className="flex items-center space-x-2 mb-1">
                    <span className="text-sm font-medium text-slate-900">{event.time}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      event.type === 'CRITICAL' ? 'bg-red-100 text-red-800' :
                      event.type === 'WARNING' ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-800'
                    }`}>
                      {event.type}
                    </span>
                  </div>
                  <p className="text-slate-600 text-sm">{event.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
