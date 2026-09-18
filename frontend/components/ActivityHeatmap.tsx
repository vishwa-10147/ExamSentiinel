import React, { useEffect, useState, useMemo } from 'react';
import { Trophy, Flame, Target } from 'lucide-react';
import { apiClient } from '@/services/apiClient';

export const ActivityHeatmap: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchActivity = async () => {
      try {
        const res = await apiClient.get('/api/users/me/activity');
        setData(res);
      } catch (err) {
        console.error("Failed to load activity", err);
      } finally {
        setLoading(false);
      }
    };
    fetchActivity();
  }, []);

  const { problemsSolved, currentStreak, maxStreak, weeks } = useMemo(() => {
    let pSolved = 0;
    let dailyCounts: Record<string, number> = {};
    
    if (data) {
      pSolved = data.problems_solved || 0;
      dailyCounts = data.daily_counts || {};
    }

    // Build the 15 week heatmap
    const wks = [];
    const today = new Date();
    // Normalize today to start of day
    today.setHours(0, 0, 0, 0);
    
    let currentStreakCount = 0;
    let maxStreakCount = 0;
    let tempStreak = 0;

    // Calculate max streak by iterating backwards from 105 days ago to today
    for (let i = 105; i >= 0; i--) {
      const d = new Date(today.getTime() - i * 86400000);
      const dateStr = d.toISOString().split('T')[0];
      if (dailyCounts[dateStr] > 0) {
        tempStreak++;
        maxStreakCount = Math.max(maxStreakCount, tempStreak);
      } else {
        tempStreak = 0;
      }
    }
    
    // Calculate current streak by iterating backwards from today
    for (let i = 0; i <= 105; i++) {
      const d = new Date(today.getTime() - i * 86400000);
      const dateStr = d.toISOString().split('T')[0];
      if (dailyCounts[dateStr] > 0) {
        currentStreakCount++;
      } else {
        if (i > 0) break; // If yesterday has no activity, streak is broken
      }
    }
    
    // Populate calendar grid (15 columns x 7 rows)
    for (let w = 0; w < 15; w++) {
      const days = [];
      for (let d = 0; d < 7; d++) {
        // Find the date for this cell (w=14, d=6 is today)
        const daysAgo = (14 - w) * 7 + (6 - d);
        const cellDate = new Date(today.getTime() - daysAgo * 86400000);
        const dateStr = cellDate.toISOString().split('T')[0];
        const count = dailyCounts[dateStr] || 0;
        
        let level = 0;
        if (count > 0) level = 1;
        if (count > 2) level = 2;
        if (count > 5) level = 3;
        if (count > 10) level = 4;
        
        days.push({ level, date: cellDate, count });
      }
      wks.push(days);
    }
    
    return {
      problemsSolved: pSolved,
      currentStreak: currentStreakCount,
      maxStreak: maxStreakCount,
      weeks: wks
    };
  }, [data]);

  const getLevelColor = (level: number) => {
    switch (level) {
      case 1: return 'bg-emerald-900/40 border-emerald-800';
      case 2: return 'bg-emerald-600/60 border-emerald-500';
      case 3: return 'bg-emerald-500 border-emerald-400';
      case 4: return 'bg-emerald-400 border-emerald-300 shadow-[0_0_8px_rgba(52,211,153,0.5)]';
      default: return 'bg-slate-800/50 border-slate-700';
    }
  };

  if (loading) return <div className="h-48 rounded-xl bg-slate-900 animate-pulse" />;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-white mb-6">Activity Graph</h3>
      
      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-slate-800/50 rounded-lg p-4 flex flex-col items-center justify-center border border-slate-700/50">
          <Target className="w-5 h-5 text-indigo-400 mb-2" />
          <div className="text-2xl font-bold text-white">{problemsSolved}</div>
          <div className="text-xs text-slate-400 mt-1 uppercase tracking-wider font-semibold">Problems Solved</div>
        </div>
        <div className="bg-slate-800/50 rounded-lg p-4 flex flex-col items-center justify-center border border-slate-700/50">
          <Flame className="w-5 h-5 text-orange-400 mb-2" />
          <div className="text-2xl font-bold text-white">{currentStreak}</div>
          <div className="text-xs text-slate-400 mt-1 uppercase tracking-wider font-semibold">Current Streak</div>
        </div>
        <div className="bg-slate-800/50 rounded-lg p-4 flex flex-col items-center justify-center border border-slate-700/50">
          <Trophy className="w-5 h-5 text-amber-400 mb-2" />
          <div className="text-2xl font-bold text-white">{maxStreak}</div>
          <div className="text-xs text-slate-400 mt-1 uppercase tracking-wider font-semibold">Max Streak</div>
        </div>
      </div>

      {/* Heatmap */}
      <div className="flex justify-center mb-2">
        <div className="flex gap-1.5 overflow-x-auto pb-2">
          {weeks.map((week, wIdx) => (
            <div key={wIdx} className="flex flex-col gap-1.5">
              {week.map((day, dIdx) => (
                <div
                  key={dIdx}
                  className={`w-3.5 h-3.5 rounded-sm border ${getLevelColor(day.level)} transition-colors duration-200 hover:border-slate-300 cursor-pointer`}
                  title={`${day.date.toDateString()}: ${day.count} submissions`}
                />
              ))}
            </div>
          ))}
        </div>
      </div>
      
      {/* Legend */}
      <div className="flex justify-end items-center gap-2 mt-4 text-xs text-slate-400">
        <span>Less</span>
        <div className="w-3 h-3 rounded-sm border bg-slate-800/50 border-slate-700" />
        <div className="w-3 h-3 rounded-sm border bg-emerald-900/40 border-emerald-800" />
        <div className="w-3 h-3 rounded-sm border bg-emerald-600/60 border-emerald-500" />
        <div className="w-3 h-3 rounded-sm border bg-emerald-500 border-emerald-400" />
        <div className="w-3 h-3 rounded-sm border bg-emerald-400 border-emerald-300" />
        <span>More</span>
      </div>
    </div>
  );
};
