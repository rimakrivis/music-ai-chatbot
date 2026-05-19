"use client";

import { useState, useRef, useEffect } from "react";
import { ChatMessage } from "@/lib/types";

interface AIChatbotProps {
  messages: ChatMessage[];
  onSendMessage: (message: string) => void;
}

// Inline SVG icon
const SendIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13"/>
    <polygon points="22 2 15 22 11 13 2 9 22 2"/>
  </svg>
);

export default function AIChatbot({ messages, onSendMessage }: AIChatbotProps) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim()) return;
    onSendMessage(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-100 flex flex-col h-[360px]">
      {/* Header */}
      <div className="p-4 border-b border-slate-100">
        <h3 className="text-slate-800 font-semibold text-base">AI Agent Chatbot</h3>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
        {/* Initial prompt suggestion */}
        <div className="flex items-start gap-2">
          <div className="w-6 h-6 bg-slate-800 rounded-lg flex items-center justify-center shrink-0">
            <span className="text-white text-xs">X</span>
          </div>
          <div className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-600 max-w-[90%]">
            Ask me about your music release... Tell me about your music release?
          </div>
        </div>

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex items-start gap-2 ${msg.role === "user" ? "justify-end" : ""}`}
          >
            {msg.role === "assistant" && (
              <div className="w-6 h-6 bg-slate-800 rounded-lg flex items-center justify-center shrink-0">
                <span className="text-white text-xs">X</span>
              </div>
            )}
            <div
              className={`rounded-xl px-3 py-2 text-sm max-w-[85%]
                ${msg.role === "user"
                  ? "bg-slate-800 text-white"
                  : "bg-slate-50 border border-slate-200 text-slate-700"
                }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-slate-100">
        <div className="relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask me anything..."
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 pr-10 text-sm text-slate-700 placeholder-slate-400 outline-none focus:border-slate-300 focus:ring-2 focus:ring-slate-100 transition-all"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 w-7 h-7 bg-slate-800 hover:bg-slate-700 disabled:bg-slate-300 rounded-lg flex items-center justify-center text-white transition-colors"
          >
            <SendIcon />
          </button>
        </div>
      </div>
    </div>
  );
}
