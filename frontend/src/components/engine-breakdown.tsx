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

const SKIP_REASONS: Record<string, string> = {
  perplexity: "No credit — paid API only",
  openai: "No API key configured",
  gemini: "No API key configured",
  exa: "No API key configured",
};

export function EngineBreakdown({ engines }: Props) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {engines.map((e) => {
        const skipped = e.status === "skipped";
        return (
          <Card
            key={e.engine}
            className={skipped ? "opacity-60 border-dashed" : undefined}
          >
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div
                    className={
                      "h-8 w-8 rounded-full flex items-center justify-center text-sm font-bold " +
                      (skipped ? "bg-muted" : "bg-primary/10")
                    }
                  >
                    {ENGINE_ICONS[e.engine] || e.engine[0].toUpperCase()}
                  </div>
                  <CardTitle className="text-sm font-medium">
                    {ENGINE_LABELS[e.engine] || e.engine}
                  </CardTitle>
                </div>
                {skipped && (
                  <span className="text-[10px] uppercase tracking-wide font-medium text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                    Skipped
                  </span>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {skipped ? (
                <p className="text-xs text-muted-foreground py-2">
                  {SKIP_REASONS[e.engine] || "Engine did not run for this analysis."}
                </p>
              ) : (
                <>
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
                      <span className="font-mono">
                        {e.avg_position.toFixed(1)}
                      </span>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
