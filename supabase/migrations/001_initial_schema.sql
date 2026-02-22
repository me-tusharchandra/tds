-- Analyses: each analysis run
CREATE TABLE analyses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_url TEXT NOT NULL,
  brand_name TEXT,
  brand_domain TEXT,
  status TEXT DEFAULT 'pending', -- pending, discovering, analyzing, completed, failed
  created_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ
);

-- Competitors discovered per analysis
CREATE TABLE competitors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id UUID REFERENCES analyses(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  domain TEXT,
  description TEXT,
  is_primary BOOLEAN DEFAULT FALSE, -- true for the input brand itself
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Search prompts used
CREATE TABLE prompts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id UUID REFERENCES analyses(id) ON DELETE CASCADE,
  prompt_text TEXT NOT NULL,
  category TEXT -- e.g. "alternatives", "best tools", "comparison"
);

-- Individual citations from AI engines
CREATE TABLE citations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id UUID REFERENCES analyses(id) ON DELETE CASCADE,
  prompt_id UUID REFERENCES prompts(id) ON DELETE CASCADE,
  engine TEXT NOT NULL, -- 'openai', 'gemini', 'perplexity', 'exa'
  cited_url TEXT NOT NULL,
  cited_domain TEXT,
  cited_title TEXT,
  position INTEGER, -- position in the citation list (1 = first cited)
  snippet TEXT, -- text around the citation
  competitor_id UUID REFERENCES competitors(id), -- matched competitor
  raw_response JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Calculated visibility scores per competitor per engine per analysis
CREATE TABLE visibility_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id UUID REFERENCES analyses(id) ON DELETE CASCADE,
  competitor_id UUID REFERENCES competitors(id) ON DELETE CASCADE,
  engine TEXT, -- 'openai', 'gemini', 'perplexity', 'exa', 'overall'
  visibility_score FLOAT, -- 0-100
  share_of_voice FLOAT, -- 0-100 percentage
  citation_count INTEGER,
  avg_position FLOAT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for common queries
CREATE INDEX idx_competitors_analysis ON competitors(analysis_id);
CREATE INDEX idx_prompts_analysis ON prompts(analysis_id);
CREATE INDEX idx_citations_analysis ON citations(analysis_id);
CREATE INDEX idx_citations_engine ON citations(engine);
CREATE INDEX idx_citations_competitor ON citations(competitor_id);
CREATE INDEX idx_visibility_analysis ON visibility_scores(analysis_id);
CREATE INDEX idx_visibility_competitor ON visibility_scores(competitor_id);
CREATE INDEX idx_analyses_brand_url ON analyses(brand_url);
CREATE INDEX idx_analyses_status ON analyses(status);
