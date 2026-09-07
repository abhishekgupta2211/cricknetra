'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Trophy, Users, Shield, Award, Sliders, Home, PlusCircle, LogIn } from 'lucide-react';

export function Navigation() {
  const pathname = usePathname();

  const navItems = [
    { label: 'Home', href: '/', icon: Home },
    { label: 'Matches', href: '/matches', icon: Trophy },
    { label: 'Tournaments', href: '/tournaments', icon: Award },
    { label: 'Teams', href: '/teams', icon: Users },
    { label: 'Players', href: '/players', icon: Shield },
    { label: 'Leaderboard', href: '/leaderboards', icon: Trophy },
    { label: 'Rules', href: '/rules', icon: Sliders },
  ];

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-16 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800/80 flex items-center justify-between px-8">
      <Link href="/" className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
          <Trophy className="w-5 h-5 text-slate-950" />
        </div>
        <span className="font-extrabold text-xl tracking-tight text-white">
          CRIC<span className="text-emerald-400">NETRA</span>
        </span>
      </Link>

      <nav className="flex items-center gap-1 bg-slate-900/60 p-1.5 rounded-2xl border border-slate-800/60">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`relative px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-200 flex items-center gap-2 ${
                isActive ? 'text-emerald-400 font-bold' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span className="relative z-10 flex items-center gap-2">
                <Icon className="w-4 h-4" />
                {item.label}
              </span>
            </Link>
          );
        })}
      </nav>

      <div className="flex items-center gap-3">
        <Link href="/matches/new" className="btn-emerald text-sm py-2">
          <PlusCircle className="w-4 h-4" />
          New Match
        </Link>
        <Link href="/login" className="btn-secondary text-sm py-2">
          <LogIn className="w-4 h-4" />
          Sign In
        </Link>
      </div>
    </header>
  );
}
