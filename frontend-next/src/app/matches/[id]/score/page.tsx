'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Trophy, RefreshCw, AlertCircle, Play, Sparkles, CheckCircle2, RotateCcw } from 'lucide-react';
import confetti from 'canvas-confetti';
import { api } from '@/lib/api';
import { MatchState } from '@/types';

export default function BallScoringPage() {
  const params = useParams();
  const matchId = params.id as string;
  const [match, setMatch] = useState<MatchState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Ball Input State
  const [runs, setRuns] = useState(0);
  const [isWicket, setIsWicket] = useState(false);
  const [wicketType, setWicketType] = useState('bowled');
  const [isExtra, setIsExtra] = useState(false);
  const [extraType, setExtraType] = useState('wide');
  const [submitting, setSubmitting] = useState(false);
  const [lastBallEvent, setLastBallEvent] = useState<string | null>(null);

  const fetchMatch = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.match(matchId);
      setMatch(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load match state');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMatch();
  }, [matchId]);

  const handleScoreBall = async () => {
    try {
      setSubmitting(true);

      if (runs === 4 || runs === 6) {
        confetti({
          particleCount: runs === 6 ? 100 : 50,
          spread: 70,
          origin: { y: 0.6 },
        });
      }

      const ballData = {
        runs,
        is_wicket: isWicket,
        wicket_type: isWicket ? wicketType : null,
        is_extra: isExtra,
        extra_type: isExtra ? extraType : null,
      };

      const updated = await api.scoreBall(matchId, ballData);
      setMatch(updated);
      setLastBallEvent(isWicket ? 'WICKET!' : runs === 6 ? 'SIX!' : runs === 4 ? 'FOUR!' : `${runs} Run${runs !== 1 ? 's' : ''}`);

      // Reset Ball State
      setRuns(0);
      setIsWicket(false);
      setIsExtra(false);
    } catch (err: any) {
      alert(err.message || 'Failed to submit ball score');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <RefreshCw className="w-8 h-8 text-emerald-400 animate-spin" />
        <p className="text-slate-400 font-medium text-sm">Loading Live Match Engine...</p>
      </div>
    );
  }

  if (error || !match) {
    return (
      <div className="glass-card p-8 max-w-lg mx-auto text-center space-y-4 border-red-500/30">
        <AlertCircle className="w-10 h-10 text-red-400 mx-auto" />
        <p className="text-red-400 font-semibold">{error || 'Match not found'}</p>
        <button onClick={fetchMatch} className="btn-secondary text-sm mx-auto">Retry</button>
      </div>
    );
  }

  const currentInnings = match.innings[match.innings.length - 1];

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Live Header Scoreboard */}
      <div className="glass-panel p-8 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl -z-10" />
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              {match.format_id.toUpperCase()} LIVE CONSOLE
            </span>
            <h1 className="text-3xl font-extrabold text-white mt-2">
              {match.team_a} <span className="text-slate-500">vs</span> {match.team_b}
            </h1>
          </div>
          <div className="text-right">
            <p className="text-xs font-semibold text-slate-400 uppercase">Current Score</p>
            <p className="text-4xl font-black text-emerald-400">
              {currentInnings ? `${currentInnings.runs}/${currentInnings.wickets}` : '0/0'}
            </p>
            <p className="text-xs font-medium text-slate-400 mt-1">
              Overs: {currentInnings ? currentInnings.overs : '0.0'} / {match.total_overs}
            </p>
          </div>
        </div>

        {/* Animated Last Ball Toast */}
        <AnimatePresence>
          {lastBallEvent && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="mt-4 p-3 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-center font-extrabold text-emerald-400 text-lg flex items-center justify-center gap-2"
            >
              <Sparkles className="w-5 h-5 animate-spin" />
              <span>Event Logged: {lastBallEvent}</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Ball Control Panel */}
      <div className="glass-card p-8 space-y-6">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <Play className="w-5 h-5 text-emerald-400 fill-emerald-400" />
          Ball-by-Ball Control Panel
        </h2>

        {/* Runs Selection */}
        <div className="space-y-3">
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Runs Scored</label>
          <div className="grid grid-cols-7 gap-2">
            {[0, 1, 2, 3, 4, 5, 6].map((r) => (
              <button
                key={r}
                onClick={() => setRuns(r)}
                className={`py-3 rounded-xl font-extrabold text-lg transition-all border ${
                  runs === r
                    ? 'bg-emerald-500 text-slate-950 border-emerald-400 shadow-lg shadow-emerald-500/20 scale-105'
                    : 'bg-slate-900/60 text-slate-300 border-slate-800 hover:bg-slate-800'
                }`}
              >
                {r}
              </button>
            ))}
          </div>
        </div>

        {/* Wicket & Extras Toggles */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
          {/* Wicket Toggle */}
          <div className="space-y-3 p-4 rounded-xl bg-slate-900/40 border border-slate-800">
            <div className="flex items-center justify-between">
              <label className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                <CheckCircle2 className={`w-4 h-4 ${isWicket ? 'text-red-400' : 'text-slate-600'}`} />
                Wicket / Dismissal
              </label>
              <input
                type="checkbox"
                checked={isWicket}
                onChange={(e) => setIsWicket(e.target.checked)}
                className="w-5 h-5 accent-red-500 cursor-pointer"
              />
            </div>

            {isWicket && (
              <select
                value={wicketType}
                onChange={(e) => setWicketType(e.target.value)}
                className="input-field text-sm"
              >
                <option value="bowled">Bowled</option>
                <option value="caught">Caught</option>
                <option value="lbw">LBW</option>
                <option value="run_out">Run Out</option>
                <option value="stumped">Stumped</option>
              </select>
            )}
          </div>

          {/* Extras Toggle */}
          <div className="space-y-3 p-4 rounded-xl bg-slate-900/40 border border-slate-800">
            <div className="flex items-center justify-between">
              <label className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                <CheckCircle2 className={`w-4 h-4 ${isExtra ? 'text-amber-400' : 'text-slate-600'}`} />
                Extra Delivery
              </label>
              <input
                type="checkbox"
                checked={isExtra}
                onChange={(e) => setIsExtra(e.target.checked)}
                className="w-5 h-5 accent-amber-500 cursor-pointer"
              />
            </div>

            {isExtra && (
              <select
                value={extraType}
                onChange={(e) => setExtraType(e.target.value)}
                className="input-field text-sm"
              >
                <option value="wide">Wide</option>
                <option value="no_ball">No Ball (Free Hit)</option>
                <option value="bye">Bye</option>
                <option value="leg_bye">Leg Bye</option>
              </select>
            )}
          </div>
        </div>

        {/* Submit Button */}
        <button
          onClick={handleScoreBall}
          disabled={submitting}
          className="btn-emerald w-full py-4 text-base font-bold shadow-xl shadow-emerald-500/20 mt-4"
        >
          {submitting ? 'Registering Ball...' : 'Log Ball & Update Scoreboard'}
        </button>
      </div>
    </div>
  );
}