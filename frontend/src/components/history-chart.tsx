"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { HistoryEntry } from "@/lib/types";

interface Props {
  entries: HistoryEntry[];
}

export function HistoryChart({ entries }: Props) {
  if (entries.length < 2) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Visibility History
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Run multiple analyses to see trends over time.
          </p>
        </CardContent>
      </Card>
    );
  }

  const data = entries.map((e) => ({
    date: new Date(e.created_at).toLocaleDateString(),
    visibility: e.visibility_score,
    sov: e.share_of_voice,
    citations: e.citation_count,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Visibility History
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="date" className="text-xs" />
            <YAxis domain={[0, 100]} className="text-xs" />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="visibility"
              stroke="hsl(220, 90%, 56%)"
              strokeWidth={2}
              name="Visibility Score"
              dot={{ fill: "hsl(220, 90%, 56%)" }}
            />
            <Line
              type="monotone"
              dataKey="sov"
              stroke="hsl(160, 60%, 45%)"
              strokeWidth={2}
              name="Share of Voice"
              dot={{ fill: "hsl(160, 60%, 45%)" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
