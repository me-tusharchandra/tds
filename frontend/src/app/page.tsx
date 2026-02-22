"use client";

import { useQuery } from "@tanstack/react-query";
import { Clock } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { BrandInput } from "@/components/brand-input";
import { listAnalyses } from "@/lib/api";

const STATUS_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  completed: "default",
  analyzing: "secondary",
  discovering: "secondary",
  generating_prompts: "secondary",
  querying_engines: "secondary",
  scoring: "secondary",
  pending: "outline",
  failed: "destructive",
};

export default function HomePage() {
  const { data: analyses } = useQuery({
    queryKey: ["analyses"],
    queryFn: listAnalyses,
    refetchInterval: 10_000,
  });

  return (
    <div className="min-h-screen flex flex-col">
      {/* Hero — full center */}
      <main className="flex-1 flex flex-col items-center justify-center px-4">
        <div className="flex flex-col items-center text-center gap-6 -mt-16">
          <div className="space-y-3">
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
              Track your AI search visibility
            </h1>
            <p className="text-xl sm:text-2xl text-muted-foreground">
              If AI can&apos;t find you, you don&apos;t{" "}
              <span className="font-semibold text-foreground">exist</span>
            </p>
          </div>
          <BrandInput />
        </div>
      </main>

      {/* Recent analyses — bottom strip */}
      {analyses && analyses.length > 0 && (
        <footer className="border-t bg-muted/30">
          <div className="container mx-auto px-4 py-6">
            <p className="text-xs text-muted-foreground uppercase tracking-wider mb-3">
              Recent
            </p>
            <div className="flex flex-wrap gap-3">
              {analyses.slice(0, 6).map((a) => (
                <Link key={a.id} href={`/dashboard/${a.id}`}>
                  <div className="flex items-center gap-2 px-3 py-2 rounded-lg border bg-background hover:bg-accent/50 transition-colors text-sm">
                    <span className="font-medium truncate max-w-[180px]">
                      {a.brand_name || a.brand_url}
                    </span>
                    <Badge
                      variant={STATUS_VARIANT[a.status] || "outline"}
                      className="text-[10px] px-1.5 py-0"
                    >
                      {a.status}
                    </Badge>
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {new Date(a.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </footer>
      )}
    </div>
  );
}
