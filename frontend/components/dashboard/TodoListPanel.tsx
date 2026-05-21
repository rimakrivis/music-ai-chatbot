"use client";

import { TodoItem } from "@/lib/types";

interface TodoListPanelProps {
  todos: TodoItem[];
  onToggle: (id: number) => void;
  onTitleClick?: (todo: TodoItem) => void;
}

const CheckIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);

const ChevronRightIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m9 18 6-6-6-6"/>
  </svg>
);

export default function TodoListPanel({ todos, onToggle, onTitleClick }: TodoListPanelProps) {
  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-slate-800 font-semibold text-base">To-Do List</h3>
        {todos.length > 0 && (
          <span className="text-xs text-slate-400">
            {todos.filter((t) => t.completed).length}/{todos.length}
          </span>
        )}
      </div>

      {/* Todo items */}
      <div className="flex flex-col gap-2">
        {todos.length === 0 && (
          <p className="text-xs text-slate-400 text-center py-3">
            No tasks yet — ask the AI for a marketing plan.
          </p>
        )}
        {todos.map((todo) => (
          <div key={todo.id} className="flex items-center gap-3 group">
            {/* Checkbox — toggles completion */}
            <button
              onClick={() => onToggle(todo.id)}
              className="shrink-0 relative flex items-center justify-center"
              aria-label={todo.completed ? "Mark incomplete" : "Mark complete"}
            >
              <div
                className={`w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all
                  ${todo.completed
                    ? "bg-slate-800 border-slate-800"
                    : "border-slate-300 group-hover:border-slate-400"
                  }`}
              >
                {todo.completed && <span className="text-white"><CheckIcon /></span>}
              </div>
            </button>

            {/* Title — clickable, opens event drawer */}
            <button
              onClick={() => onTitleClick?.(todo)}
              className={`flex-1 text-left text-sm transition-colors flex items-center justify-between gap-1 group/title
                ${todo.completed
                  ? "text-slate-400 line-through"
                  : "text-slate-700 hover:text-slate-900"
                }`}
            >
              <span>{todo.title}</span>
              {!todo.completed && onTitleClick && (
                <span className="opacity-0 group-hover/title:opacity-100 transition-opacity text-slate-400 shrink-0">
                  <ChevronRightIcon />
                </span>
              )}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
