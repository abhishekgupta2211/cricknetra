'use client';

import React, { useEffect, useState } from 'react';
import { Award, RefreshCw, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api';

export default function TournamentsPage() {
  const [tournaments, setTournaments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTournaments = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.tournaments();
      setTournaments(data || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load tournaments');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTournaments();
  }, []);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-extrabold text-white">Tournaments & Leagues</h1>
          <p className="text-slate-400 text-sm mt-1">Round-robin standings, Net Run Rate (NRR), and knockout brackets</p>
        </div>
        <button onClick={fetchTournaments} className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="glass-card p-6 h-36 animate-pulse bg-slate-900/40" />
          ))}
        </div>
      ) : error ? (
        <div className="glass-card p-8 text-center space-y-4 border-red-500/30">
          <AlertCircle className="w-10 h-10 text-red-400 mx-auto" />
          <p className="text-red-400 font-semibold">{error}</p>
          <button onClick={fetchTournaments} className="btn-secondary text-sm mx-auto">Retry</button>
        </div>
      ) : tournaments.length === 0 ? (
        <div className="glass-card p-10 text-center space-y-4">
          <Award className="w-12 h-12 text-slate-600 mx-auto" />
          <h3 className="text-lg font-bold text-slate-300">No active tournaments</h3>
          <p className="text-slate-400 text-sm">Create your first league tournament to auto-calculate NRR standings.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {tournaments.map((t: any) => (
            <div key={t.id} className="glass-card p-6 space-y-3 border-emerald-500/20">
              <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                {t.format || 'LEAGUE'}
              </span>
              <h3 className="font-bold text-white text-xl">{t.name}</h3>
              <p className="text-xs text-slate-400">{t.teams_count || 4} Teams Participating</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}