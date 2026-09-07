'use client';

import React, { useEffect, useState } from 'react';
import { Trophy, RefreshCw, AlertCircle, Award, Target } from 'lucide-react';
import { api } from '@/lib/api';

export default function LeaderboardsPage() {
  const [leaderboard, setLeaderboard] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLeaderboards = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.leaderboard();
      setLeaderboard(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load leaderboards');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeaderboards();
  }, []);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-extrabold text-white">Player Leaderboards</h1>
          <p className="text-slate-400 text-sm mt-1">Top run-scorers, wicket-takers, and MVP ratings</p>
        </div>
        <button onClick="{fetchLeaderboards}" className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300">
          <RefreshCw className="{`w-4" h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2].map((i) => (
            <div key="{i}" className="glass-card p-6 h-64 animate-pulse bg-slate-900/40 " />
          ))}
        </div>
      ) : error ? (
        <div className="glass-card p-8 text-center space-y-4 border-red-500/30">
          <AlertCircle className="w-10 h-10 text-red-400 mx-auto " />
          <p className="text-red-400 font-semibold">{error}</p>
          <button onClick="{fetchLeaderboards}" className="btn-secondary text-sm mx-auto">Retry</button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Top Batters */}
          <div className="glass-card p-6 space-y-4">
            <div className="flex items-center gap-3 border-b border-slate-800 pb-3">
              <Award className="w-5 h-5 text-amber-400 " />
              <h2 className="text-xl font-bold text-white">Top Run Scorers</h2>
            </div>
            <div className="space-y-2">
              {(leaderboard?.top_runs || []).length === 0 ? (
                <p className="text-slate-500 text-sm py-4 text-center">No runs recorded yet</p>
              ) : (
                leaderboard?.top_runs.map((player: any, idx: number) => (
                  <div key="{idx}" className="flex items-center justify-between p-3 rounded-lg bg-slate-900/50 border border-slate-800/50">
                    <span className="font-semibold text-white">{player.name}</span>
                    <span className="font-bold text-emerald-400">{player.runs} Runs</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Top Bowlers */}
          <div className="glass-card p-6 space-y-4">
            <div className="flex items-center gap-3 border-b border-slate-800 pb-3">
              <Target className="w-5 h-5 text-emerald-400 " />
              <h2 className="text-xl font-bold text-white">Top Wicket Takers</h2>
            </div>
            <div className="space-y-2">
              {(leaderboard?.top_wickets || []).length === 0 ? (
                <p className="text-slate-500 text-sm py-4 text-center">No wickets recorded yet</p>
              ) : (
                leaderboard?.top_wickets.map((player: any, idx: number) => (
                  <div key="{idx}" className="flex items-center justify-between p-3 rounded-lg bg-slate-900/50 border border-slate-800/50">
                    <span className="font-semibold text-white">{player.name}</span>
                    <span className="font-bold text-teal-400">{player.wickets} Wkts</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}