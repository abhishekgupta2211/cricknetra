'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Trophy, RefreshCw, AlertCircle, Play, ArrowLeft, Activity } from 'lucide-react';
import { api } from '@/lib/api';
import { MatchState } from '@/types';

export default function MatchDetailPage() {
  const params = useParams();
  const matchId = params.id as string;
  const [match, setMatch] = useState<MatchState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMatch = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.match(matchId);
      setMatch(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load match details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMatch();
  }, [matchId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <RefreshCw className="w-8 h-8 text-emerald-400 animate-spin" />
        <p className="text-slate-400 font-medium text-sm">Loading Full Scorecard...</p>
      </div>
    );
  }

  if (error || !match) {
    return (
      <div className="glass-card p-8 text-center space-y-4 border-red-500/30 max-w-md mx-auto my-12">
        <AlertCircle className="w-10 h-10 text-red-400 mx-auto" />
        <p className="text-red-400 font-semibold">{error || 'Match not found'}</p>
        <Link href="/" className="btn-secondary text-sm mx-auto inline-flex">
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="glass-panel p-8 space-y-6">
        <div className="flex items-center justify-between">
          <Link href="/" className="text-slate-400 hover:text-white flex items-center gap-2 text-sm font-semibold">
            <ArrowLeft className="w-4 h-4" /> Back
          </Link>
          <span className="text-xs font-bold px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            {match.format_id.toUpperCase()}  {match.total_overs} OVERS
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center text-center">
          <div className="space-y-1">
            <h2 className="text-2xl font-black text-white">{match.team_a}</h2>
            <p className="text-3xl font-extrabold text-emerald-400">
              {match.innings[0] ? `${match.innings[0].runs}/${match.innings[0].wickets}` : '0/0'}
            </p>
            <p className="text-xs text-slate-400">({match.innings[0] ? match.innings[0].overs : '0.0'} Overs)</p>
          </div>

          <div className="space-y-2">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">VS</span>
            {match.status === 'in_progress' ? (
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 text-amber-400 text-xs font-bold border border-amber-500/20">
                <Activity className="w-3.5 h-3.5 animate-pulse" /> LIVE IN PROGRESS
              </div>
            ) : (
              <p className="text-xs font-semibold text-slate-300">Match Ended</p>
            )}
            <div className="pt-2">
              <Link href="{`/matches/${match.id}/score`}" className="btn-emerald text-xs py-2 inline-flex">
                <Play className="w-3.5 h-3.5" /> Open Scoring Console
              </Link>
            </div>
          </div>

          <div className="space-y-1">
            <h2 className="text-2xl font-black text-white">{match.team_b}</h2>
            <p className="text-3xl font-extrabold text-emerald-400">
              {match.innings[1] ? `${match.innings[1].runs}/${match.innings[1].wickets}` : 'Yet to Bat'}
            </p>
            <p className="text-xs text-slate-400">({match.innings[1] ? match.innings[1].overs : '0.0'} Overs)</p>
          </div>
        </div>

        {match.result && (
          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-center text-sm font-bold text-emerald-400">
             {match.result}
          </div>
        )}
      </div>

      {/* Detailed Innings Breakdown */}
      <div className="space-y-6">
        <h3 className="text-xl font-bold text-white">Full Match Scorecard</h3>
        {match.innings.map((inn, idx) => (
          <div key="{idx}" className="glass-card p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h4 className="font-bold text-lg text-white">Innings {idx + 1}: {idx === 0 ? match.team_a : match.team_b}</h4>
              <span className="text-emerald-400 font-extrabold">{inn.runs}/{inn.wickets} ({inn.overs} Overs)</span>
            </div>
            <p className="text-sm text-slate-400">Extras: {inn.extras} | Run Rate: {(inn.runs / (inn.overs || 1)).toFixed(2)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}