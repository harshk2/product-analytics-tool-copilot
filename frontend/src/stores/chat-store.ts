/**
 * Zustand store for chat state management
 */
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { v4 as uuidv4 } from 'uuid';
import type {
  ChatMessage,
  InvestigationResponse,
  StreamEvent,
} from '@/types';
import { streamInvestigation } from '@/lib/api';

interface ChatStore {
  // State
  messages: ChatMessage[];
  sessionId: string;
  isStreaming: boolean;
  currentInvestigationId: string | null;
  error: string | null;

  // Actions
  sendMessage: (content: string) => void;
  clearMessages: () => void;
  resetSession: () => void;
  dismissError: () => void;
}

export const useChatStore = create<ChatStore>()(
  devtools(
    persist(
      (set, get) => ({
        messages: [],
        sessionId: uuidv4(),
        isStreaming: false,
        currentInvestigationId: null,
        error: null,

        sendMessage: (content: string) => {
          const { sessionId, messages } = get();

          // Add user message
          const userMessage: ChatMessage = {
            id: uuidv4(),
            role: 'user',
            content,
            timestamp: new Date(),
          };

          // Add placeholder assistant message
          const assistantMessageId = uuidv4();
          const assistantMessage: ChatMessage = {
            id: assistantMessageId,
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            isStreaming: true,
            streamEvents: [],
            investigation: {},
          };

          set({
            messages: [...messages, userMessage, assistantMessage],
            isStreaming: true,
            error: null,
          });

          // Stream events from the API
          const cleanup = streamInvestigation(
            {
              message: content,
              session_id: sessionId,
            },
            // onEvent
            (event: StreamEvent) => {
              set((state) => {
                const updatedMessages = state.messages.map((msg) => {
                  if (msg.id !== assistantMessageId) return msg;

                  const updatedEvents = [...(msg.streamEvents || []), event];
                  const investigation = buildInvestigationFromEvents(updatedEvents);

                  // Build content from events
                  const content = buildContentFromEvent(event, msg.content);

                  return {
                    ...msg,
                    content,
                    streamEvents: updatedEvents,
                    investigation,
                  };
                });

                return { messages: updatedMessages };
              });
            },
            // onError
            (error: Error) => {
              set((state) => ({
                isStreaming: false,
                error: error.message,
                messages: state.messages.map((msg) =>
                  msg.id === assistantMessageId
                    ? {
                        ...msg,
                        isStreaming: false,
                        content: `❌ Investigation failed: ${error.message}`,
                      }
                    : msg
                ),
              }));
            },
            // onComplete
            () => {
              set((state) => ({
                isStreaming: false,
                messages: state.messages.map((msg) =>
                  msg.id === assistantMessageId
                    ? { ...msg, isStreaming: false }
                    : msg
                ),
              }));
            }
          );

          // Store cleanup function (not in state to avoid serialization issues)
          (window as any).__investigationCleanup = cleanup;
        },

        clearMessages: () => set({ messages: [] }),

        resetSession: () =>
          set({
            messages: [],
            sessionId: uuidv4(),
            isStreaming: false,
            currentInvestigationId: null,
            error: null,
          }),

        dismissError: () => set({ error: null }),
      }),
      {
        name: 'chat-store',
        partialize: (state) => ({
          messages: state.messages.slice(-50), // Keep last 50 messages
          sessionId: state.sessionId,
        }),
      }
    )
  )
);

// ─── Helper Functions ─────────────────────────────────────────────────────────

function buildContentFromEvent(event: StreamEvent, currentContent: string): string {
  switch (event.type) {
    case 'thinking':
      return currentContent || `🔍 ${event.message || 'Analyzing...'}`;

    case 'finding': {
      const findingType = event.data?.type as string;
      if (findingType === 'intent') return currentContent;
      if (findingType === 'executive_summary') {
        const summary = event.data?.summary as string;
        return summary || currentContent;
      }
      return currentContent || `📊 ${event.message || 'Processing...'}`;
    }

    case 'complete':
      return currentContent;

    case 'error':
      return `❌ ${event.message || 'An error occurred'}`;

    default:
      return currentContent;
  }
}

function buildInvestigationFromEvents(
  events: StreamEvent[]
): Partial<InvestigationResponse> {
  const investigation: Partial<InvestigationResponse> = {};

  for (const event of events) {
    if (event.type !== 'finding') continue;

    const data = event.data;
    if (!data) continue;
    const findingType = data.type as string;

    switch (findingType) {
      case 'intent':
        investigation.intent = {
          intent_type: data.intent_type as any,
          primary_metrics: (data.metrics as string[]) || [],
          hypotheses: (data.hypotheses as string[]) || [],
          dimensions: [],
          required_analyses: [],
          priority: 'medium',
        };
        break;

      case 'cohort_analysis':
        investigation.cohort_analysis = data.insights as any;
        break;

      case 'root_cause':
        investigation.root_cause = {
          hypotheses: [],
          root_cause: undefined,
          confidence: (data.confidence as number) || 0,
          summary: data.summary as string,
        };
        break;

      case 'executive_summary':
        investigation.executive_summary = {
          summary: data.summary as string,
          key_findings: [],
          recommendations: [],
          confidence: 0,
        };
        break;

      case 'visualizations':
        investigation.visualizations = (data.charts as any[]) || [];
        break;
    }
  }

  return investigation;
}