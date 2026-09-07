'use client';

import React, { useState } from 'react';
import { Target, PieChart, Shield, Activity } from 'lucide-react';

interface Shot {
  x: number;
  y: number;
  runs: number;
  wicket?: boolean;
}

interface PitchMark {
  x: number;
  y: number;
  runs: number;
  length?: string;
}

export function AnalyticsVisualizer({ shots = [], pitchMarks = [] }: { shots?: Shot[]; pitchMarks?: PitchMark[] }) {
  const [filter, setFilter] = useState<'all' | 'boundaries' | 'wickets'>('all');

  const filteredShots = shots.filter((s) => {
    if (filter === 'boundaries') return s.runs >= 4;
    if (filter === 'wickets') return s.wicket;
    return true;
  });

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Wagon Wheel SVG */}
      <div className="glass-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-white flex items-center gap-2">
            <PieChart className="w-5 h-5 text-emerald-400" /> Wagon Wheel
          </h3>
          <div className="flex gap-1.5">
            {(['all', 'boundaries', 'wickets'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`text-xs font-semibold px-2.5 py-1 rounded-full capitalize transition-all ${
                  filter === f ? 'bg-emerald-500 text-slate-950 font-bold' : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        <div className="relative aspect-square max-w-sm mx-auto bg-slate-900/80 rounded-full border-2 border-emerald-500/30 flex items-center justify-center p-4">
          <svg viewBox="0 0 200 200" className="w-full h-full">
            {/* Field Boundary Circle */}
            <circle cx="100" cy="100" r="95" fill="none" stroke="#10b981" strokeWidth="1.5" strokeDasharray="4 4" opacity="0.4" />
            <circle cx="100" cy="100" r="45" fill="none" stroke="#0d9488" strokeWidth="1" opacity="0.3" />
            {/* Pitch Rect */}
            <rect x="94" y="80" width="12" height="40" fill="#334155" rx="1" />

            {/* Shots trajectories */}
            {filteredShots.length === 0 ? (
              <text x="100" y="105" textAnchor="middle" fill="#64748b" fontSize="10">No shot data recorded</text>
            ) : (
              filteredShots.map((shot, idx) => (
                <line
                  key={idx}
                  x1="100"
                  y1="100"
                  x2={shot.x}
                  y2={shot.y}
                  stroke={shot.wicket ? '#ef4444' : shot.runs >= 6 ? '#f5c518' : shot.runs >= 4 ? '#22c55e' : '#3b82f6'}
                  strokeWidth={shot.runs >= 4 ? '2.5' : '1.5'}
                  opacity="0.85"
                />
              ))
            )}
          </svg>
        </div>
      </div>

      {/* Pitch Heatmap SVG */}
      <div className="glass-card p-6 space-y-4">
        <h3 className="font-bold text-white flex items-center gap-2">
          <Target className="w-5 h-5 text-teal-400" /> Pitch Map & Bowling Line
        </h3>

        <div className="relative aspect-[1/2] max-w-[200px] mx-auto bg-slate-900/80 rounded-2xl border-2 border-slate-800 flex items-center justify-center p-2">
          <svg viewBox="0 0 100 200" className="w-full h-full">
            {/* Pitch Lines */}
            <rect x="15" y="10" width="70" height="180" fill="none" stroke="#475569" strokeWidth="1.5" />
            <line x1="15" y1="35" x2="85" y2="35" stroke="#94a3b8" strokeWidth="1.5" />
            <line x1="15" y1="165" x2="85" y2="165" stroke="#94a3b8" strokeWidth="1.5" />

            {/* Pitch Marks */}
            {pitchMarks.length === 0 ? (
              <text x="50" y="100" textAnchor="middle" fill="#64748b" fontSize="8">No pitch marks</text>
            ) : (
              pitchMarks.map((mark, idx) => (
                <circle
                  key={idx}
                  cx={mark.x}
                  cy={mark.y}
                  r="4"
                  fill={mark.runs >= 4 ? '#22c55e' : '#3b82f6'}
                  opacity="0.9"
                />
              ))
            )}
          </svg>
        </div>
      </div>
    </div>
  );
}
