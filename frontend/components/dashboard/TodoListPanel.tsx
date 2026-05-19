"use client";

import { TodoItem } from "@/lib/types";

interface TodoListPanelProps {
  todos: TodoItem[];
  onToggle: (id: number) => void;
}

// Inline SVG icons
const PlusIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19"/>
    <line x1="5" y1="12" x2="19" y2="12"/>
  </svg>
);

const CheckIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);

export default function TodoListPanel({ todos, onToggle }: TodoListPanelProps) {
  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-slate-800 font-semibold text-base">To-Do List</h3>
        <button className="w-7 h-7 flex items-center justify-center rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors">
          <PlusIcon />
        </button>
      </div>

      {/* Todo items */}
      <div className="flex flex-col gap-3">
        {todos.map((todo) => (
          <label
            key={todo.id}
            className="flex items-center gap-3 cursor-pointer group"
          >
            <div className="relative flex items-center justify-center">
              <input
                type="checkbox"
                checked={todo.completed}
                onChange={() => onToggle(todo.id)}
                className="sr-only peer"
              />
              <div
                className={`w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all
                  ${todo.completed
                    ? "bg-slate-800 border-slate-800"
                    : "border-slate-300 group-hover:border-slate-400"
                  }`}
              >
                {todo.completed && <span className="text-white"><CheckIcon /></span>}
              </div>
            </div>
            <span
              className={`text-sm transition-colors
                ${todo.completed ? "text-slate-400 line-through" : "text-slate-700"}`}
            >
              {todo.title}
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}
