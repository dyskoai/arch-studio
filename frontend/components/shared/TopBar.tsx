"use client";

import { useArchStore } from "@/store/useArchStore";

export function TopBar() {
  const reset = useArchStore((s) => s.reset);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-3 border-b border-[#1e1e2e] bg-[#0a0a0f]/90 backdrop-blur">
      <span className="text-[10px] tracking-[0.3em] text-slate-500 uppercase">
        Arch Studio
      </span>
      <button
        onClick={reset}
        className="text-[10px] tracking-[0.2em] text-slate-500 uppercase hover:text-teal-400 transition-colors"
      >
        ← New
      </button>
    </header>
  );
}
