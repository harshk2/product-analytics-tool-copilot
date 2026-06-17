'use client';

import { useState } from 'react';
import useSWR from 'swr';
import {
  Search, Filter, Clock, CheckCircle2, XCircle, Loader2,
  ChevronDown, ChevronUp, RefreshCw, Calendar
} from 'lucide-react';
import { formatDistanceToNow, format } from 'date-fns';
import type { InvestigationStatus } from '@/types';
import { useChatStore } from '@/stores/chat-store';

interface Investigation {
  id: string;
  question: string;
  status: InvestigationStatus;
  summary?: string;
  started_at: string;
  completed_at?: string;
  recommendations?: Array<{ action: string; impact: string }>;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const fetcher = (url: string) => fetch(url).then((r) => r.json());

function StatusBadge({ status }: { status: InvestigationStatus }) {
  const config = {
    completed: {
      icon: CheckCircle2,
      cls: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      label: 'Completed',
    },
    in_progress: {
      icon: Loader2,
      cls: 'bg-blue-50 text-blue-700 border-blue-200',
      label: 'Running',
    },
    failed: {
      icon: XCircle,
      cls: 'bg-red-50 text-red-700 border-red-200',
      label: 'Failed',
    },
    cancelled: {
      icon: XCircle,
      cls: 'bg-slate-50 text-slate-600 border-slate-200',
      label: 'Cancelled',
    },
  };

  const { icon: Icon, cls, label } = config[status] || config.failed;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${cls}`}>
      <Icon className={`w-3 h-3 ${status === 'in_progress' ? 'animate-spin' : ''}`} />
      {label}
    </span>
  );
}

function InvestigationCard({ inv }: { inv: Investigation }) {
  const [expanded, setExpanded] = useState(false);
  const { sendMessage } = useChatStore();

  const handleRerun = () => {
    sendMessage(inv.question);
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden hover:shadow-md transition-shadow duration-200">
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-800 leading-snug">{inv.question}</p>
            <div className="flex items-center gap-3 mt-2">
              <StatusBadge status={inv.status} />
              <span className="flex items-center gap-1 text-xs text-slate-400">
                <Calendar className="w-3 h-3" />
                {formatDistanceToNow(new Date(inv.started_at), { addSuffix: true })}
              </span>
              {inv.completed_at && (
                <span className="text-xs text-slate-400">
                  · {format(new Date(inv.started_at), 'MMM d, HH:mm')}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={handleRerun}
              className="text-xs text-brand-600 hover:text-brand-700 flex items-center gap-1
                         px-2 py-1 rounded-lg hover:bg-brand-50 transition-colors"
              title="Re-run this investigation"
            >
              <RefreshCw className="w-3 h-3" />
              Re-run
            </button>
            {inv.summary && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded transition-colors"
              >
                {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
            )}
          </div>
        </div>

        {/* Summary preview */}
        {inv.summary && !expanded && (
          <p className="text-xs text-slate-500 mt-2 line-clamp-2 leading-relaxed">
            {inv.summary}
          </p>
        )}
      </div>

      {/* Expanded content */}
      {expanded && inv.summary && (
        <div className="border-t border-slate-100 p-4 space-y-3 bg-slate-50">
          <div>
            <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Summary</p>
            <p className="text-xs text-slate-700 leading-relaxed">{inv.summary}</p>
          </div>

          {inv.recommendations && inv.recommendations.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide mb-2">
                Recommendations
              </p>
              <div className="space-y-1.5">
                {inv.recommendations.slice(0, 3).map((rec, i) => {
                  const impactColors: Record<string, string> = {
                    high: 'bg-red-100 text-red-700',
                    medium: 'bg-yellow-100 text-yellow-700',
                    low: 'bg-green-100 text-green-700',
                  };
                  return (
                    <div key={i} className="flex items-start gap-2">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium mt-0.5 flex-shrink-0 ${impactColors[rec.impact] || 'bg-slate-100 text-slate-600'}`}>
                        {rec.impact}
                      </span>
                      <p className="text-xs text-slate-600">{rec.action}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function HistorySkeleton() {
  return (
    <div className="space-y-3">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="bg-white border border-slate-200 rounded-xl p-4 space-y-2">
          <div className="h-4 w-3/4 shimmer rounded" />
          <div className="h-3 w-1/3 shimmer rounded" />
          <div className="h-3 w-full shimmer rounded mt-1" />
        </div>
      ))}
    </div>
  );
}

export default function InvestigationHistory() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<InvestigationStatus | 'all'>('all');

  const { data, error, isLoading, mutate } = useSWR<{ investigations: Investigation[] }>(
    `${API_URL}/api/v1/memory/?limit=50`,
    fetcher,
    { refreshInterval: 30000 }
  );

  const investigations = data?.investigations || [];

  const filtered = investigations.filter((inv) => {
    const matchesSearch = !searchQuery ||
      inv.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inv.summary?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || inv.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const statusCounts = investigations.reduce(
    (acc, inv) => {
      acc[inv.status] = (acc[inv.status] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-6 max-w-3xl mx-auto space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-900">Investigation History</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              {investigations.length} past investigation{investigations.length !== 1 ? 's' : ''}
            </p>
          </div>
          <button
            onClick={() => mutate()}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-600
                       hover:text-slate-900 border border-slate-200 rounded-lg hover:bg-slate-50
                       transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
        </div>

        {/* Stats row */}
        {investigations.length > 0 && (
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'Completed', count: statusCounts['completed'] || 0, color: 'text-emerald-600' },
              { label: 'In Progress', count: statusCounts['in_progress'] || 0, color: 'text-blue-600' },
              { label: 'Failed', count: statusCounts['failed'] || 0, color: 'text-red-600' },
            ].map(({ label, count, color }) => (
              <div key={label} className="bg-white border border-slate-200 rounded-xl p-3 text-center">
                <p className={`text-2xl font-bold ${color}`}>{count}</p>
                <p className="text-xs text-slate-500 mt-0.5">{label}</p>
              </div>
            ))}
          </div>
        )}

        {/* Search & filter */}
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search investigations..."
              className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-xl
                         focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent
                         bg-white text-slate-900 placeholder-slate-400"
            />
          </div>
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as InvestigationStatus | 'all')}
              className="pl-9 pr-8 py-2 text-sm border border-slate-200 rounded-xl
                         focus:outline-none focus:ring-2 focus:ring-brand-500
                         bg-white text-slate-700 appearance-none cursor-pointer"
            >
              <option value="all">All Status</option>
              <option value="completed">Completed</option>
              <option value="in_progress">In Progress</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>

        {/* Investigation list */}
        {isLoading ? (
          <HistorySkeleton />
        ) : error ? (
          <div className="text-center py-12 space-y-2">
            <XCircle className="w-10 h-10 text-red-300 mx-auto" />
            <p className="text-slate-600 text-sm">Failed to load history</p>
            <p className="text-slate-400 text-xs">{error.message}</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12 space-y-3">
            <Clock className="w-12 h-12 text-slate-200 mx-auto" />
            <p className="text-slate-500 text-sm">
              {searchQuery || statusFilter !== 'all'
                ? 'No investigations match your filters'
                : 'No past investigations yet'}
            </p>
            <p className="text-slate-400 text-xs">
              {!searchQuery && statusFilter === 'all' && 'Start by asking a business question in the Investigate tab'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((inv) => (
              <InvestigationCard key={inv.id} inv={inv} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
