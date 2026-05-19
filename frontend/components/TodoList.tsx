"use client";

import { useState, useEffect } from "react";

interface TodoItem {
  id: number;
  title: string;
  due_date: string | null;
  status: string;
}

interface TodoListProps {
  sessionId: string;
  refreshTrigger?: number;
}

export default function TodoList({ sessionId, refreshTrigger }: TodoListProps) {
  const [items, setItems] = useState<TodoItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");

  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  async function fetchTodos() {
    try {
      const res = await fetch(`${API}/todos/${sessionId}`);
      const data = await res.json();
      setItems(data.items || []);
    } catch (e) {
      console.error("Failed to fetch todos", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchTodos(); }, [sessionId, refreshTrigger]);

  async function handleToggle(item: TodoItem) {
    const newStatus = item.status === "done" ? "pending" : "done";
    try {
      await fetch(`${API}/todos/${item.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });
      setItems((prev) => prev.map((t) => t.id === item.id ? { ...t, status: newStatus } : t));
    } catch (e) {
      console.error("Failed to toggle todo", e);
    }
  }

  async function handleEditSave(id: number) {
    try {
      await fetch(`${API}/todos/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: editTitle }),
      });
      setItems((prev) => prev.map((t) => t.id === id ? { ...t, title: editTitle } : t));
      setEditingId(null);
    } catch (e) {
      console.error("Failed to edit todo", e);
    }
  }

  async function handleDelete(id: number) {
    try {
      await fetch(`${API}/todos/${id}`, { method: "DELETE" });
      setItems((prev) => prev.filter((t) => t.id !== id));
    } catch (e) {
      console.error("Failed to delete todo", e);
    }
  }

  const done = items.filter((t) => t.status === "done").length;
  const total = items.length;
  const progress = total === 0 ? 0 : Math.round((done / total) * 100);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-slate-800 font-semibold text-sm tracking-wide">Tasks</h3>
        {total > 0 && (
          <span className="text-slate-400 text-xs">{done}/{total}</span>
        )}
      </div>

      {/* Progress bar */}
      {total > 0 && (
        <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-violet-500 to-indigo-500 rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {loading ? (
        <p className="text-slate-400 text-xs">Loading…</p>
      ) : total === 0 ? (
        <p className="text-slate-300 text-xs italic">No tasks yet. Ask for a release plan!</p>
      ) : (
        <div className="flex flex-col gap-2">
          {items.map((item) => (
            <div key={item.id} className={`bg-white border rounded-xl px-3 py-2.5 shadow-sm flex items-start gap-2.5 transition-all
              ${item.status === "done" ? "border-slate-100 opacity-60" : "border-slate-200"}`}>
              {/* Checkbox */}
              <button
                onClick={() => handleToggle(item)}
                className={`w-4 h-4 rounded-full border-2 shrink-0 mt-0.5 flex items-center justify-center transition-all
                  ${item.status === "done"
                    ? "bg-gradient-to-br from-violet-500 to-indigo-600 border-violet-500"
                    : "border-slate-300 hover:border-violet-400"
                  }`}
              >
                {item.status === "done" && (
                  <svg width="8" height="8" viewBox="0 0 10 10" fill="none">
                    <path d="M2 5l2.5 2.5L8 3" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                )}
              </button>

              {/* Title or edit input */}
              <div className="flex-1 min-w-0">
                {editingId === item.id ? (
                  <input
                    autoFocus
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onBlur={() => handleEditSave(item.id)}
                    onKeyDown={(e) => e.key === "Enter" && handleEditSave(item.id)}
                    className="w-full text-xs text-slate-700 bg-slate-50 border border-violet-300 rounded-lg px-2 py-1 outline-none"
                  />
                ) : (
                  <p className={`text-xs ${item.status === "done" ? "line-through text-slate-400" : "text-slate-700"}`}>
                    {item.title}
                  </p>
                )}
                {item.due_date && (
                  <p className="text-slate-400 text-xs mt-0.5">Due {item.due_date}</p>
                )}
              </div>

              {/* Actions */}
              <div className="flex gap-1 shrink-0">
                <button
                  onClick={() => { setEditingId(item.id); setEditTitle(item.title); }}
                  className="text-slate-300 hover:text-violet-500 transition-colors text-xs"
                >✏️</button>
                <button
                  onClick={() => handleDelete(item.id)}
                  className="text-slate-300 hover:text-rose-500 transition-colors text-sm leading-none"
                >×</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}