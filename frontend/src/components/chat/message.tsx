'use client';

import { useState } from 'react';
import { Bot, User, ChevronDown, ChevronUp, CheckCircle2, Clock, AlertCircle, TrendingDown, TrendingUp, Minus } from 'lucide-react';
import type { ChatMessage, StreamEvent, ExecutiveSummary, RootCause, ChartVisualization, CohortAnalysis } from '@/types';
import ChartRenderer from '@/components/charts/ChartRenderer';
import CohortHeatmap from '@/components/charts/CohortHeatmap';

interface MessageProps {
  message: ChatMessage;
}

export default function Message({ message }: MessageProps) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="chat-message chat-message-user">
        <div className="flex items-end gap-2 max-w-[75%]">
          <div className="chat-bubble chat-bubble-user">
            <p className="whitespace-pre-wrap">{message.content}</p>
          </div>
          <div className="w-7 h-7 rounded-full bg-brand-600 flex items-center justify-center flex-shrink-0">
            <User className="w-3.5 h-3.5 text-white" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-message chat-message-assistant">
      <div className="flex items-start gap-2 max-w-[88%]">
        <div className="w-7 h-7 rounded-full bg-slate-800 flex items-center justify-center flex-shrink-0 mt-0.5">
          <Bot className="w-3.5 h-3.5 text-white" />
        </div>
        <div className="space-y-3 flex-1">
          {/* Stream events panel */}
          {message.streamEvents && message.streamEvents.length > 0 && (
            <AgentProgress events={message.streamEvents} />
          )}

          {/* Metrics panel */}
          {message.investigation?.metrics && message.investigation.metrics.length > 0 && (
            <MetricsPanel metrics={message.investigation.metrics} />
          )}

          {/* Main summary content */}
          {message.content && (
            <div className="chat-bubble chat-bubble-assistant">
              <p className="text-slate-700 whitespace-pre-wrap text-sm">{message.content}</p>
            </div>
          )}

          {/* Executive summary */}
          {message.investigation?.executive_summary && (
            <ExecutiveSummaryCard summary={message.investigation.executive_summary} />
          )}

          {/* Root cause */}
          {message.investigation?.root_cause && (
            <RootCauseCard rootCause={message.investigation.root_cause} />
          )}

          {/* Cohort heatmap */}
          {message.investigation?.cohort_analysis && (
            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide mb-3">📊 Cohort Retention Heatmap</p>
              <CohortHeatmap cohortData={message.investigation.cohort_analysis as CohortAnalysis} />
            </div>
          )}

          {/* Visualizations */}
          {message.investigation?.visualizations && message.investigation.visualizations.length > 0 && (
            <VisualizationPanel visualizations={message.investigation.visualizations as ChartVisualization[]} />
          )}

          {/* Streaming indicator */}
          {message.isStreaming && (
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Clock className="w-3 h-3 animate-spin" />
              Analyzing...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Agent Progress Panel ─────────────────────────────────────────────────────

const AGENT_LABELS: Record<string, { label: string; emoji: string }> = {
  intent: { label: 'Intent Analysis', emoji: '🎯' },
  metrics: { label: 'Metrics Analyst', emoji: '📏' },
  sql_generation: { label: 'Data Retrieval', emoji: '🔍' },
  cohort_analysis: { label: 'Cohort Analysis', emoji: '📊' },
  segmentation: { label: 'Segmentation', emoji: '👥' },
  root_cause: { label: 'Root Cause', emoji: '🔬' },
  visualization: { label: 'Visualization', emoji: '📈' },
  summary: { label: 'Summary', emoji: '📝' },
};

function AgentProgress({ events }: { events: StreamEvent[] }) {
  const [expanded, setExpanded] = useState(false);

  const thinkingEvents = events.filter((e) => e.type === 'thinking');
  const findingEvents = events.filter((e) => e.type === 'finding');
  const hasCompleted = events.some((e) => e.type === 'complete');

  // Get unique agents that have run
  const agentsDone = new Set(
    events.filter((e) => e.type === 'finding').map((e) => e.agent)
  );

  return (
    <div className="bg-white border border-slate-100 rounded-xl overflow-hidden text-xs">
      {/* Collapsed summary */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          {hasCompleted ? (
            <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
          ) : (
            <Clock className="w-3.5 h-3.5 text-brand-500 animate-spin" />
          )}
          <span className="font-medium text-slate-600">
            {hasCompleted
              ? `${agentsDone.size} agents completed`
              : `Running ${thinkingEvents[thinkingEvents.length - 1]?.message || 'analysis'}...`}
          </span>
        </div>
        {expanded ? (
          <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
        )}
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-slate-100 px-4 py-3 space-y-2">
          {findingEvents.map((event, i) => {
            const agentInfo = AGENT_LABELS[event.agent || ''] || {
              label: event.agent || 'Unknown',
              emoji: '⚙️',
            };
            return (
              <div key={i} className="flex items-start gap-2">
                <span className="text-base leading-none mt-0.5">{agentInfo.emoji}</span>
                <div>
                  <span className="font-medium text-slate-700">{agentInfo.label}</span>
                  {event.message && (
                    <span className="text-slate-400 ml-2">{event.message}</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Metrics Panel ────────────────────────────────────────────────────────────

interface MetricItem {
  metric: string;
  value: number;
  change_pct?: number;
  is_significant?: boolean;
}

function MetricsPanel({ metrics }: { metrics: MetricItem[] }) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {metrics.map((m) => {
        const change = m.change_pct || 0;
        const isUp = change > 0;
        const isDown = change < 0;
        const isSignificant = m.is_significant;

        return (
          <div
            key={m.metric}
            className={`p-3 rounded-xl border ${
              isSignificant
                ? isDown ? 'border-red-200 bg-red-50' : 'border-green-200 bg-green-50'
                : 'border-slate-100 bg-white'
            }`}
          >
            <p className="text-[10px] font-medium text-slate-500 uppercase tracking-wide truncate">
              {m.metric.replace(/_/g, ' ')}
            </p>
            <p className="text-lg font-bold text-slate-800 mt-0.5">
              {m.value >= 1 ? m.value.toLocaleString('en', { maximumFractionDigits: 1 }) : `${(m.value * 100).toFixed(1)}%`}
            </p>
            {change !== 0 && (
              <div className={`flex items-center gap-1 mt-0.5 text-[10px] font-medium ${
                isDown && isSignificant ? 'text-red-600'
                : isUp && isSignificant ? 'text-green-600'
                : 'text-slate-500'
              }`}>
                {isUp ? <TrendingUp className="w-3 h-3" /> : isDown ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
                {change > 0 ? '+' : ''}{change.toFixed(1)}% vs prior
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Visualization Panel ──────────────────────────────────────────────────────

function VisualizationPanel({ visualizations }: { visualizations: ChartVisualization[] }) {
  if (!visualizations || visualizations.length === 0) return null;

  return (
    <div className="space-y-3">
      {visualizations.slice(0, 3).map((viz) => (
        <ChartRenderer key={viz.id} visualization={viz} />
      ))}
    </div>
  );
}

// ─── Executive Summary Card ───────────────────────────────────────────────────

function ExecutiveSummaryCard({ summary }: { summary: ExecutiveSummary }) {
  const urgencyColor = {
    high: 'bg-red-100 text-red-700 border-red-200',
    medium: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    low: 'bg-green-100 text-green-700 border-green-200',
  };

  const impactIcon = {
    high: '🔴',
    medium: '🟡',
    low: '🟢',
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm">📋</span>
          <span className="text-xs font-semibold text-slate-700 uppercase tracking-wide">
            Executive Summary
          </span>
        </div>
        {summary.confidence > 0 && (
          <span className="text-xs text-slate-400">
            {Math.round(summary.confidence * 100)}% confidence
          </span>
        )}
      </div>

      <div className="p-4 space-y-4">
        {/* Summary */}
        <p className="text-sm text-slate-800 font-medium leading-relaxed">{summary.summary}</p>

        {/* Key findings */}
        {summary.key_findings?.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Key Findings
            </p>
            <ul className="space-y-1">
              {summary.key_findings.map((finding, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-slate-600">
                  <span className="text-brand-500 mt-0.5">•</span>
                  {finding}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Recommendations */}
        {summary.recommendations?.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Recommendations
            </p>
            {summary.recommendations.slice(0, 3).map((rec, i) => (
              <div
                key={i}
                className="flex items-start gap-3 p-3 rounded-lg border border-slate-100 bg-slate-50"
              >
                <span className="text-sm leading-none mt-0.5">
                  {impactIcon[rec.impact] || '⚪'}
                </span>
                <div className="flex-1 space-y-1">
                  <p className="text-xs font-medium text-slate-800">{rec.action}</p>
                  {rec.expected_outcome && (
                    <p className="text-xs text-slate-500">{rec.expected_outcome}</p>
                  )}
                  <div className="flex items-center gap-2 pt-0.5">
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded border font-medium ${urgencyColor[rec.urgency]}`}
                    >
                      {rec.urgency} urgency
                    </span>
                    <span className="text-xs text-slate-400">{rec.effort} effort</span>
                    {rec.timeline && (
                      <span className="text-xs text-slate-400">· {rec.timeline}</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Root Cause Card ──────────────────────────────────────────────────────────

function RootCauseCard({ rootCause }: { rootCause: RootCause }) {
  const [showAll, setShowAll] = useState(false);
  const primaryHypothesis = rootCause.hypotheses.find(
    (h) => h.id === rootCause.root_cause
  ) || rootCause.hypotheses[0];

  const otherHypotheses = rootCause.hypotheses.filter(
    (h) => h.id !== primaryHypothesis?.id && !h.ruled_out
  );

  const confidenceColor = (confidence: number) => {
    if (confidence >= 0.7) return 'text-red-600 bg-red-50';
    if (confidence >= 0.4) return 'text-yellow-600 bg-yellow-50';
    return 'text-green-600 bg-green-50';
  };

  if (!primaryHypothesis) return null;

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm">🔬</span>
          <span className="text-xs font-semibold text-slate-700 uppercase tracking-wide">
            Root Cause Analysis
          </span>
        </div>
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${confidenceColor(rootCause.confidence)}`}
        >
          {Math.round(rootCause.confidence * 100)}% confidence
        </span>
      </div>

      <div className="p-4 space-y-3">
        {/* Primary hypothesis */}
        <div className="p-3 rounded-lg bg-red-50 border border-red-100">
          <div className="flex items-center gap-2 mb-1">
            <AlertCircle className="w-3.5 h-3.5 text-red-500" />
            <span className="text-xs font-semibold text-red-700">Primary Cause</span>
          </div>
          <p className="text-xs text-slate-700 leading-relaxed">{primaryHypothesis.description}</p>
          {primaryHypothesis.next_steps.length > 0 && (
            <div className="mt-2 pt-2 border-t border-red-100">
              <p className="text-xs text-red-500 font-medium mb-1">Next Steps:</p>
              <ul className="space-y-0.5">
                {primaryHypothesis.next_steps.slice(0, 3).map((step, i) => (
                  <li key={i} className="text-xs text-slate-600">→ {step}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Other hypotheses */}
        {otherHypotheses.length > 0 && (
          <div>
            <button
              onClick={() => setShowAll(!showAll)}
              className="text-xs text-brand-600 hover:text-brand-700 flex items-center gap-1"
            >
              {showAll ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              {showAll ? 'Hide' : 'Show'} {otherHypotheses.length} other hypothesis
              {otherHypotheses.length !== 1 ? 'es' : ''}
            </button>

            {showAll && (
              <div className="mt-2 space-y-2">
                {otherHypotheses.map((h) => (
                  <div key={h.id} className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-slate-600">{h.description}</span>
                      <span className="text-xs text-slate-400">
                        {Math.round(h.confidence * 100)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {rootCause.summary && (
          <p className="text-xs text-slate-500 italic border-t border-slate-100 pt-2">
            {rootCause.summary}
          </p>
        )}
      </div>
    </div>
  );
}