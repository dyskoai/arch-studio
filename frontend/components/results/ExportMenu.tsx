"use client";

import { useArchStore } from "@/store/useArchStore";
import { exportDrawio, exportMermaid } from "@/lib/api";

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a   = document.createElement("a");
  a.href     = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function downloadText(text: string, filename: string) {
  downloadBlob(new Blob([text], { type: "text/plain" }), filename);
}

export function ExportMenu() {
  const result           = useArchStore((s) => s.result);
  const showExportMenu   = useArchStore((s) => s.showExportMenu);
  const setShowExportMenu = useArchStore((s) => s.setShowExportMenu);
  const copied           = useArchStore((s) => s.copied);
  const setCopied        = useArchStore((s) => s.setCopied);

  if (!result) return null;

  const close = () => setShowExportMenu(false);

  const handleJSON = () => {
    downloadText(JSON.stringify(result, null, 2), "architecture.json");
    close();
  };

  const handleCopyJSON = async () => {
    await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    close();
  };

  const handleDrawio = async () => {
    try {
      const blob = await exportDrawio(result);
      downloadBlob(blob, "architecture.drawio");
    } catch { /* user can retry */ }
    close();
  };

  const handleSVG = () => {
    const svg = document.querySelector("svg");
    if (!svg) return;
    downloadBlob(new Blob([svg.outerHTML], { type: "image/svg+xml" }), "architecture.svg");
    close();
  };

  const handleMermaidDownload = async () => {
    try {
      const mmd = await exportMermaid(result);
      downloadText(mmd, "architecture.mmd");
    } catch { /* user can retry */ }
    close();
  };

  const handleMermaidCopy = async () => {
    try {
      const mmd = await exportMermaid(result);
      // Wrap in GitHub markdown fenced block for instant paste into a .md file
      const mdBlock = "```mermaid\n" + mmd + "\n```";
      await navigator.clipboard.writeText(mdBlock);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* user can retry */ }
    close();
  };

  const items = [
    { label: "JSON",                    action: handleJSON },
    { label: copied ? "Copied!" : "Copy JSON", action: handleCopyJSON },
    { label: "draw.io (.drawio)",       action: handleDrawio },
    { label: "SVG",                     action: handleSVG },
    { label: "Mermaid (.mmd)",          action: handleMermaidDownload },
    { label: copied ? "Copied!" : "Copy Mermaid (GitHub)", action: handleMermaidCopy },
  ];

  return (
    <div className="relative">
      <button
        onClick={() => setShowExportMenu(!showExportMenu)}
        className="px-4 py-2 text-[10px] tracking-[0.2em] uppercase border border-[#1e1e2e] text-slate-400 rounded hover:border-teal-500 hover:text-teal-400 transition-colors"
      >
        Export ↓
      </button>

      {showExportMenu && (
        <>
          {/* Backdrop to close on outside click */}
          <div
            className="fixed inset-0 z-40"
            onClick={close}
          />
          <div className="absolute right-0 top-full mt-1 w-52 bg-[#111118] border border-[#1e1e2e] rounded shadow-xl z-50">
            {items.map(({ label, action }) => (
              <button
                key={label}
                onClick={action}
                className="w-full text-left px-4 py-2.5 text-xs text-slate-400 hover:bg-[#161620] hover:text-white transition-colors"
              >
                {label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
