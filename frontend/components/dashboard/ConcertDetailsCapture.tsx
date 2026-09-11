"use client";

import { useState } from "react";
import { updateProjectDetails } from "@/lib/api";

interface ConcertDetailsCaptureProps {
  projectId: number;
}

type TicketOwner = "manager" | "venue";

export default function ConcertDetailsCapture({ projectId }: ConcertDetailsCaptureProps) {
  const [ticketOwner, setTicketOwner] = useState<TicketOwner | null>(null);
  const [isPaid, setIsPaid] = useState<boolean | null>(null);
  const [saving, setSaving] = useState(false);

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

  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100 space-y-4">
      <p className="text-slate-600 text-sm font-medium">Quick concert details</p>

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
