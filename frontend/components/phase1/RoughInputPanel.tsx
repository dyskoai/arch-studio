"use client";

import { useArchStore } from "@/store/useArchStore";

const EXAMPLES = [
  "Order status for support",
  "Customer support triage",
  "Code review pipeline",
];

const MAX_CHARS = 500;

export function RoughInputPanel() {
  const roughInput = useArchStore((s) => s.roughInput);
  const setRoughInput = useArchStore((s) => s.setRoughInput);
  const refine = useArchStore((s) => s.refine);
  const error = useArchStore((s) => s.error);

  const canSubmit = roughInput.trim().length >= 5;

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6 py-20">
      <div className="w-full max-w-xl flex flex-col gap-8">
        {/* Brand */}
        <p className="text-[9px] tracking-[0.35em] text-slate-500 uppercase">
          Intentiv · Architecture Studio
        </p>

        {/* Headline */}
        <div>
          <h1 className="text-3xl font-medium text-white mb-2">
            What are you building?
          </h1>
          <p className="text-sm text-slate-500">
            Describe it roughly. We&apos;ll make it precise.
          </p>
        </div>

        {/* Example pills */}
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => setRoughInput(ex)}
              className="px-3 py-1 text-[11px] tracking-wide border border-[#1e1e2e] text-slate-400 rounded hover:border-teal-500 hover:text-teal-400 transition-colors"
            >
              {ex}
            </button>
          ))}
        </div>

        {/* Textarea */}
        <div className="relative">
          <textarea
            value={roughInput}
            onChange={(e) => setRoughInput(e.target.value.slice(0, MAX_CHARS))}
            placeholder="Describe the problem in plain language. Don't overthink it."
            rows={3}
            className="w-full bg-[#111118] border border-[#1e1e2e] rounded px-4 py-3 text-sm text-slate-200 placeholder-slate-600 resize-none focus:outline-none focus:border-teal-500 transition-colors"
          />
          <span className="absolute bottom-2 right-3 text-[10px] text-slate-600">
            {roughInput.length}/{MAX_CHARS}
          </span>
        </div>

        {/* Error */}
        {error && (
          <p className="text-xs text-red-400 border border-red-900 bg-red-950/30 rounded px-3 py-2">
            {error}
          </p>
        )}

        {/* Submit */}
        <button
          onClick={refine}
          disabled={!canSubmit}
          className="self-end px-6 py-2.5 text-[11px] tracking-[0.2em] uppercase font-medium bg-teal-500 text-black rounded hover:bg-teal-400 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        >
          Refine My Idea →
        </button>
      </div>
    </div>
  );
}
