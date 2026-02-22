const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// Analyses
export function createAnalysis(brandUrl: string) {
  return fetchApi<{ id: string; status: string }>("/api/analyses", {
    method: "POST",
    body: JSON.stringify({ brand_url: brandUrl }),
  });
}

export function listAnalyses() {
  return fetchApi<
    Array<{
      id: string;
      brand_url: string;
      brand_name: string | null;
      status: string;
      created_at: string;
    }>
  >("/api/analyses");
}

export function getAnalysisStatus(id: string) {
  return fetchApi<{
    id: string;
    status: string;
    brand_name: string | null;
    progress: import("./types").AnalysisProgress | null;
  }>(`/api/analyses/${id}/status`);
}

// Dashboard
import type {
  Overview,
  Competitor,
  Citation,
  EngineScore,
  HistoryEntry,
  PromptResult,
  TopCitedBrand,
  BrandMention,
} from "./types";

export function getOverview(id: string) {
  return fetchApi<Overview>(`/api/analyses/${id}/overview`);
}

export function getCompetitors(id: string) {
  return fetchApi<{ competitors: Competitor[] }>(
    `/api/analyses/${id}/competitors`
  );
}

export function getCitations(id: string, engine?: string) {
  const params = engine ? `?engine=${engine}` : "";
  return fetchApi<{ citations: Citation[]; total: number }>(
    `/api/analyses/${id}/citations${params}`
  );
}

export function getEngineBreakdown(id: string) {
  return fetchApi<{ engines: EngineScore[]; brand_scores: Record<string, number> }>(
    `/api/analyses/${id}/engines`
  );
}

export function getHistory(id: string) {
  return fetchApi<{ brand_url: string; entries: HistoryEntry[] }>(
    `/api/analyses/${id}/history`
  );
}

export function getPromptResults(id: string) {
  return fetchApi<{ prompts: PromptResult[] }>(
    `/api/analyses/${id}/prompts`
  );
}

export function getTopCitedBrands(id: string) {
  return fetchApi<{ brands: TopCitedBrand[] }>(
    `/api/analyses/${id}/top-cited`
  );
}

export function getBrandMentions(id: string) {
  return fetchApi<{ brands: BrandMention[]; total: number }>(
    `/api/analyses/${id}/brand-mentions`
  );
}
