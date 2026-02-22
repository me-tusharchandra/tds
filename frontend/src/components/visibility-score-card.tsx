"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

interface Props {
  score: number;
  label?: string;
  subtitle?: string;
}

function getScoreColor(score: number) {
  if (score >= 70) return "text-green-600";
  if (score >= 40) return "text-yellow-600";
  return "text-red-500";
}

export function VisibilityScoreCard({ score, label = "Visibility Score", subtitle }: Props) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-2">
          <span className={`text-4xl font-bold ${getScoreColor(score)}`}>
            {score.toFixed(1)}
          </span>
          <span className="text-muted-foreground text-sm">/100</span>
        </div>
        <Progress value={score} className="mt-3 h-2" />
        {subtitle && (
          <p className="text-xs text-muted-foreground mt-2">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
}
