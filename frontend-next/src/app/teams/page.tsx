'use client';

import React, { useEffect, useState } from 'react';
import { Users, RefreshCw, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api';

export default function TeamsPage() {
  const [teams, setTeams] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTeams = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.teams();
      setTeams(data || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load teams directory');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTeams();
  }, []);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-extrabold text-white">Teams Directory</h1>
          <p className="text-slate-400 text-sm mt-1">Manage team rosters, captains, and head-to-head stats</p>
        </div>
        <button onClick={fetchTeams} className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300">
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
          <button onClick={fetchTeams} className="btn-secondary text-sm mx-auto">Retry</button>
        </div>
      ) : teams.length === 0 ? (
        <div className="glass-card p-10 text-center space-y-4">
          <Users className="w-12 h-12 text-slate-600 mx-auto" />
          <h3 className="text-lg font-bold text-slate-300">No teams registered</h3>
          <p className="text-slate-400 text-sm">Teams will be listed here as matches & tournaments are registered.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {teams.map((team: any) => (
            <div key={team.id} className="glass-card p-6 space-y-3 border-emerald-500/20">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400 font-bold">
                {team.name ? team.name[0].toUpperCase() : 'T'}
              </div>
              <h3 className="font-bold text-white text-lg">{team.name}</h3>
              <p className="text-xs text-slate-400">{team.squad_count || 11} Players Registered</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}