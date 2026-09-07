'use client';

import React, { useEffect, useState } from 'react';
import { Shield, RefreshCw, AlertCircle, UserPlus } from 'lucide-react';
import { api } from '@/lib/api';

export default function PlayersPage() {
  const [players, setPlayers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPlayers = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.players();
      setPlayers(data || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load player directory');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlayers();
  }, []);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-extrabold text-white">Players Roster</h1>
          <p className="text-slate-400 text-sm mt-1">Directory of registered players, batting & bowling styles</p>
        </div>
        <button onClick={fetchPlayers} className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300">
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
          <button onClick={fetchPlayers} className="btn-secondary text-sm mx-auto">Retry</button>
        </div>
      ) : players.length === 0 ? (
        <div className="glass-card p-10 text-center space-y-4">
          <Shield className="w-12 h-12 text-slate-600 mx-auto" />
          <h3 className="text-lg font-bold text-slate-300">No players registered</h3>
          <p className="text-slate-400 text-sm">Players will appear here as squads are populated.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {players.map((player: any) => (
            <div key={player.id} className="glass-card p-6 space-y-3 border-emerald-500/20">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-400 font-bold">
                  {player.name ? player.name[0].toUpperCase() : 'P'}
                </div>
                <div>
                  <h3 className="font-bold text-white text-lg">{player.name}</h3>
                  <p className="text-xs text-slate-400">{player.batting_style || 'Right-hand bat'}  {player.bowling_style || 'Right-arm medium'}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}