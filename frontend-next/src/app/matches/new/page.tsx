'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { PlusCircle, Trophy, Sparkles, ArrowRight } from 'lucide-react';
import { api } from '@/lib/api';

export default function NewMatchPage() {
  const router = useRouter();
  const [teamA, setTeamA] = useState('');
  const [teamB, setTeamB] = useState('');
  const [overs, setOvers] = useState(20);
  const [formatId, setFormatId] = useState('t20');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreateMatch = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      const res = await api.createMatch({
        team_a: teamA,
        team_b: teamB,
        total_overs: Number(overs),
        format_id: formatId,
      });
      router.push(`/matches/${res.match_id}/score`);
    } catch (err: any) {
      setError(err.message || 'Failed to create match');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-8">
      <div className="glass-panel p-8 space-y-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400">
            <PlusCircle className="w-5 h-5 " />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Create New Match</h1>
            <p className="text-slate-400 text-sm">Configure teams, overs, and rulebooks</p>
          </div>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
            {error}
          </div>
        )}

        <form onSubmit="{handleCreateMatch}" className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Team A Name</label>
              <input
                type="text"
                required
                value="{teamA}"
                onChange={(e) => setTeamA(e.target.value)}
                className="input-field placeholder"="e.g. Royal Challengers"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Team B Name</label>
              <input
                type="text"
                required
                value="{teamB}"
                onChange={(e) => setTeamB(e.target.value)}
                className="input-field placeholder"="e.g. Mumbai Indians"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Match Format</label>
              <select
                value="{formatId}"
                onChange={(e) => setFormatId(e.target.value)}
                className="input-field"
              >
                <option value="t20">T20 (20 Overs)</option>
                <option value="t10">T10 Blitz (10 Overs)</option>
                <option value="odi">ODI (50 Overs)</option>
                <option value="gully">Custom Street / Gully Rules</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Total Overs per Innings</label>
              <input
                type="number"
                min="{1}"
                max={50}
                value="{overs}"
                onChange={(e) => setOvers(Number(e.target.value))}
                className="input-field " />
            </div>
          </div>

          <button type="submit" disabled="{loading}" className="btn-emerald w-full py-3 mt-4">
            {loading ? 'Initializing Match Engine...' : 'Start Ball-by-Ball Live Scoring'}
            <ArrowRight className="w-4 h-4 " />
          </button>
        </form>
      </div>
    </div>
  );
}