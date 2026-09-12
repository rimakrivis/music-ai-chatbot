"use client";

import { useState } from "react";
import { createCalendarEventManual } from "@/lib/api";
import { EVENT_COLORS } from "@/lib/types";

interface AddToCalendarModalProps {
  open: boolean;
  onClose: () => void;
  bandId: string;
  videoId?: string | null;
  projectId?: number | null;
  onSaved: () => void; // parent calls loadFromSupabase() to refresh the Agenda
}

const EVENT_TYPES = Object.keys(EVENT_COLORS) as (keyof typeof EVENT_COLORS)[];

export default function AddToCalendarModal({
  open,
  onClose,
  bandId,
  videoId,
  projectId,
  onSaved,
}: AddToCalendarModalProps) {
  const [title, setTitle] = useState("");
  const [date, setDate] = useState("");
  const [type, setType] = useState<keyof typeof EVENT_COLORS>("general");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const resetAndClose = () => {
    setTitle("");
    setDate("");
    setType("general");
    setError(null);
    onClose();
  };

  const handleSubmit = async () => {
    if (!title.trim() || !date) {
      setError("Title and date are required.");
      return;
    }
    if (!bandId) {
      setError("Band isn't ready yet — try again in a moment.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createCalendarEventManual(bandId, { title: title.trim(), date, type }, videoId, projectId);
      onSaved();
      resetAndClose();
    } catch (err) {
      console.error("[AddToCalendarModal] Failed to save event", err);
      setError("Couldn't save — please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div onClick={resetAndClose} className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40" />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
        <div className="bg-white rounded-2xl border border-slate-100 shadow-xl w-full max-w-sm p-5 pointer-events-auto">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-slate-800 font-semibold text-base">Add to calendar</h2>
            <button type="button" onClick={resetAndClose} className="text-slate-400 hover:text-slate-600 transition-colors">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="space-y-3">
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Title</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Book venue for release show"
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700 focus:outline-none focus:border-slate-400"
              />
            </div>

            <div>
              <label className="text-xs text-slate-500 mb-1 block">Date</label>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700 focus:outline-none focus:border-slate-400"
              />
            </div>

            <div>
              <label className="text-xs text-slate-500 mb-1 block">Type</label>
              <div className="grid grid-cols-2 gap-1.5">
                {EVENT_TYPES.map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setType(t)}
                    className={`rounded-lg px-2.5 py-1.5 text-xs font-medium border transition-colors capitalize ${
                      type === t
                        ? "bg-slate-800 text-white border-slate-800"
                        : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
                    }`}
                  >
                    {EVENT_COLORS[t].label}
                  </button>
                ))}
              </div>
            </div>

            {error && <p className="text-xs text-rose-500">{error}</p>}
          </div>

          <div className="flex gap-2 mt-5">
            <button
              type="button"
              onClick={resetAndClose}
              className="flex-1 rounded-xl px-3 py-2 text-sm font-medium text-slate-500 border border-slate-200 hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={saving}
              className="flex-1 rounded-xl px-3 py-2 text-sm font-medium bg-slate-800 text-white hover:bg-slate-700 transition-colors disabled:opacity-50"
            >
              {saving ? "Saving…" : "Add event"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
