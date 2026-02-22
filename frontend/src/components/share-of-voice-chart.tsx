"use client";

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Competitor, BrandMention } from "@/lib/types";

const COLORS = [
  "hsl(220, 90%, 56%)",
  "hsl(160, 60%, 45%)",
  "hsl(30, 90%, 56%)",
  "hsl(280, 60%, 56%)",
  "hsl(0, 70%, 56%)",
  "hsl(190, 70%, 45%)",
  "hsl(45, 90%, 50%)",
  "hsl(320, 60%, 50%)",
];

interface Props {
  competitors: Competitor[];
  brands?: BrandMention[];
}

export function ShareOfVoiceChart({ competitors, brands = [] }: Props) {
  const data = buildChartData(competitors, brands);

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Brand Visibility
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            Mention share across AI engines
          </p>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No data available</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Brand Visibility
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          Mention share across AI engines
        </p>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={100}
              innerRadius={50}
              paddingAngle={2}
              label={({ name, value }) =>
                `${name}: ${value.toFixed(1)}%`
              }
              labelLine={true}
            >
              {data.map((entry, i) => (
                <Cell
                  key={entry.name}
                  fill={COLORS[i % COLORS.length]}
                  strokeWidth={entry.isPrimary ? 3 : 1}
                  stroke={entry.isPrimary ? "hsl(220, 90%, 40%)" : "#fff"}
                />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => `${Number(value).toFixed(1)}%`}
            />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

interface SliceEntry {
  name: string;
  value: number;
  isPrimary: boolean;
}

function buildChartData(
  competitors: Competitor[],
  brands: BrandMention[],
): SliceEntry[] {
  // If no brand mentions data, fall back to competitor-only behavior
  if (brands.length === 0) {
    return competitors
      .filter((c) => (c.visibility_score || 0) > 0)
      .map((c) => ({
        name: c.name,
        value: c.visibility_score || 0,
        isPrimary: c.is_primary,
      }))
      .sort((a, b) => b.value - a.value);
  }

  const includedNames = new Set<string>();
  const entries: { name: string; mentions: number; isPrimary: boolean }[] = [];

  // 1. Always include the user's primary brand
  const primary = competitors.find((c) => c.is_primary);
  if (primary) {
    entries.push({
      name: primary.name,
      mentions: primary.brand_mention_count || 0,
      isPrimary: true,
    });
    includedNames.add(primary.name.toLowerCase());
  }

  // 2. Top 3 non-primary competitors by brand_mention_count
  const topCompetitors = competitors
    .filter((c) => !c.is_primary && (c.brand_mention_count || 0) > 0)
    .sort((a, b) => (b.brand_mention_count || 0) - (a.brand_mention_count || 0))
    .slice(0, 3);

  for (const c of topCompetitors) {
    entries.push({
      name: c.name,
      mentions: c.brand_mention_count || 0,
      isPrimary: false,
    });
    includedNames.add(c.name.toLowerCase());
  }

  // 3. Top 3 brand mentions not already included
  const topBrands = brands
    .filter(
      (b) =>
        !b.is_primary &&
        !includedNames.has(b.normalized_name.toLowerCase()) &&
        b.mention_count > 0,
    )
    .sort((a, b) => b.mention_count - a.mention_count)
    .slice(0, 3);

  for (const b of topBrands) {
    entries.push({
      name: b.brand_name,
      mentions: b.mention_count,
      isPrimary: false,
    });
    includedNames.add(b.normalized_name.toLowerCase());
  }

  // Compute share percentages from top entries only (no "Others")
  const totalMentions = entries.reduce((sum, e) => sum + e.mentions, 0);

  if (totalMentions === 0) return [];

  return entries
    .map((e) => ({
      name: e.name,
      value: (e.mentions / totalMentions) * 100,
      isPrimary: e.isPrimary,
    }))
    .sort((a, b) => b.value - a.value);
}
