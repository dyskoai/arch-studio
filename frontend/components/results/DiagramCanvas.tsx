"use client";

import { useArchStore } from "@/store/useArchStore";
import type { ArchNode, Tier } from "@/lib/types";

const NODE_W = 160;
const NODE_H = 52;
const H_GAP  = 36;
const V_GAP  = 72;
const PAD_X  = 60;
const PAD_Y  = 48;

// SVG fill colours per tier — Tailwind bg-* classes don't apply to SVG shapes
const TIER_FILL: Record<Tier, string> = {
  entry:  "#1a1a2e",
  light:  "#16213e",
  medium: "#0f3460",
  heavy:  "#533483",
};
const TIER_STROKE: Record<Tier, string> = {
  entry:  "#475569",
  light:  "#1d4ed8",
  medium: "#0d9488",
  heavy:  "#a855f7",
};
const TIER_LABEL: Record<Tier, string> = {
  entry: "ENTRY", light: "LIGHT", medium: "MEDIUM", heavy: "HEAVY",
};

function layoutNodes(nodes: ArchNode[]): Map<string, { x: number; y: number }> {
  const layers = new Map<number, ArchNode[]>();
  for (const n of nodes) {
    if (!layers.has(n.layer)) layers.set(n.layer, []);
    layers.get(n.layer)!.push(n);
  }
  const pos = new Map<string, { x: number; y: number }>();
  const layerEntries = Array.from(layers.entries());
  const maxCount = Math.max(...layerEntries.map(([, l]) => l.length));

  for (const [layer, nodesInLayer] of layerEntries) {
    const count = nodesInLayer.length;
    const totalW = count * NODE_W + (count - 1) * H_GAP;
    const maxW   = maxCount * NODE_W + (maxCount - 1) * H_GAP;
    const offsetX = PAD_X + (maxW - totalW) / 2;
    nodesInLayer.forEach((n, i) => {
      pos.set(n.id, {
        x: offsetX + i * (NODE_W + H_GAP),
        y: PAD_Y + layer * (NODE_H + V_GAP),
      });
    });
  }
  return pos;
}

function edgePath(
  from: { x: number; y: number },
  to:   { x: number; y: number }
): string {
  const x1 = from.x + NODE_W / 2;
  const y1 = from.y + NODE_H;
  const x2 = to.x   + NODE_W / 2;
  const y2 = to.y;
  const cy = (y1 + y2) / 2;
  return `M ${x1} ${y1} C ${x1} ${cy}, ${x2} ${cy}, ${x2} ${y2}`;
}

// Back-edges (output → input) loop around the left margin so they don't
// cut through the diagram. The path hugs the left side with rounded corners.
function backEdgePath(
  from: { x: number; y: number },
  to:   { x: number; y: number }
): string {
  const srcCx = from.x + NODE_W / 2;
  const srcY  = from.y + NODE_H;       // bottom of source node
  const dstCx = to.x   + NODE_W / 2;
  const dstY  = to.y;                  // top of target node
  const xL = 12;                       // left margin rail x
  const r  = 20;                       // bezier pull for smooth corners
  return [
    `M ${srcCx} ${srcY}`,
    // arc left: pull control points horizontally toward the rail
    `C ${srcCx - r} ${srcY}, ${xL} ${srcY - r}, ${xL} ${srcY - r * 2}`,
    // straight up the left rail
    `L ${xL} ${dstY + r * 2}`,
    // arc right: curve into the target node top
    `C ${xL} ${dstY + r}, ${dstCx - r} ${dstY}, ${dstCx} ${dstY}`,
  ].join(" ");
}

