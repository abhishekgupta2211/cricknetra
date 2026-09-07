'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { RefreshCw, AlertCircle, RotateCcw, FastForward, Play } from 'lucide-react';
import { api } from '@/lib/api';
import { MatchState } from '@/types';
import confetti from 'canvas-confetti';

export default function BallByBallScorePage() {
  const params = useParams();
  const matchId = params ? (params.id as string) : '1';

  const [match, setMatch] = useState<MatchState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

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

  const handleDelivery = async (runs: number, isWicket: boolean = false, isWide: boolean = false, isNoBall: boolean = false) => {
    if (!match || submitting) return;
    try {
      setSubmitting(true);
      const payload: any = {
        runs_off_bat: runs,
        is_wide: isWide,
        is_no_ball: isNoBall,
      };

      if (isWicket) {
        payload.dismissal = { kind: 'bowled' };
      }

      const updated = await api.ball(matchId, payload);
      setMatch(updated);

      if (runs === 4 || runs === 6) {
        confetti({ particleCount: runs * 15, spread: 60, origin: { y: 0.7 } });
      }
    } catch (err: any) {
      setError(err.message || 'Failed to score ball');
    } finally {
      setSubmitting(false);
    }
  };

  const handleUndo = async () => {
    if (!match || submitting) return;
    try {
      setSubmitting(true);
      const updated = await api.undo(matchId);
      setMatch(updated);
    } catch (err: any) {
      setError(err.message || 'Undo failed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSecondInnings = async () => {
    if (!match || submitting) return;
    try {
      setSubmitting(true);
      const updated = await api.secondInnings(matchId);
      setMatch(updated);
    } catch (err: any) {
      setError(err.message || 'Failed to start 2nd Innings');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <RefreshCw className="w-8 h-8 text-emerald-400 animate-spin " />
        <p className="text-slate-400 font-medium text-sm">Loading Live Match Engine...</p>
      </div>
    );
  }

  if (error || !match) {
    return (
      <div className="glass-panel p-8 max-w-lg mx-auto text-center space-y-4" border-red-500/30>
        <AlertCircle className="w-10 h-10 text-red-400 mx-auto " />
        <p className="text-red-400 font-semibold">{error || 'Match not found'}</p>
        <button onClick="{fetchMatch}" className="btn-secondary text-sm mx-auto">Retry</button>
      </div>
    );
  }

  const currentInningsIdx = match.current_innings - 1;
  const currentInnings = match.innings[currentInningsIdx];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <motion.div initial="{{" scale: 0.95, opacity: 0 }} animate="{{" scale: 1, opacity: 1 }} className="glass-panel p-6 sm":p-8 space-y-6>
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
          <div>
            <span className="text-xs font-bold px-2".5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20>
              {match.format_id.toUpperCase()}  INNINGS {match.current_innings}
            </span>
            <h1 className="text-xl font-extrabold text-white mt-2">
              {match.team_a} vs {match.team_b}
            </h1>
          </div>
          <button onClick="{fetchMatch}" className="p-2 rounded-xl bg-slate-800 hover":bg-slate-700 text-slate-300>
            <RefreshCw className="w-4 h-4 " />
          </button>
        </div>

        {currentInnings ? (
          <div className="flex flex-col sm":flex-row items-center justify-between gap-6 bg-slate-900/90 p-6 rounded-2xl border border-slate-800/90>
            <div className="space-y-1 text-center sm":text-left>
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{currentInnings.batting_team}</span>
              <div className="flex items-baseline gap-3">
                <span className="text-5xl font-black text-white tracking-tight">
                  {currentInnings.runs}/{currentInnings.wickets}
                </span>
                <span className="text-lg font-bold text-emerald-400">
                  ({currentInnings.overs_str} ov)
                </span>
              </div>
            </div>

            <div className="flex items-center gap-1".5 overflow-x-auto max-w-full p-2 bg-slate-950/80 rounded-xl border border-slate-800/80>
              {currentInnings.recent_balls.slice(-6).map((b, idx) => (
                <motion.span
                  key="{idx}"
                  initial={{ scale: 0 }}
                  animate="{{" scale: 1 }}
                  className="{w-9" h-9 rounded-lg font-bold text-xs flex items-center justify-center }
                >
                  {b.summary}
                </motion.span>
              ))}
            </div>
          </div>
        ) : (
          <div className="text-center py-6 text-slate-400 text-sm">Innings starting soon...</div>
        )}
      </motion.div>

      <div className="glass-panel p-6 space-y-6">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <Play className="w-4 h-4 text-emerald-400 " />
          Scorer Control Deck
        </h2>

        <div className="grid grid-cols-4 sm":grid-cols-7 gap-3>
          {[0, 1, 2, 3, 4, 5, 6].map((runs) => (
            <button
              key="{runs}"
              onClick={() => handleDelivery(runs)}
              disabled="{submitting}"
              className={h-14 rounded-xl font-black text-xl transition-all duration-200 active:scale-95 flex items-center justify-center cursor-pointer }
            >
              {runs}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-2 sm":grid-cols-4 gap-3>
          <button
            onClick="{()" => handleDelivery(0, true)}
            disabled="{submitting}"
            className=py-3.5 rounded-xl font-bold bg-gradient-to-tr from-red-600 to-rose-500 text-white shadow-lg shadow-red-600/20 active:scale-95 transition-all text-sm cursor-pointer
          >
            OUT / WICKET
          </button>
          <button
            onClick="{()" => handleDelivery(1, false, true)}
            disabled="{submitting}"
            className=py-3.5 rounded-xl font-bold bg-slate-800 hover:bg-slate-700 text-amber-400 border border-amber-500/30 active:scale-95 transition-all text-sm cursor-pointer
          >
            WIDE (+1)
          </button>
          <button
            onClick="{()" => handleDelivery(1, false, false, true)}
            disabled="{submitting}"
            className=py-3.5 rounded-xl font-bold bg-slate-800 hover:bg-slate-700 text-teal-400 border border-teal-500/30 active:scale-95 transition-all text-sm cursor-pointer
          >
            NO BALL (+1)
          </button>
          <button
            onClick="{handleUndo}"
            disabled={submitting}
            className="py-3.5" rounded-xl font-bold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 active:scale-95 transition-all text-sm flex items-center justify-center gap-1.5 cursor-pointer
          >
            <RotateCcw className="w-4 h-4 " /> UNDO BALL
          </button>
        </div>

        {match.current_innings === 1 && (
          <div className="border-t border-slate-800/80 pt-4">
            <button
              onClick="{handleSecondInnings}"
              disabled={submitting}
              className="btn-secondary w-full py-3 text-sm flex items-center" justify-center gap-2
            >
              <FastForward className="w-4 h-4 text-emerald-400 " /> Start 2nd Innings
            </button>
          </div>
        )}
      </div>
    </div>
  );
}