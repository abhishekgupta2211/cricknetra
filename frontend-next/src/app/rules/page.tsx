'use client';

import React, { useEffect, useState } from 'react';
import { Sliders, RefreshCw, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api';

export default function RulesPage() {
  const [templates, setTemplates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTemplates = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.templates();
      setTemplates(data || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load rule templates');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-extrabold text-white">Custom Rules Engine</h1>
          <p className="text-slate-400 text-sm mt-1">Configure preset format rules, powerplays, DLS, and street rulebooks</p>
        </div>
        <button onClick={fetchTemplates} className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300">
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
          <button onClick={fetchTemplates} className="btn-secondary text-sm mx-auto">Retry</button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="glass-card p-6 space-y-3 border-emerald-500/30">
            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Preset</span>
            <h3 className="text-xl font-bold text-white">T20 Standard</h3>
            <p className="text-xs text-slate-400">20 overs per innings, max 4 overs per bowler, 6 over powerplay, free hit on no-ball.</p>
          </div>

          <div className="glass-card p-6 space-y-3 border-teal-500/30">
            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-teal-500/10 text-teal-400 border border-teal-500/20">Preset</span>
            <h3 className="text-xl font-bold text-white">T10 Blitz</h3>
            <p className="text-xs text-slate-400">10 overs per innings, max 2 overs per bowler, 3 over powerplay.</p>
          </div>

          <div className="glass-card p-6 space-y-3 border-amber-500/30">
            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">Custom Gully</span>
            <h3 className="text-xl font-bold text-white">Street / Gully Rules</h3>
            <p className="text-xs text-slate-400">Over-boundary direct hit is declared OUT, last batter standing allowed.</p>
          </div>
        </div>
      )}
    </div>
  );
}