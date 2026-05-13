export interface AnalysisProgress {
  competitors_found?: number;
  prompts_generated?: number;
  engines?: Record<string, { completed: number; total: number }>;
  citations_found?: number;
  brands_found?: number;
}

export interface Analysis {
  id: string;
  brand_url: string;
  brand_name: string | null;
  status:
    | "pending"
    | "discovering"
    | "generating_prompts"
    | "querying_engines"
    | "scoring"
    | "completed"
    | "failed";
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
  brand_mention_count: number | null;
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
  mentioned_brands: string[];
}

export interface EngineScore {
  engine: string;
  visibility_score: number;
  share_of_voice: number;
  citation_count: number;
  avg_position: number | null;
  status?: "ok" | "skipped";
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

export interface TopCitedBrand {
  domain: string;
  citation_count: number;
  avg_position: number | null;
  engines: string[];
  sample_urls: string[];
  sample_title: string | null;
  is_primary: boolean;
}

export interface BrandMention {
  brand_name: string;
  normalized_name: string;
  mention_count: number;
  avg_position: number | null;
  engines: string[];
  prompt_count: number;
  presence_rate: number | null;
  competitor_name: string | null;
  is_primary: boolean;
  sample_contexts: string[];
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
