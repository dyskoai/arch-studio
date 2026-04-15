"use client";

import { useArchStore } from "@/store/useArchStore";
import { TopBar } from "@/components/shared/TopBar";
import { DiagramCanvas } from "./DiagramCanvas";
import { NodeInspector } from "./NodeInspector";
import { PatternBadge } from "./PatternBadge";
import { ExportMenu } from "./ExportMenu";

export function ResultsLayout() {
  const result = useArchStore((s) => s.result);
  const meta   = useArchStore((s) => s.meta);

  if (!result || !meta) return null;

  const totalSec = (meta.stages.total_ms / 1000).toFixed(1);

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <TopBar />

      {/* Sub-header — single slim bar */}
      <div className="mt-12 px-5 py-2.5 border-b border-[#1e1e2e] flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <h2 className="text-sm font-medium text-white truncate">{result.title}</h2>
          <PatternBadge pattern={result.pattern} />
          {meta.repaired && (
            <span className="shrink-0 text-[9px] tracking-wide text-amber-500 border border-amber-800 px-1.5 py-0.5 rounded">
              repaired
            </span>
          )}
        </div>

        <div className="flex items-center gap-4 shrink-0">
          {/* Inline meta — less clutter than a full side panel */}
          <span className="text-[10px] text-slate-600">
            {result.nodes.length} nodes · {result.edges.length} edges · {totalSec}s
          </span>
          <ExportMenu />
        </div>
      </div>

      {/* Main — diagram takes most space, inspector is a narrow strip */}
      <div className="flex flex-1 min-h-0">
        <div className="flex-1 overflow-auto">
          <DiagramCanvas />
        </div>

        {/* Inspector — narrower, just the node detail */}
        <div className="w-56 shrink-0 border-l border-[#1e1e2e] flex flex-col overflow-hidden">
          <NodeInspector />

          {/* Justification at the bottom */}
          <div className="border-t border-[#1e1e2e] p-3">
            <p className="text-[9px] tracking-[0.2em] text-slate-600 uppercase mb-1.5">
              Why this pattern
            </p>
            <p className="text-[10px] text-slate-500 leading-relaxed line-clamp-6">
              {result.justification}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
