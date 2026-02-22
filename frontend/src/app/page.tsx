"use client";

import { useQuery } from "@tanstack/react-query";
import { Clock, ExternalLink } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { BrandInput } from "@/components/brand-input";
import { listAnalyses } from "@/lib/api";

const STATUS_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  completed: "default",
  analyzing: "secondary",
  discovering: "secondary",
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
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold tracking-tight">TDS</h1>
          <span className="text-sm text-muted-foreground">
            AI Search Visibility Analytics
          </span>
        </div>
      </header>

      {/* Hero */}
      <main className="flex-1 container mx-auto px-4 py-16">
        <div className="flex flex-col items-center text-center gap-8 mb-16">
          <div className="space-y-4 max-w-2xl">
            <h2 className="text-4xl font-bold tracking-tight sm:text-5xl">
              How visible is your brand in AI search?
            </h2>
            <p className="text-lg text-muted-foreground">
              Discover how AI engines like ChatGPT, Gemini, Perplexity, and Exa
              reference your brand. Get visibility scores, competitor analysis,
              and citation tracking.
            </p>
          </div>
          <BrandInput />
        </div>

        {/* Recent Analyses */}
        {analyses && analyses.length > 0 && (
          <div className="max-w-3xl mx-auto">
            <h3 className="text-lg font-semibold mb-4">Recent Analyses</h3>
            <div className="grid gap-3">
              {analyses.map((a) => (
                <Link key={a.id} href={`/dashboard/${a.id}`}>
                  <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
                    <CardContent className="flex items-center justify-between py-4">
                      <div className="flex items-center gap-3">
                        <ExternalLink className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="font-medium">
                            {a.brand_name || a.brand_url}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {a.brand_url}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge variant={STATUS_VARIANT[a.status] || "outline"}>
                          {a.status}
                        </Badge>
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {new Date(a.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
