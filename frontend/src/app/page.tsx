'use client';

import { useState } from 'react';
import ChatInterface from '@/components/chat/chat-interface';
import Dashboard from '@/components/dashboard/dashboard';
import InvestigationHistory from '@/components/dashboard/InvestigationHistory';
import { useChatStore } from '@/stores/chat-store';
import { MessageSquare, LayoutDashboard, History, Settings, Zap } from 'lucide-react';

type ActiveView = 'chat' | 'dashboard' | 'history';

export default function Home() {
  const [activeView, setActiveView] = useState<ActiveView>('chat');

  const navItems = [
    { id: 'chat' as ActiveView, icon: MessageSquare, label: 'Investigate' },
    { id: 'dashboard' as ActiveView, icon: LayoutDashboard, label: 'Dashboard' },
    { id: 'history' as ActiveView, icon: History, label: 'History' },
  ];

  return (
    <div className="flex h-screen bg-slate-50">
      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
        {/* Logo */}
        <div className="p-5 border-b border-slate-200">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-900 leading-tight">Analytics</p>
              <p className="text-xs text-slate-500">Copilot</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeView === item.id;
            return (
              <button
                key={item.id}
                id={`nav-${item.id}`}
                onClick={() => setActiveView(item.id)}
                className={`
                  w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
                  transition-colors duration-150
                  ${isActive
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }
                `}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Quick Questions */}
        <div className="p-3 border-t border-slate-200">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 mb-2">
            Quick Investigations
          </p>
          <QuickQuestions onSelect={() => setActiveView('chat')} />
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-slate-200 flex items-center justify-center">
              <span className="text-xs font-medium text-slate-600">PM</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-slate-700 truncate">Product Team</p>
              <p className="text-xs text-slate-400">Pro Plan</p>
            </div>
            <Settings className="w-4 h-4 text-slate-400 cursor-pointer hover:text-slate-600" />
          </div>
        </div>
      </aside>

      {/* ── Main Content ──────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-hidden">
        {activeView === 'chat' && <ChatInterface />}
        {activeView === 'dashboard' && <Dashboard />}
        {activeView === 'history' && <InvestigationHistory />}
      </main>
    </div>
  );
}

// ─── Quick Questions Component ─────────────────────────────────────────────────

const QUICK_QUESTIONS = [
  'Why did retention drop last week?',
  'Why are payment failures increasing?',
  'Which users are most likely to churn?',
  'What changed after last feature launch?',
];

function QuickQuestions({ onSelect }: { onSelect: () => void }) {
  const { sendMessage } = useChatStore();

  return (
    <div className="space-y-1">
      {QUICK_QUESTIONS.map((q) => (
        <button
          key={q}
          id={`quick-q-${q.slice(0, 20).replace(/\s+/g, '-').toLowerCase()}`}
          onClick={() => {
            sendMessage(q);
            onSelect();
          }}
          className="w-full text-left px-3 py-2 text-xs text-slate-500 hover:text-slate-700
                     hover:bg-slate-50 rounded-md transition-colors duration-150 line-clamp-2"
        >
          {q}
        </button>
      ))}
    </div>
  );
}