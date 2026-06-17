'use client';

import type { CohortAnalysis } from '@/types';

interface CohortHeatmapProps {
  cohortData: CohortAnalysis;
}

function retentionToColor(value: number): string {
  // HSL: Green (120°) at 100% → Yellow (60°) at 50% → Red (0°) at 0%
  const hue = Math.round(value * 120);
  const lightness = 90 - value * 30; // 90% at 0 → 60% at 100%
  return `hsl(${hue}, 65%, ${lightness}%)`;
}

function retentionToTextColor(value: number): string {
  return value > 0.5 ? '#1e293b' : '#374151';
}

export default function CohortHeatmap({ cohortData }: CohortHeatmapProps) {
  const { cohorts, average_retention } = cohortData;

  if (!cohorts || cohorts.length === 0) {
    return (
      <div className="text-xs text-slate-400 text-center py-4">
        No cohort data available
      </div>
    );
  }

  const maxPeriods = Math.max(...cohorts.map((c) => c.retention.length));
  const periodLabels = Array.from({ length: maxPeriods }, (_, i) =>
    i === 0 ? 'Week 0' : `W${i}`
  );

  return (
    <div className="overflow-x-auto">
      <table className="text-xs border-collapse w-full min-w-max">
        <thead>
          <tr>
            <th className="text-left py-1 pr-3 font-medium text-slate-500 whitespace-nowrap">
              Cohort
            </th>
            <th className="py-1 px-2 text-center font-medium text-slate-500">
              Size
            </th>
            {periodLabels.map((label) => (
              <th key={label} className="py-1 px-1 text-center font-medium text-slate-500 min-w-[36px]">
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {cohorts.map((cohort, rowIdx) => (
            <tr key={cohort.period}>
              <td className="py-0.5 pr-3 font-medium text-slate-600 whitespace-nowrap">
                {cohort.period}
              </td>
              <td className="py-0.5 px-2 text-center text-slate-500">
                {cohort.size.toLocaleString()}
              </td>
              {Array.from({ length: maxPeriods }, (_, colIdx) => {
                const value = cohort.retention[colIdx];
                if (value === undefined) {
                  return (
                    <td key={colIdx} className="py-0.5 px-1">
                      <div className="w-9 h-6 rounded" />
                    </td>
                  );
                }
                return (
                  <td key={colIdx} className="py-0.5 px-1">
                    <div
                      className="w-9 h-6 rounded flex items-center justify-center font-mono text-[10px] font-medium transition-all hover:opacity-80"
                      style={{
                        backgroundColor: retentionToColor(value),
                        color: retentionToTextColor(value),
                      }}
                      title={`${cohort.period} Week ${colIdx}: ${(value * 100).toFixed(1)}%`}
                    >
                      {(value * 100).toFixed(0)}%
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}

          {/* Average row */}
          {average_retention && average_retention.length > 0 && (
            <tr className="border-t border-slate-200">
              <td className="py-1 pr-3 font-semibold text-slate-700">Average</td>
              <td className="py-1 px-2 text-center text-slate-500">—</td>
              {average_retention.slice(0, maxPeriods).map((value, colIdx) => (
                <td key={colIdx} className="py-1 px-1">
                  <div
                    className="w-9 h-6 rounded flex items-center justify-center font-mono text-[10px] font-bold ring-1 ring-slate-300"
                    style={{
                      backgroundColor: retentionToColor(value),
                      color: retentionToTextColor(value),
                    }}
                  >
                    {(value * 100).toFixed(0)}%
                  </div>
                </td>
              ))}
            </tr>
          )}
        </tbody>
      </table>

      {/* Legend */}
      <div className="flex items-center gap-2 mt-3">
        <span className="text-[10px] text-slate-400">Low</span>
        <div className="flex gap-0.5">
          {[0, 0.2, 0.4, 0.6, 0.8, 1.0].map((v) => (
            <div
              key={v}
              className="w-5 h-2.5 rounded-sm"
              style={{ backgroundColor: retentionToColor(v) }}
            />
          ))}
        </div>
        <span className="text-[10px] text-slate-400">High</span>
      </div>
    </div>
  );
}
