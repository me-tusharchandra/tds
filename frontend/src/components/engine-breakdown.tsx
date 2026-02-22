"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { EngineScore } from "@/lib/types";
import { ENGINE_LABELS } from "@/lib/types";

interface Props {
  engines: EngineScore[];
}

const ENGINE_ICONS: Record<string, string> = {
  openai: "O",
  gemini: "G",
  perplexity: "P",
  exa: "E",
};

export function EngineBreakdown({ engines }: Props) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {engines.map((e) => (
        <Card key={e.engine}>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-sm font-bold">
                {ENGINE_ICONS[e.engine] || e.engine[0].toUpperCase()}
              </div>
              <CardTitle className="text-sm font-medium">
                {ENGINE_LABELS[e.engine] || e.engine}
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-muted-foreground">Visibility</span>
                <span className="font-mono font-medium">
                  {e.visibility_score.toFixed(1)}
                </span>
              </div>
              <Progress value={e.visibility_score} className="h-1.5" />
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Citations</span>
              <span className="font-mono">{e.citation_count}</span>
            </div>
            {e.avg_position && (
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Avg Position</span>
                <span className="font-mono">{e.avg_position.toFixed(1)}</span>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
