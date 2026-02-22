"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Citation } from "@/lib/types";

interface Props {
  citations: Citation[];
}

export function TopCitedDomains({ citations }: Props) {
  // Count citations per domain
  const domainCounts: Record<string, number> = {};
  for (const c of citations) {
    const domain = c.cited_domain || "unknown";
    domainCounts[domain] = (domainCounts[domain] || 0) + 1;
  }

  const data = Object.entries(domainCounts)
    .map(([domain, count]) => ({ domain, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 15);

  if (data.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Top Cited Domains
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={Math.max(300, data.length * 32)}>
          <BarChart data={data} layout="vertical" margin={{ left: 120 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis type="number" className="text-xs" />
            <YAxis
              type="category"
              dataKey="domain"
              width={110}
              className="text-xs"
              tick={{ fontSize: 11 }}
            />
            <Tooltip />
            <Bar
              dataKey="count"
              fill="hsl(220, 90%, 56%)"
              radius={[0, 4, 4, 0]}
              name="Citations"
            />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
