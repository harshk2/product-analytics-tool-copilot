'use client';

import useSWR from 'swr';
import { getDashboard } from '@/lib/api';
import {
  TrendingUp, TrendingDown, Minus, AlertTriangle,
  BarChart2, Users, CreditCard, Activity
} from 'lucide-react';
import type { DashboardData, KPIValue } from '@/types';
import { formatDistanceToNow } from 'date-fns';

export default function Dashboard() {
  const { data, error, isLoading } = useSWR<DashboardData>(
    '/dashboard',
    getDashboard,
    { refreshInterval: 30000 } // Refresh every 30s
  );

  if (isLoading) return <DashboardSkeleton />;
  if (error) return <DashboardError error={error} />;
  if (!data) return null;

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Analytics Dashboard</h1>
          <p className="text-sm text-slate-500">
            Updated {formatDistanceToNow(new Date(data.updated_at), { addSuffix: true })}
          </p>
        </div>
      </div>

      {/* Alerts */}
      {data.alerts.length > 0 && (
        <div className="space-y-2">
          {data.alerts.map((alert, i) => (
            <div
              key={i}
              className={`flex items-center gap-3 p-3 rounded-lg border text-sm ${
                alert.severity === 'critical'
                  ? 'bg-red-50 border-red-200 text-red-800'
                  : alert.severity === 'warning'
                  ? 'bg-yellow-50 border-yellow-200 text-yellow-800'
                  : 'bg-blue-50 border-blue-200 text-blue-800'
              }`}
            >
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>{alert.message}</span>
            </div>
          ))}
        </div>
      )}

      {/* KPI Grid */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {Object.entries(data.kpis).map(([key, kpi]) => (
          <KPICard key={key} name={key} kpi={kpi as KPIValue} />
        ))}
      </div>

      {/* Recent Investigations */}
      {data.recent_investigations.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Recent Investigations</h2>
          <div className="space-y-2">
            {data.recent_investigations.map((inv) => (
              <div
                key={inv.id}
                className="bg-white border border-slate-200 rounded-lg p-4 hover:shadow-sm
                           transition-shadow duration-150"
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium text-slate-800 flex-1">{inv.question}</p>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0 ${
                      inv.status === 'completed'
                        ? 'bg-green-100 text-green-700'
                        : inv.status === 'in_progress'
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-red-100 text-red-700'
                    }`}
                  >
                    {inv.status}
                  </span>
                </div>
                {inv.summary && (
                  <p className="text-xs text-slate-500 mt-1 line-clamp-2">{inv.summary}</p>
                )}
                <p className="text-xs text-slate-400 mt-1">
                  {formatDistanceToNow(new Date(inv.started_at), { addSuffix: true })}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── KPI Card ──────────────────────────────────────────────────────────────────

const KPI_ICONS: Record<string, typeof BarChart2> = {
  dau: Users,
  mau: Users,
  mrr: CreditCard,
  retention: Activity,
  investigations_this_week: BarChart2,
};

const KPI_LABELS: Record<string, string> = {
  dau: 'Daily Active Users',
  mau: 'Monthly Active Users',
  mrr: 'Monthly Revenue',
  retention_d7: '7-Day Retention',
  investigations_this_week: 'Investigations',
  status: 'System Status',
};

function KPICard({ name, kpi }: { name: string; kpi: KPIValue }) {
  const Icon = KPI_ICONS[name] || BarChart2;
  const label = KPI_LABELS[name] || name.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());

  const TrendIcon =
    kpi.trend === 'up' ? TrendingUp : kpi.trend === 'down' ? TrendingDown : Minus;

  const trendColorClass = kpi.is_good_change
    ? kpi.trend === 'up'
      ? 'text-green-600'
      : 'text-slate-400'
    : kpi.trend === 'down'
    ? 'text-red-600'
    : 'text-slate-400';

  const formatValue = (value: number): string => {
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
    if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
    return value.toFixed(0);
  };

  return (
    <div className="kpi-card space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</p>
        <div className="w-7 h-7 rounded-lg bg-brand-50 flex items-center justify-center">
          <Icon className="w-3.5 h-3.5 text-brand-600" />
        </div>
      </div>

      <div>
        <p className="text-2xl font-bold text-slate-900">{formatValue(kpi.value)}</p>
      </div>

      <div className={`flex items-center gap-1 text-xs ${trendColorClass}`}>
        <TrendIcon className="w-3.5 h-3.5" />
        <span className="font-medium">
          {kpi.change_pct > 0 ? '+' : ''}{kpi.change_pct.toFixed(1)}%
        </span>
        <span className="text-slate-400">vs last week</span>
      </div>
    </div>
  );
}

// ─── Loading & Error States ────────────────────────────────────────────────────

function DashboardSkeleton() {
  return (
    <div className="p-6 space-y-6">
      <div className="h-8 w-48 shimmer rounded" />
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="kpi-card space-y-3">
            <div className="h-4 w-24 shimmer rounded" />
            <div className="h-8 w-16 shimmer rounded" />
            <div className="h-3 w-20 shimmer rounded" />
          </div>
        ))}
      </div>
    </div>
  );
}

function DashboardError({ error }: { error: Error }) {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center space-y-3">
        <AlertTriangle className="w-10 h-10 text-red-400 mx-auto" />
        <p className="text-slate-600 text-sm">Failed to load dashboard</p>
        <p className="text-slate-400 text-xs">{error.message}</p>
      </div>
    </div>
  );
}