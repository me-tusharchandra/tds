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
import type { Competitor } from "@/lib/types";

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
}

export function ShareOfVoiceChart({ competitors }: Props) {
  const data = competitors
    .filter((c) => (c.share_of_voice || 0) > 0)
    .map((c) => ({
      name: c.name,
      value: c.share_of_voice || 0,
      isPrimary: c.is_primary,
    }))
    .sort((a, b) => b.value - a.value);

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Share of Voice
          </CardTitle>
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
          Share of Voice
        </CardTitle>
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
