'use client';

import { useEffect, useRef, useState } from 'react';
import { Send, Loader2, Bot, RotateCcw, StopCircle } from 'lucide-react';
import { useChatStore } from '@/stores/chat-store';
import Message from './message';
import TypingIndicator from './typing-indicator';

export default function ChatInterface() {
  const { messages, isStreaming, error, sendMessage, clearMessages, dismissError } = useChatStore();
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;

    sendMessage(trimmed);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  const handleStop = () => {
    if ((window as any).__investigationCleanup) {
      (window as any).__investigationCleanup();
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="px-6 py-4 border-b border-slate-200 bg-white flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-slate-900">Analytics Copilot</h1>
            <p className="text-xs text-slate-500">
              {isStreaming ? (
                <span className="text-brand-600 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-brand-500 animate-pulse inline-block" />
                  Investigating...
                </span>
              ) : (
                'Ask a business question'
              )}
            </p>
          </div>
        </div>

        {messages.length > 0 && (
          <button
            onClick={clearMessages}
            className="text-xs text-slate-400 hover:text-slate-600 flex items-center gap-1.5
                       px-2 py-1 rounded hover:bg-slate-100 transition-colors"
          >
            <RotateCcw className="w-3 h-3" />
            Clear
          </button>
        )}
      </div>

      {/* ── Messages Area ─────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            {messages.map((message) => (
              <Message key={message.id} message={message} />
            ))}
            {isStreaming && (
              <div className="flex justify-start">
                <TypingIndicator />
              </div>
            )}
          </>
        )}

        {/* Error banner */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-center justify-between">
            <p className="text-sm text-red-700">⚠️ {error}</p>
            <button
              onClick={dismissError}
              className="text-red-400 hover:text-red-600 text-xs"
            >
              Dismiss
            </button>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Input Area ────────────────────────────────────────────────────── */}
      <div className="px-6 py-4 border-t border-slate-200 bg-white">
        <form onSubmit={handleSubmit} className="flex gap-3">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a business question... (e.g. 'Why did retention drop last week?')"
              disabled={isStreaming}
              rows={1}
              className="
                w-full resize-none rounded-xl border border-slate-200 bg-slate-50
                px-4 py-3 text-sm text-slate-900 placeholder-slate-400
                focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent
                disabled:opacity-60 disabled:cursor-not-allowed
                transition-all duration-150
                max-h-32
              "
              style={{
                minHeight: '44px',
                height: 'auto',
                overflowY: input.split('\n').length > 3 ? 'scroll' : 'hidden',
              }}
            />
          </div>

          {isStreaming ? (
            <button
              type="button"
              onClick={handleStop}
              className="
                flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium
                bg-red-100 text-red-700 hover:bg-red-200 transition-colors
              "
            >
              <StopCircle className="w-4 h-4" />
              Stop
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim() || isStreaming}
              className="
                flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium
                bg-brand-600 text-white hover:bg-brand-700
                disabled:opacity-50 disabled:cursor-not-allowed
                transition-colors duration-150
              "
            >
              <Send className="w-4 h-4" />
              Send
            </button>
          )}
        </form>

        <p className="mt-2 text-xs text-slate-400 text-center">
          Shift+Enter for new line · Enter to send
        </p>
      </div>
    </div>
  );
}

// ─── Empty State ──────────────────────────────────────────────────────────────

function EmptyState() {
  const { sendMessage } = useChatStore();

  const examples = [
    {
      icon: '📉',
      question: 'Why did retention drop last week?',
      description: 'Investigate retention changes',
    },
    {
      icon: '💳',
      question: 'Why are payment failures increasing?',
      description: 'Analyze payment failure patterns',
    },
    {
      icon: '🚨',
      question: 'Which users are most likely to churn?',
      description: 'Identify at-risk customers',
    },
    {
      icon: '🚀',
      question: 'What changed after our last feature launch?',
      description: 'Measure feature impact',
    },
  ];

  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[60vh] gap-8">
      <div className="text-center space-y-3">
        <div className="w-16 h-16 rounded-2xl bg-brand-600 flex items-center justify-center mx-auto">
          <Bot className="w-8 h-8 text-white" />
        </div>
        <h2 className="text-xl font-bold text-slate-900">Analytics Copilot</h2>
        <p className="text-slate-500 max-w-md text-sm leading-relaxed">
          I&apos;m your autonomous product analyst. Ask me any business question and I&apos;ll
          investigate it with real data — generating hypotheses, running queries,
          and identifying root causes.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 w-full max-w-2xl">
        {examples.map((ex) => (
          <button
            key={ex.question}
            onClick={() => sendMessage(ex.question)}
            className="
              text-left p-4 rounded-xl border border-slate-200 bg-white
              hover:border-brand-300 hover:bg-brand-50 hover:shadow-sm
              transition-all duration-150 space-y-1.5
            "
          >
            <p className="text-base">{ex.icon}</p>
            <p className="text-sm font-medium text-slate-800 leading-snug">{ex.question}</p>
            <p className="text-xs text-slate-400">{ex.description}</p>
          </button>
        ))}
      </div>
    </div>
  );
}