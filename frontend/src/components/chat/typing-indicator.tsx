'use client';

export default function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-4 py-2.5 bg-white border border-slate-100 rounded-2xl rounded-bl-sm shadow-sm">
      <span className="typing-dot" />
      <span className="typing-dot" />
      <span className="typing-dot" />
    </div>
  );
}