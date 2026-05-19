"use client";

import { Plus } from "lucide-react";

interface ProgressBarProps {
  progress: number;
}

export default function ProgressBar({ progress }: ProgressBarProps) {
  // Create gradient segments
  const colors = [
    "bg-green-400",
    "bg-lime-400",
    "bg-yellow-400",
    "bg-orange-400",
    "bg-red-400",
    "bg-pink-400",
    "bg-purple-400",
    "bg-blue-400",
  ];

  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-slate-800 font-semibold text-base">Progress Bar</h3>
        <button className="w-7 h-7 flex items-center justify-center rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors">
          <Plus size={18} />
        </button>
      </div>

      {/* Progress bar with rainbow gradient */}
      <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden flex">
        {colors.map((color, i) => {
          const segmentWidth = 100 / colors.length;
          const fillAmount = Math.min(
            100,
            Math.max(0, (progress - i * segmentWidth) / segmentWidth) * 100
          );

          return (
            <div
              key={i}
              className="flex-1 relative overflow-hidden"
            >
              <div
                className={`h-full ${color} transition-all duration-500`}
                style={{ width: `${fillAmount}%` }}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
