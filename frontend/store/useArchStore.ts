"use client";

import { create } from "zustand";
import type { ArchResult, GenerateResponse } from "@/lib/types";
import { refineSpec, generateArchitecture } from "@/lib/api";

export type Screen =
  | "rough_input"    // Phase 1a: user types rough problem
  | "refining"       // Phase 1b: loading — refiner running
  | "refined_review" // Phase 1c: user reviews / edits refined spec
  | "generating"     // Phase 2a: loading — pipeline running
  | "results";       // Phase 2b: diagram ready

interface ArchStore {
  // Phase 1
  screen: Screen;
  roughInput: string;
  refinedSpec: string;
  setRoughInput: (v: string) => void;
  setRefinedSpec: (v: string) => void;
  refine: () => Promise<void>;

  // Phase 2
  result: ArchResult | null;
  meta: GenerateResponse["meta"] | null;
  error: string;
  generate: () => Promise<void>;

  // Diagram interaction
  hoveredNodeId: string | null;
  selectedNodeId: string | null;
  setHoveredNodeId: (id: string | null) => void;
  setSelectedNodeId: (id: string | null) => void;
  activeNodeId: () => string | null;

  // Export
  showExportMenu: boolean;
  setShowExportMenu: (v: boolean) => void;
  copied: boolean;
  setCopied: (v: boolean) => void;

  reset: () => void;
}

export const useArchStore = create<ArchStore>((set, get) => ({
  screen: "rough_input",
  roughInput: "",
  refinedSpec: "",
  setRoughInput: (roughInput) => set({ roughInput }),
  setRefinedSpec: (refinedSpec) => set({ refinedSpec }),

  refine: async () => {
    const { roughInput } = get();
    if (!roughInput.trim() || roughInput.length < 5) return;
    set({ screen: "refining", error: "" });
    try {
      const data = await refineSpec(roughInput);
      set({ refinedSpec: data.refined_spec, screen: "refined_review" });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Refinement failed.";
      set({ error: msg, screen: "rough_input" });
    }
  },

  result: null,
  meta: null,
  error: "",

  generate: async () => {
    const { refinedSpec } = get();
    if (!refinedSpec.trim() || refinedSpec.length < 20) return;
    set({ screen: "generating", error: "", result: null });
    try {
      const data = await generateArchitecture(refinedSpec);
      set({ result: data.result, meta: data.meta, screen: "results" });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Generation failed.";
      set({ error: msg, screen: "refined_review" });
    }
  },

  hoveredNodeId: null,
  selectedNodeId: null,
  setHoveredNodeId: (id) => set({ hoveredNodeId: id }),
  setSelectedNodeId: (id) =>
    set((s) => ({ selectedNodeId: s.selectedNodeId === id ? null : id })),
  activeNodeId: () => get().selectedNodeId ?? get().hoveredNodeId,

  showExportMenu: false,
  setShowExportMenu: (v) => set({ showExportMenu: v }),
  copied: false,
  setCopied: (v) => set({ copied: v }),

  reset: () =>
    set({
      screen: "rough_input",
      roughInput: "",
      refinedSpec: "",
      result: null,
      meta: null,
      error: "",
      selectedNodeId: null,
      hoveredNodeId: null,
    }),
}));
