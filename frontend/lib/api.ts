import type { ArchResult, GenerateResponse, RefineResponse } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Unknown error" }));
    throw Object.assign(new Error(err.error ?? "Request failed"), {
      code: err.code,
      status: res.status,
    });
  }
  return res.json() as Promise<T>;
}

// Phase 1
export async function refineSpec(roughInput: string): Promise<RefineResponse> {
  return post<RefineResponse>("/refine", { rough_input: roughInput });
}

// Phase 2
export async function generateArchitecture(
  refinedSpec: string
): Promise<GenerateResponse> {
  return post<GenerateResponse>("/generate", { refined_spec: refinedSpec });
}

// Export — draw.io
export async function exportDrawio(result: ArchResult): Promise<Blob> {
  const res = await fetch(`${BASE}/export/drawio`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ result }),
  });
  if (!res.ok) throw new Error("draw.io export failed");
  return res.blob();
}

// Export — Mermaid (.mmd text)
export async function exportMermaid(result: ArchResult): Promise<string> {
  const res = await fetch(`${BASE}/export/mermaid`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ result }),
  });
  if (!res.ok) throw new Error("Mermaid export failed");
  return res.text();
}
