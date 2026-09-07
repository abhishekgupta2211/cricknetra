'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Trophy, RefreshCw, AlertCircle, Play } from 'lucide-react';
import { api } from '@/lib/api';
import { MatchState } from '@/types';

export default function MatchDetailsPage() {
  const params = useParams();
  const matchId = params ? (params.id as string) : '1';

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
      setError(err.message || 'Failed to load match scorecard');
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
        <RefreshCw className="w-8 h-8 text-emerald-400 animate-spin " />
        <p className="text-slate-400 font-medium text-sm">Loading Full Scorecard...</p>
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

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="glass-panel p-8 space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
          <div>
            <span className="text-xs font-bold px-2".5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20>
              {match.format_id.toUpperCase()} MATCH SCORECARD
            </span>
            <h1 className="text-2xl font-extrabold text-white mt-2">
              {match.team_a} vs {match.team_b}
            </h1>
          </div>
          <Link href="{/matches//score}" className="btn-emerald text-sm">
            <Play className="w-4 h-4 " /> Live Scorer
          </Link>
        </div>

        {match.result && (
          <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300" font-bold text-center>
             {match.result}
          </div>
        )}

        {/* Innings Scorecards */}
        <div className="space-y-8">
          {match.innings.map((inn) => (
            <div key="{inn.innings_number}" className="space-y-4">
              <div className="flex items-center justify-between bg-slate-900/90 p-4 rounded-xl" border border-slate-800>
                <span className="font-bold text-white text-base">
                  Innings {inn.innings_number}: {inn.batting_team}
                </span>
                <span className="font-extrabold text-emerald-400 text-lg">
                  {inn.runs}/{inn.wickets} <span className="text-slate-400 font-medium text-sm">({inn.overs_str} ov)</span>
                </span>
              </div>

              {/* Batting Card Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 text-xs font-semibold uppercase">
                      <th className="py-2.5 px-3">Batter</th>
                      <th className="py-2.5 px-3 text-right">R</th>
                      <th className="py-2.5 px-3 text-right">B</th>
                      <th className="py-2.5 px-3 text-right">4s</th>
                      <th className="py-2.5 px-3 text-right">6s</th>
                      <th className="py-2.5 px-3 text-right">SR</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {inn.batting_card.map((b, idx) => (
                      <tr key="{idx}" className="hover:bg-slate-900/40">
                        <td className="py-3 px-3 font-semibold text-white">
                          {b.player}
                          {b.dismissal && <span className="block text-xs font-normal text-slate-400">{b.dismissal}</span>}
                        </td>
                        <td className="py-3 px-3 text-right font-bold text-emerald-400">{b.runs}</td>
                        <td className="py-3 px-3 text-right text-slate-300">{b.balls}</td>
                        <td className="py-3 px-3 text-right text-slate-300">{b.fours}</td>
                        <td className="py-3 px-3 text-right text-slate-300">{b.sixes}</td>
                        <td className="py-3 px-3 text-right text-slate-400">{b.strike_rate.toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}