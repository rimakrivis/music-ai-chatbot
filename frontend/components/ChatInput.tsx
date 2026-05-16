"use client";

import { useState, useRef } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleSend() {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setText(e.target.value);
    // Auto-grow textarea up to 5 lines
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  }

  return (
    <div className="flex gap-2 items-end p-4 border-t border-zinc-800 bg-zinc-950">
      <textarea
        ref={textareaRef}
        value={text}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        rows={1}
        placeholder="Ask about this song… (Enter to send, Shift+Enter for new line)"
        className="flex-1 resize-none bg-zinc-900 border border-zinc-700 text-zinc-100
                   placeholder-zinc-500 rounded-xl px-4 py-3 text-sm focus:outline-none
                   focus:border-violet-500 transition-colors disabled:opacity-50
                   leading-relaxed min-h-[48px]"
      />
      <button
        onClick={handleSend}
        disabled={disabled || !text.trim()}
        className="shrink-0 bg-violet-600 hover:bg-violet-500 disabled:bg-zinc-800
                   disabled:text-zinc-600 disabled:cursor-not-allowed text-white
                   p-3 rounded-xl transition-colors"
        aria-label="Send message"
      >
        {disabled ? (
          <span className="inline-block w-4 h-4 border-2 border-zinc-600 border-t-violet-400 rounded-full animate-spin" />
        ) : (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        )}
      </button>
    </div>
  );
}
