import type { Tier } from "./types";

export interface TierConfig {
  bg: string;
  border: string;
  label: string;
  dot: string;
}

export const TIER_CONFIG: Record<Tier, TierConfig> = {
  entry: {
    bg: "bg-[#1a1a2e]",
    border: "border-slate-600",
    label: "ENTRY",
    dot: "bg-slate-400",
  },
  light: {
    bg: "bg-[#16213e]",
    border: "border-blue-700",
    label: "LIGHT",
    dot: "bg-blue-400",
  },
  medium: {
    bg: "bg-[#0f3460]",
    border: "border-teal-600",
    label: "MEDIUM",
    dot: "bg-teal-400",
  },
  heavy: {
    bg: "bg-[#533483]",
    border: "border-purple-500",
    label: "HEAVY",
    dot: "bg-purple-300",
  },
};
