export interface Analysis {
  id: string;
  brand_url: string;
  brand_name: string | null;
  status: "pending" | "discovering" | "analyzing" | "completed" | "failed";
  created_at: string;
  completed_at: string | null;
}

export interface Competitor {
  id: string;
  name: string;
  url: string;
  domain: string | null;
  description: string | null;
  is_primary: boolean;
  visibility_score: number | null;
  share_of_voice: number | null;
  citation_count: number | null;
  avg_position: number | null;
  engines: Record<
    string,
    { visibility_score: number; citation_count: number }
  > | null;
}

export interface Citation {
  id: string;
  engine: string;
  cited_url: string;
  cited_domain: string | null;
  cited_title: string | null;
  position: number | null;
  snippet: string | null;
  competitor_name: string | null;
  prompt_text: string | null;
}

export interface EngineScore {
  engine: string;
  visibility_score: number;
  share_of_voice: number;
  citation_count: number;
  avg_position: number | null;
}

export interface Overview {
  analysis_id: string;
  brand_name: string | null;
  brand_url: string;
  status: string;
  overall_visibility: number;
  overall_sov: number;
  total_citations: number;
  engines: EngineScore[];
  competitor_count: number;
  prompt_count: number;
}

export interface HistoryEntry {
  analysis_id: string;
  created_at: string;
  visibility_score: number;
  share_of_voice: number;
  citation_count: number;
}

export interface PromptResult {
  prompt_id: string;
  prompt_text: string;
  category: string | null;
  citations: Citation[];
}

export const ENGINE_LABELS: Record<string, string> = {
  openai: "OpenAI GPT-4o",
  gemini: "Gemini 2.0 Flash",
  perplexity: "Perplexity Sonar",
  exa: "Exa AI",
};

export const ENGINE_COLORS: Record<string, string> = {
  openai: "hsl(var(--chart-1))",
  gemini: "hsl(var(--chart-2))",
  perplexity: "hsl(var(--chart-3))",
  exa: "hsl(var(--chart-4))",
};
