/**
 * TypeScript type definitions for AI Product Analytics Copilot
 */

// ─── Intent & Investigation Types ─────────────────────────────────────────────

export type IntentType =
  | 'retention_investigation'
  | 'revenue_investigation'
  | 'payment_failure_investigation'
  | 'churn_investigation'
  | 'feature_impact_investigation'
  | 'engagement_investigation'
  | 'general_analytics';

export type AnalysisType =
  | 'cohort_retention'
  | 'segment_comparison'
  | 'funnel_analysis'
  | 'revenue_analysis'
  | 'churn_prediction'
  | 'anomaly_detection'
  | 'root_cause';

export type InvestigationStatus = 'in_progress' | 'completed' | 'failed' | 'cancelled';

export interface InvestigationPlan {
  intent_type: IntentType;
  primary_metrics: string[];
  time_range?: {
    focus?: string;
    comparison?: string;
    lookback_days?: number;
  };
  dimensions: string[];
  hypotheses: string[];
  required_analyses: AnalysisType[];
  priority: 'low' | 'medium' | 'high' | 'critical';
  reasoning?: string;
}

// ─── Cohort Analysis ──────────────────────────────────────────────────────────

export interface CohortData {
  period: string;
  size: number;
  retention: number[]; // [1.0, 0.65, 0.52, ...]
  revenue?: number[];
}

export interface CohortInsight {
  metric: string;
  value?: number;
  trend?: 'improving' | 'declining' | 'stable';
  change?: number;
  description?: string;
}

export interface CohortAnalysis {
  cohort_type: string;
  cohorts: CohortData[];
  average_retention: number[];
  insights: CohortInsight[];
}

// ─── Segmentation ─────────────────────────────────────────────────────────────

export interface Segment {
  name: string;
  definition: string;
  user_count: number;
  percentage: number;
  characteristics: Record<string, number | string | boolean>;
  risk_level?: 'low' | 'medium' | 'high' | 'critical';
}

export interface SegmentationResult {
  segments: Segment[];
  method: 'behavioral' | 'demographic' | 'value_based' | 'risk_based';
  total_users: number;
  recommendations: Array<{
    segment: string;
    action: string;
    priority: 'low' | 'medium' | 'high';
  }>;
}

// ─── Root Cause ───────────────────────────────────────────────────────────────

export interface Evidence {
  type: 'correlation' | 'timing' | 'statistical' | 'anecdotal';
  metric?: string;
  value?: string | number;
  description: string;
  confidence: number;
}

export interface Hypothesis {
  id: string;
  description: string;
  confidence: number;
  evidence: Evidence[];
  ruled_out: boolean;
  next_steps: string[];
  category?: string;
}

export interface RootCause {
  hypotheses: Hypothesis[];
  root_cause?: string; // ID of primary hypothesis
  confidence: number;
  summary?: string;
}

// ─── Visualizations ───────────────────────────────────────────────────────────

export type ChartType = 'line' | 'bar' | 'heatmap' | 'scatter' | 'funnel' | 'area' | 'donut';

export interface DataPoint {
  x: string | number;
  y: number;
  label?: string;
  metadata?: Record<string, unknown>;
}

export interface ChartVisualization {
  id: string;
  type: ChartType;
  title: string;
  data: DataPoint[] | Record<string, unknown>;
  config: {
    type: ChartType;
    title: string;
    x_axis?: string;
    y_axis?: string;
    show_legend?: boolean;
    color_scheme?: string;
    annotations?: Array<Record<string, unknown>>;
  };
  vega_spec?: Record<string, unknown>;
}

// ─── Executive Summary ────────────────────────────────────────────────────────

export interface Recommendation {
  action: string;
  impact: 'low' | 'medium' | 'high';
  effort: 'low' | 'medium' | 'high';
  urgency: 'low' | 'medium' | 'high';
  owner?: string;
  timeline?: string;
  expected_outcome?: string;
}

export interface ExecutiveSummary {
  summary: string;
  key_findings: string[];
  root_cause?: string;
  recommendations: Recommendation[];
  metrics_impact?: Record<string, unknown>;
  confidence: number;
}

// ─── Full Investigation Response ──────────────────────────────────────────────

export interface InvestigationResponse {
  id: string;
  question: string;
  status: InvestigationStatus;
  intent?: InvestigationPlan;
  metrics?: Array<{
    metric: string;
    value: number;
    period: string;
    change?: number;
    change_pct?: number;
    is_significant?: boolean;
  }>;
  cohort_analysis?: CohortAnalysis;
  segmentation?: SegmentationResult;
  root_cause?: RootCause;
  visualizations?: ChartVisualization[];
  executive_summary?: ExecutiveSummary;
  started_at: string;
  completed_at?: string;
}

// ─── Chat / Streaming ─────────────────────────────────────────────────────────

export type StreamEventType =
  | 'investigation_start'
  | 'thinking'
  | 'finding'
  | 'recommendation'
  | 'complete'
  | 'error';

export interface StreamEvent {
  type: StreamEventType;
  agent?: string;
  data?: Record<string, unknown>;
  message?: string;
  timestamp?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  streamEvents?: StreamEvent[];
  investigation?: Partial<InvestigationResponse>;
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

export interface KPIValue {
  value: number;
  change: number;
  change_pct: number;
  trend: 'up' | 'down' | 'flat';
  is_good_change: boolean;
}

export interface DashboardAlert {
  metric: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  value: number;
  threshold: number;
  detected_at: string;
}

export interface RecentInvestigation {
  id: string;
  question: string;
  status: InvestigationStatus;
  summary?: string;
  started_at: string;
  completed_at?: string;
}

export interface DashboardData {
  kpis: Record<string, KPIValue>;
  alerts: DashboardAlert[];
  recent_investigations: RecentInvestigation[];
  updated_at: string;
}

// ─── API Request Types ────────────────────────────────────────────────────────

export interface ChatRequest {
  message: string;
  session_id?: string;
  context?: {
    filters?: Record<string, unknown>;
    time_range?: {
      start?: string;
      end?: string;
      focus?: string;
      comparison?: string;
    };
    focus_segments?: string[];
  };
}

export interface QueryRequest {
  question: string;
  response_format?: 'table' | 'chart' | 'summary';
}

export interface QueryResult {
  query: string;
  results: Array<Record<string, unknown>>;
  row_count: number;
  execution_time_ms: number;
  columns: string[];
  explanation?: string;
}

export interface MemoryItem {
  id: string;
  question: string;
  summary?: string;
  root_cause?: string;
  started_at: string;
  completed_at?: string;
  similarity_score?: number;
}