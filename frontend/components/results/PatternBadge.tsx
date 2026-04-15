"use client";

import type { Pattern } from "@/lib/types";

const LABELS: Record<Pattern, string> = {
  "single-agent-router": "Single-Agent Router",
  "multi-agent-supervisor": "Multi-Agent Supervisor",
};

export function PatternBadge({ pattern }: { pattern: Pattern }) {
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 text-[9px] tracking-[0.2em] uppercase border border-teal-700 text-teal-400 rounded">
      <span className="w-1.5 h-1.5 rounded-full bg-teal-400" />
      {LABELS[pattern]}
    </span>
  );
}
