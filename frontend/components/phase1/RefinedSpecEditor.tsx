"use client";

import { useArchStore } from "@/store/useArchStore";

export function RefinedSpecEditor() {
  const refinedSpec = useArchStore((s) => s.refinedSpec);
  const setRefinedSpec = useArchStore((s) => s.setRefinedSpec);
  const generate = useArchStore((s) => s.generate);
  const reset = useArchStore((s) => s.reset);
  const error = useArchStore((s) => s.error);

  const wordCount = refinedSpec.trim() ? refinedSpec.trim().split(/\s+/).length : 0;
  const canGenerate = refinedSpec.trim().length >= 20;

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6 py-20">
      <div className="w-full max-w-xl flex flex-col gap-6">
        {/* Label */}
        <p className="text-[9px] tracking-[0.35em] text-teal-400 uppercase">
          AI-Refined Specification
        </p>

        <p className="text-xs text-slate-500">
          Review and edit before generating. This is what the architecture will be based on.
        </p>

        {/* Editable textarea */}
        <div className="relative">
          <textarea
            value={refinedSpec}
            onChange={(e) => setRefinedSpec(e.target.value)}
            rows={6}
            className="w-full bg-[#111118] border border-[#1e1e2e] rounded px-4 py-3 text-sm text-slate-100 resize-none focus:outline-none focus:border-teal-500 transition-colors leading-relaxed"
          />
          <span className="absolute bottom-2 left-3 text-[10px] text-slate-600">
            {wordCount} words
          </span>
        </div>

        {/* Error */}
        {error && (
          <p className="text-xs text-red-400 border border-red-900 bg-red-950/30 rounded px-3 py-2">
            {error}
          </p>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-3">
          <button
            onClick={reset}
            className="px-4 py-2 text-[11px] tracking-[0.15em] uppercase text-slate-500 hover:text-slate-300 transition-colors"
          >
            ← Start Over
          </button>
          <button
            onClick={generate}
            disabled={!canGenerate}
            className="px-6 py-2.5 text-[11px] tracking-[0.2em] uppercase font-medium bg-teal-500 text-black rounded hover:bg-teal-400 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Generate Architecture →
          </button>
        </div>
      </div>
    </div>
  );
}
