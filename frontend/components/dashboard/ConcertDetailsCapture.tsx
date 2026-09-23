"use client";

import { useState } from "react";
import { updateProjectDetails } from "@/lib/api";

interface ConcertDetailsCaptureProps {
  projectId: number;
  chatActive: boolean; // true once the user has sent a chat message — auto-collapses this panel
}

type TicketOwner = "manager" | "venue";

const ChevronIcon = ({ direction }: { direction: "down" | "right" }) => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2">
    {direction === "down" ? <path d="M6 9l6 6 6-6" /> : <path d="M9 6l6 6-6 6" />}
  </svg>
);

export default function ConcertDetailsCapture({ projectId, chatActive }: ConcertDetailsCaptureProps) {
  const [ticketOwner, setTicketOwner] = useState<TicketOwner | null>(null);
  const [isPaid, setIsPaid] = useState<boolean | null>(null);
  const [saving, setSaving] = useState(false);
  // null = auto (collapses once the chat is in use), true/false = user override.
  const [manualOverride, setManualOverride] = useState<boolean | null>(null);
  const collapsed = manualOverride ?? chatActive;

  const saveField = async (details: Record<string, unknown>) => {
    setSaving(true);
    try {
      await updateProjectDetails(projectId, details);
    } catch (err) {
      console.error("[ConcertDetailsCapture] Failed to save project details", err);
    } finally {
      setSaving(false);
    }
  };

  const handleTicketOwner = (value: TicketOwner) => {
    setTicketOwner(value);
    saveField({ ticket_owner: value });
  };

  const handleIsPaid = (value: boolean) => {
    setIsPaid(value);
    saveField({ is_paid: value });
  };

  if (collapsed) {
    const summary = [
      ticketOwner === "manager" ? "I'm making tickets" : ticketOwner === "venue" ? "Venue tickets" : null,
      isPaid === true ? "Paid" : isPaid === false ? "Free" : null,
    ].filter(Boolean).join(" · ") || "Quick concert details";

    return (
      <button
        type="button"
        onClick={() => setManualOverride(false)}
        className="w-full flex items-center gap-3 px-5 py-3 border-b border-slate-200 shrink-0 hover:bg-slate-50 transition-colors text-left"
      >
        <span className="flex-1 min-w-0 text-sm text-slate-600 truncate">{summary}</span>
        <ChevronIcon direction="right" />
      </button>
    );
  }

  return (
    <div className="p-5 border-b border-slate-200 shrink-0 space-y-4">
      <div className="flex items-center gap-3">
        <p className="text-slate-600 text-sm font-medium flex-1">Quick concert details</p>
        {chatActive && (
          <button
            type="button"
            onClick={() => setManualOverride(true)}
            className="p-1.5 -m-1.5 rounded-lg hover:bg-slate-100 transition-colors"
            title="Collapse"
          >
            <ChevronIcon direction="down" />
          </button>
        )}
      </div>

      <div>
        <p className="text-xs text-slate-500 mb-2">Who's making the tickets?</p>
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => handleTicketOwner("manager")}
            className={`rounded-xl px-3 py-2 text-xs font-medium border transition-colors ${
              ticketOwner === "manager"
                ? "bg-slate-800 text-white border-slate-800"
                : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
            }`}
          >
            I am (manager)
          </button>
          <button
            type="button"
            onClick={() => handleTicketOwner("venue")}
            className={`rounded-xl px-3 py-2 text-xs font-medium border transition-colors ${
              ticketOwner === "venue"
                ? "bg-slate-800 text-white border-slate-800"
                : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
            }`}
          >
            The venue
          </button>
        </div>
      </div>

      <div>
        <p className="text-xs text-slate-500 mb-2">Is this a paid event?</p>
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => handleIsPaid(true)}
            className={`rounded-xl px-3 py-2 text-xs font-medium border transition-colors ${
              isPaid === true
                ? "bg-slate-800 text-white border-slate-800"
                : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
            }`}
          >
            Paid
          </button>
          <button
            type="button"
            onClick={() => handleIsPaid(false)}
            className={`rounded-xl px-3 py-2 text-xs font-medium border transition-colors ${
              isPaid === false
                ? "bg-slate-800 text-white border-slate-800"
                : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
            }`}
          >
            Free
          </button>
        </div>
      </div>

      {saving && <p className="text-xs text-slate-400">Saving…</p>}
    </div>
  );
}
