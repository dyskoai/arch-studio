// ─── Phase 1 ──────────────────────────────────────────────────────────────────
export interface RefineRequest  { rough_input: string; }
export interface RefineResponse { refined_spec: string; word_count: number; }

// ─── Phase 2 ──────────────────────────────────────────────────────────────────
export type Tier    = "entry" | "light" | "medium" | "heavy";
export type Pattern = "single-agent-router" | "multi-agent-supervisor";

export interface ArchNode {
  id: string;
  label: string;
  tier: Tier;
  layer: number;
  role: string;
  rationale: string;
  primary: string;
  secondary: string;
}

export interface ArchEdge {
  from: string;
  to: string;
  label: string;
}

export interface ArchResult {
  pattern: Pattern;
  title: string;
  justification: string;
  nodes: ArchNode[];
  edges: ArchEdge[];
}

export interface PipelineTimings {
  router_ms: number;
  architect_ms: number;
  validator_ms: number;
  total_ms: number;
}

export interface GenerateMeta {
  pattern: Pattern;
  stages: PipelineTimings;
  repaired: boolean;
}

export interface GenerateResponse {
  result: ArchResult;
  meta: GenerateMeta;
}

export interface GenerateErrorResponse {
  error: string;
  code: "RATE_LIMITED" | "INVALID_INPUT" | "REFINE_FAILED" | "GENERATION_FAILED";
}
