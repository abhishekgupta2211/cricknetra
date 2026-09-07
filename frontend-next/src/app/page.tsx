import React from "react";
import Link from "next/link";
import { PlusCircle, Sparkles } from "lucide-react";

export default function HomePage() {
  return (
    <div className="space-y-10">
      <section className="glass-panel p-8 rounded-2xl">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-semibold mb-4">
          <Sparkles className="w-3.5 h-3.5 " /> Next-Gen Animated Scoring Platform
        </div>
        <h1 className="text-4xl font-extrabold text-white">Score Cricket Matches by <span className="text-emerald-400">Your Rules</span></h1>
        <p className="text-slate-300 mt-2">Event-sourced ball-by-ball scoring, automated DLS, custom gully rules, and live brackets.</p>
        <Link href="/matches/new" className="btn-emerald inline-flex mt-6 px-6 py-3">
          <PlusCircle className="w-5 h-5 " /> Start New Match
        </Link>
      </section>
    </div>
  );
}