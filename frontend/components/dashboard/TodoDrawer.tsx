"use client";

import { useEffect, useState } from "react";
import TodoListPanel from "./TodoListPanel";
import { TodoItem } from "@/lib/types";

interface TodoDrawerProps {
  open: boolean;
  onClose: () => void;
  todos: TodoItem[];
  onToggle: (id: number) => void;
  onTitleClick: (todo: TodoItem) => void; // matches TodoListPanel's existing signature exactly
}

// Deliberately does NOT reuse EventDrawer's component — it wraps the
// existing TodoListPanel (unchanged, same props) in the same slide-in
// overlay pattern EventDrawer already uses, so calendar-event clicks and
// to-do clicks each keep their own independent open/close state in
// page.tsx and can never fight over the same drawer.
export default function TodoDrawer({ open, onClose, todos, onToggle, onTitleClick }: TodoDrawerProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (open) {
      const t = setTimeout(() => setIsVisible(true), 10);
      return () => clearTimeout(t);
    }
    setIsVisible(false);
  }, [open]);

  if (!open) return null;

  return (
    <>
      <div
        onClick={onClose}
        className={`fixed inset-0 bg-black/20 backdrop-blur-sm z-40 transition-opacity duration-300 ${
          isVisible ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
      />
      <div
        className={`fixed top-0 right-0 h-full z-50 flex transition-transform duration-300 ease-out
          ${isVisible ? "translate-x-0" : "translate-x-full"}
          w-full max-w-md`}
      >
        <div className="w-full flex flex-col bg-white border-l border-slate-200 overflow-y-auto">
          <div className="px-4 py-4 border-b border-slate-100 shrink-0 flex items-center justify-between">
            <h2 className="text-slate-800 font-semibold text-base">To-do list</h2>
            <button
              type="button"
              onClick={onClose}
              className="text-slate-400 hover:text-slate-600 transition-colors"
              title="Close"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="p-4">
            <TodoListPanel todos={todos} onToggle={onToggle} onTitleClick={onTitleClick} />
          </div>
        </div>
      </div>
    </>
  );
}