export function DiagramCanvas() {
  const result = useArchStore((s) => s.result);

  // Subscribe to the raw values — function selector causes no re-renders on change
  const hoveredNodeId  = useArchStore((s) => s.hoveredNodeId);
  const selectedNodeId = useArchStore((s) => s.selectedNodeId);
  const activeNodeId   = selectedNodeId ?? hoveredNodeId;

  const setHovered  = useArchStore((s) => s.setHoveredNodeId);
  const setSelected = useArchStore((s) => s.setSelectedNodeId);

  if (!result) return null;

  const pos      = layoutNodes(result.nodes);
  const maxLayer = Math.max(...result.nodes.map((n) => n.layer));
  const uniqueLayers = Array.from(new Set(result.nodes.map((n) => n.layer)));
  const maxCount = Math.max(
    ...uniqueLayers.map(
      (l) => result.nodes.filter((n) => n.layer === l).length
    )
  );
  const svgW = PAD_X * 2 + maxCount * NODE_W + (maxCount - 1) * H_GAP;
  const svgH = PAD_Y * 2 + (maxLayer + 1) * (NODE_H + V_GAP);

  return (
    <div className="p-8">
      <svg
        width={svgW}
        height={svgH}
        viewBox={`0 0 ${svgW} ${svgH}`}
        style={{ userSelect: "none", display: "block", margin: "0 auto" }}
      >
        <defs>
          <marker id="arr"        markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="#334155" />
          </marker>
          <marker id="arr-a"      markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="#2dd4bf" />
          </marker>
          <marker id="arr-loop"   markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="#78350f" />
          </marker>
          <marker id="arr-loop-a" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="#f59e0b" />
          </marker>
        </defs>

        {/* Edges */}
        {result.edges.map((edge, i) => {
          const fp = pos.get(edge.from);
          const tp = pos.get(edge.to);
          if (!fp || !tp) return null;
          const active   = activeNodeId === edge.from || activeNodeId === edge.to;
          const isBack   = fp.y >= tp.y;  // source is at or below target — conversation loop
          const d        = isBack ? backEdgePath(fp, tp) : edgePath(fp, tp);
          const stroke   = isBack
            ? (active ? "#f59e0b" : "#78350f")   // amber for loopback
            : (active ? "#2dd4bf" : "#1e2a3a");
          const marker   = isBack
            ? (active ? "url(#arr-loop-a)" : "url(#arr-loop)")
            : (active ? "url(#arr-a)"      : "url(#arr)");
          return (
            <g key={i}>
              <path
                d={d}
                fill="none"
                stroke={stroke}
                strokeWidth={isBack ? 1 : (active ? 1.5 : 1)}
                strokeDasharray={isBack ? "4 3" : undefined}
                markerEnd={marker}
              />
              {edge.label && active && (
                <text
                  x={isBack ? 20 : (fp.x + tp.x) / 2 + NODE_W / 2}
                  y={isBack ? (fp.y + NODE_H + tp.y) / 2 : (fp.y + NODE_H + tp.y) / 2}
                  textAnchor="start"
                  fontSize={8}
                  fill={isBack ? "#f59e0b" : "#2dd4bf"}
                >
                  {edge.label}
                </text>
              )}
            </g>
          );
        })}

        {/* Nodes */}
        {result.nodes.map((node) => {
          const p = pos.get(node.id);
          if (!p) return null;
          const active = activeNodeId === node.id;

          return (
            <g
              key={node.id}
              transform={`translate(${p.x},${p.y})`}
              style={{ cursor: "pointer" }}
              onMouseEnter={() => setHovered(node.id)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => setSelected(node.id)}
            >
              <rect
                width={NODE_W}
                height={NODE_H}
                rx={6}
                fill={active ? "#0d2e2e" : TIER_FILL[node.tier]}
                stroke={active ? "#2dd4bf" : TIER_STROKE[node.tier]}
                strokeWidth={active ? 1.5 : 1}
              />
              <text
                x={NODE_W / 2}
                y={NODE_H / 2 - 7}
                textAnchor="middle"
                fontSize={11}
                fontWeight={500}
                fill="#e2e8f0"
              >
                {node.label}
              </text>
              <text
                x={NODE_W / 2}
                y={NODE_H / 2 + 9}
                textAnchor="middle"
                fontSize={8}
                fill={active ? "#2dd4bf" : TIER_STROKE[node.tier]}
              >
                {TIER_LABEL[node.tier]}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
