"use client";

import { useArchStore } from "@/store/useArchStore";
import { TIER_CONFIG } from "@/lib/tierConfig";
import type { ArchNode } from "@/lib/types";

function NodeDetail({ node }: { node: ArchNode }) {
  const cfg = TIER_CONFIG[node.tier];
  return (
    <div className="p-4 flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
        <span className="text-[9px] tracking-[0.25em] uppercase text-slate-500">
          {cfg.label} · Layer {node.layer}
        </span>
      </div>
      <h3 className="text-sm font-medium text-white">{node.label}</h3>
      <p className="text-xs text-slate-400 leading-relaxed">{node.role}</p>
      {node.rationale && (
        <p className="text-xs text-slate-500 italic">{node.rationale}</p>
      )}
      {(node.primary || node.secondary) && (
        <div className="flex flex-col gap-2 mt-1 pt-2 border-t border-[#1e1e2e]">
          <p className="text-[9px] tracking-[0.2em] uppercase text-slate-600">Model</p>
          {node.primary && (
            <div className="flex flex-col gap-0.5">
              <span className="text-[9px] text-slate-600 uppercase tracking-wide">Commercial</span>
              <span className="text-sm font-medium text-teal-400">{node.primary}</span>
            </div>
          )}
          {node.secondary && (
            <div className="flex flex-col gap-0.5">
              <span className="text-[9px] text-slate-600 uppercase tracking-wide">Open-weight alt.</span>
              <span className="text-sm font-medium text-slate-300">{node.secondary}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function NodeInspector() {
  const result         = useArchStore((s) => s.result);
  const hoveredNodeId  = useArchStore((s) => s.hoveredNodeId);
  const selectedNodeId = useArchStore((s) => s.selectedNodeId);
  const activeNodeId   = selectedNodeId ?? hoveredNodeId;

  const activeNode = result?.nodes.find((n) => n.id === activeNodeId) ?? null;

  return (
    <div className="h-full border-l border-[#1e1e2e] flex flex-col">
      <div className="px-4 py-3 border-b border-[#1e1e2e]">
        <p className="text-[9px] tracking-[0.25em] text-slate-600 uppercase">
          Node Inspector
        </p>
      </div>
      {activeNode ? (
        <NodeDetail node={activeNode} />
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-[10px] text-slate-700">hover or click a node</p>
        </div>
      )}
    </div>
  );
}
