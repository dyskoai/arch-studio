"use client";

export function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-[#1e1e2e] last:border-0">
      <span className="text-[10px] tracking-wide text-slate-500 uppercase">{label}</span>
      <span className="text-xs text-slate-300 font-medium">{value}</span>
    </div>
  );
}
