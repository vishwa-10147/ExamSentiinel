"use client";

import React, { useState, useEffect } from 'react';
import { apiClient } from "@/services/apiClient";
import Link from "next/link";
import { Search, Filter, AlertTriangle, Clock } from "lucide-react";

// Mock data as fallback
const MOCK_REVIEWS = [
  { id: '1', candidateName: 'Alice Smith', examName: 'Midterm CS101', status: 'PENDING', date: '2023-10-27T10:00:00Z', riskScore: 85 },
  { id: '2', candidateName: 'Bob Johnson', examName: 'Final CS101', status: 'ESCALATED', date: '2023-10-28T14:30:00Z', riskScore: 92 },
  { id: '3', candidateName: 'Charlie Brown', examName: 'Midterm CS101', status: 'PENDING', date: '2023-10-29T09:15:00Z', riskScore: 45 },
];

export default function ReviewQueuePage() {
  const [reviews, setReviews] = useState(MOCK_REVIEWS);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('ALL');

  useEffect(() => {
    const fetchReviews = async () => {
      try {
        const response = await apiClient.get('/reviews');
        if (response && response.data) {
          setReviews(response.data);
        }
      } catch (error) {
        console.warn('Using mock data, failed to fetch reviews:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchReviews();
  }, []);

  const filteredReviews = reviews.filter(r => filter === 'ALL' || r.status === filter);

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Review Queue</h1>
          <p className="text-slate-500 mt-1">Manage pending and escalated exam sessions.</p>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
          <div className="flex items-center space-x-2">
            <Filter className="w-5 h-5 text-slate-400" />
            <select 
              value={filter} 
              onChange={(e) => setFilter(e.target.value)}
              className="bg-white border border-slate-300 text-slate-700 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="ALL">All Statuses</option>
              <option value="PENDING">Pending</option>
              <option value="ESCALATED">Escalated</option>
            </select>
          </div>
          <div className="relative">
            <Search className="w-5 h-5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input 
              type="text" 
              placeholder="Search candidate..." 
              className="pl-10 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-64"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-white text-slate-500 text-sm border-b border-slate-200">
                <th className="p-4 font-medium">Candidate</th>
                <th className="p-4 font-medium">Exam</th>
                <th className="p-4 font-medium">Date</th>
                <th className="p-4 font-medium">Risk Score</th>
                <th className="p-4 font-medium">Status</th>
                <th className="p-4 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-slate-500">Loading reviews...</td>
                </tr>
              ) : filteredReviews.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-slate-500">No reviews found.</td>
                </tr>
              ) : (
                filteredReviews.map((review) => (
                  <tr key={review.id} className="hover:bg-slate-50 transition-colors">
                    <td className="p-4 font-medium text-slate-900">{review.candidateName}</td>
                    <td className="p-4 text-slate-600">{review.examName}</td>
                    <td className="p-4 text-slate-500 text-sm">
                      {new Date(review.date).toLocaleDateString()} {new Date(review.date).toLocaleTimeString()}
                    </td>
                    <td className="p-4">
                      <div className="flex items-center space-x-2">
                        <div className="w-16 h-2 bg-slate-100 rounded-full overflow-hidden">
                          <div 
                            className={`h-full ${review.riskScore > 80 ? 'bg-red-500' : review.riskScore > 50 ? 'bg-amber-500' : 'bg-green-500'}`}
                            style={{ width: `${review.riskScore}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium">{review.riskScore}</span>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        review.status === 'ESCALATED' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'
                      }`}>
                        {review.status === 'ESCALATED' ? <AlertTriangle className="w-3 h-3 mr-1" /> : <Clock className="w-3 h-3 mr-1" />}
                        {review.status}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <Link href={`/admin/review/${review.id}`} className="text-blue-600 hover:text-blue-700 font-medium text-sm">
                        Review Case
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
