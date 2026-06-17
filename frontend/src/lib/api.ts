/**
 * API client for communicating with the backend
 */
import axios, { AxiosInstance } from 'axios';
import type {
  ChatRequest,
  DashboardData,
  InvestigationResponse,
  QueryRequest,
  QueryResult,
  StreamEvent,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_V1 = `${API_BASE}/api/v1`;

// ─── Axios Instance ────────────────────────────────────────────────────────────

const apiClient: AxiosInstance = axios.create({
  baseURL: API_V1,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'An error occurred';
    console.error('[API Error]', message, error.response?.status);
    return Promise.reject(new Error(message));
  }
);

// ─── Chat API ──────────────────────────────────────────────────────────────────

/**
 * Start an investigation with SSE streaming
 */
export function streamInvestigation(
  request: ChatRequest,
  onEvent: (event: StreamEvent) => void,
  onError: (error: Error) => void,
  onComplete: () => void
): () => void {
  const controller = new AbortController();

  const fetchStream = async () => {
    try {
      const response = await fetch(`${API_V1}/chat/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error('No response body for streaming');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();
            if (data) {
              try {
                const event = JSON.parse(data) as StreamEvent;
                onEvent(event);

                if (event.type === 'complete' || event.type === 'error') {
                  onComplete();
                  return;
                }
              } catch (e) {
                console.warn('[SSE Parse Error]', e, data);
              }
            }
          }
        }
      }

      onComplete();
    } catch (error) {
      if ((error as Error).name !== 'AbortError') {
        onError(error as Error);
      }
    }
  };

  fetchStream();

  // Return cleanup function
  return () => controller.abort();
}

/**
 * Get a completed investigation by ID
 */
export async function getInvestigation(id: string): Promise<InvestigationResponse> {
  const response = await apiClient.get<InvestigationResponse>(`/chat/${id}`);
  return response.data;
}

// ─── Query API ─────────────────────────────────────────────────────────────────

/**
 * Execute a natural language query
 */
export async function executeQuery(request: QueryRequest): Promise<QueryResult> {
  const response = await apiClient.post<QueryResult>('/query/', request);
  return response.data;
}

// ─── Dashboard API ─────────────────────────────────────────────────────────────

/**
 * Get dashboard data
 */
export async function getDashboard(): Promise<DashboardData> {
  const response = await apiClient.get<DashboardData>('/dashboard/');
  return response.data;
}

// ─── Memory API ────────────────────────────────────────────────────────────────

/**
 * List past investigations
 */
export async function listInvestigations(params?: { limit?: number; offset?: number }) {
  const response = await apiClient.get('/memory/investigations', { params });
  return response.data;
}

/**
 * Find similar past investigations
 */
export async function findSimilar(question: string, limit = 5) {
  const response = await apiClient.get('/memory/similar', {
    params: { question, limit },
  });
  return response.data;
}

export default apiClient;