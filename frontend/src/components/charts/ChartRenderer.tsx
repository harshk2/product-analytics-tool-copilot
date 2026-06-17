'use client';

import {
  LineChart, Line, BarChart, Bar, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts';
import type { ChartVisualization, DataPoint } from '@/types';

interface ChartRendererProps {
  visualization: ChartVisualization;
  height?: number;
}

const CHART_COLORS = [
  '#6366f1', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444',
];

function toRechartsData(data: DataPoint[] | Record<string, unknown>): Array<Record<string, unknown>> {
  if (Array.isArray(data)) {
    return data.map((point) => ({
      name: String(point.x),
      value: point.y,
      label: point.label,
    }));
  }
  return [];
}

export default function ChartRenderer({ visualization, height = 240 }: ChartRendererProps) {
  const { type, title, data, config } = visualization;
  const chartData = toRechartsData(data as DataPoint[] | Record<string, unknown>);

  if (chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-slate-400 text-xs">
        No chart data available
      </div>
    );
  }

  const commonProps = {
    data: chartData,
    margin: { top: 5, right: 10, left: 0, bottom: 5 },
  };

  const renderChart = () => {
    switch (type) {
      case 'line':
        return (
          <LineChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="name" tick={{ fontSize: 10 }} stroke="#94a3b8" />
            <YAxis tick={{ fontSize: 10 }} stroke="#94a3b8" />
            <Tooltip
              contentStyle={{ fontSize: 11, borderRadius: 8, border: '1px solid #e2e8f0' }}
            />
            {config.show_legend && <Legend wrapperStyle={{ fontSize: 10 }} />}
            <Line
              type="monotone"
              dataKey="value"
              stroke={CHART_COLORS[0]}
              strokeWidth={2}
              dot={{ fill: CHART_COLORS[0], r: 3 }}
              activeDot={{ r: 5 }}
              name={config.y_axis || 'Value'}
            />
          </LineChart>
        );

      case 'bar':
        return (
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="name" tick={{ fontSize: 10 }} stroke="#94a3b8" />
            <YAxis tick={{ fontSize: 10 }} stroke="#94a3b8" />
            <Tooltip
              contentStyle={{ fontSize: 11, borderRadius: 8, border: '1px solid #e2e8f0' }}
            />
            {config.show_legend && <Legend wrapperStyle={{ fontSize: 10 }} />}
            <Bar dataKey="value" fill={CHART_COLORS[0]} radius={[3, 3, 0, 0]} name={config.y_axis || 'Value'} />
          </BarChart>
        );

      case 'area':
        return (
          <AreaChart {...commonProps}>
            <defs>
              <linearGradient id="colorGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={CHART_COLORS[0]} stopOpacity={0.2} />
                <stop offset="95%" stopColor={CHART_COLORS[0]} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="name" tick={{ fontSize: 10 }} stroke="#94a3b8" />
            <YAxis tick={{ fontSize: 10 }} stroke="#94a3b8" />
            <Tooltip
              contentStyle={{ fontSize: 11, borderRadius: 8, border: '1px solid #e2e8f0' }}
            />
            {config.show_legend && <Legend wrapperStyle={{ fontSize: 10 }} />}
            <Area
              type="monotone"
              dataKey="value"
              stroke={CHART_COLORS[0]}
              strokeWidth={2}
              fill="url(#colorGradient)"
              name={config.y_axis || 'Value'}
            />
          </AreaChart>
        );

      default:
        // Fallback to line chart
        return (
          <LineChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="name" tick={{ fontSize: 10 }} stroke="#94a3b8" />
            <YAxis tick={{ fontSize: 10 }} stroke="#94a3b8" />
            <Tooltip contentStyle={{ fontSize: 11, borderRadius: 8, border: '1px solid #e2e8f0' }} />
            <Line type="monotone" dataKey="value" stroke={CHART_COLORS[0]} strokeWidth={2} />
          </LineChart>
        );
    }
  };

  return (
    <div className="bg-white border border-slate-100 rounded-xl p-4">
      <p className="text-xs font-semibold text-slate-600 mb-3">{title}</p>
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          {renderChart()}
        </ResponsiveContainer>
      </div>
      {(config.x_axis || config.y_axis) && (
        <div className="flex justify-between mt-1">
          {config.y_axis && (
            <p className="text-[10px] text-slate-400">{config.y_axis}</p>
          )}
          {config.x_axis && (
            <p className="text-[10px] text-slate-400 ml-auto">{config.x_axis}</p>
          )}
        </div>
      )}
    </div>
  );
}
