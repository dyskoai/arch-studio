"use client";

import { useArchStore } from "@/store/useArchStore";
import { RoughInputPanel } from "@/components/phase1/RoughInputPanel";
import { RefinedSpecEditor } from "@/components/phase1/RefinedSpecEditor";
import { ResultsLayout } from "@/components/results/ResultsLayout";
import {
  LoadingScreen,
  REFINING_MESSAGES,
  GENERATING_MESSAGES,
} from "@/components/shared/LoadingScreen";

export default function Home() {
  const screen = useArchStore((s) => s.screen);

  switch (screen) {
    case "rough_input":
      return <RoughInputPanel />;
    case "refining":
      return <LoadingScreen messages={REFINING_MESSAGES} />;
    case "refined_review":
      return <RefinedSpecEditor />;
    case "generating":
      return <LoadingScreen messages={GENERATING_MESSAGES} />;
    case "results":
      return <ResultsLayout />;
  }
}
