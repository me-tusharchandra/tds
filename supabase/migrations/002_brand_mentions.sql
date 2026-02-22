-- Brand mentions extracted from AI engine response text
CREATE TABLE brand_mentions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id UUID REFERENCES analyses(id) ON DELETE CASCADE,
  prompt_id UUID REFERENCES prompts(id) ON DELETE CASCADE,
  engine TEXT NOT NULL,
  brand_name TEXT NOT NULL,
  normalized_name TEXT NOT NULL,
  position INTEGER,
  context TEXT,
  competitor_id UUID REFERENCES competitors(id),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_brand_mentions_analysis ON brand_mentions(analysis_id);
CREATE INDEX idx_brand_mentions_competitor ON brand_mentions(competitor_id);
