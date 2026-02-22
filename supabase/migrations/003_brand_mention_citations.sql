-- Add source_citations column to brand_mentions
-- Stores an array of citation position numbers (e.g. {1, 3}) indicating
-- which citations in the response this brand was mentioned in connection with.
ALTER TABLE brand_mentions ADD COLUMN source_citations INTEGER[];
