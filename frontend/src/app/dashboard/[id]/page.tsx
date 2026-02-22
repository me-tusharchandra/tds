"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Clock, ExternalLink, Loader2 } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

import { VisibilityScoreCard } from "@/components/visibility-score-card";
import { ShareOfVoiceChart } from "@/components/share-of-voice-chart";
import { CompetitorTable } from "@/components/competitor-table";
import { EngineBreakdown } from "@/components/engine-breakdown";
import { CitationSourcesTable } from "@/components/citation-sources-table";
import { PromptResults } from "@/components/prompt-results";
import { HistoryChart } from "@/components/history-chart";
import { TopCitedDomains } from "@/components/top-cited-domains";

import {
  getAnalysisStatus,
  getOverview,
  getCompetitors,
  getCitations,
  getHistory,
  getPromptResults,
} from "@/lib/api";

const STATUS_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  completed: "default",
  analyzing: "secondary",
  discovering: "secondary",
  pending: "outline",
  failed: "destructive",
};

export default function DashboardPage() {
  const params = useParams();
  const id = params.id as string;

  // Poll status until completed
  const { data: status } = useQuery({
    queryKey: ["analysis-status", id],
    queryFn: () => getAnalysisStatus(id),
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === "completed" || s === "failed" ? false : 3000;
    },
  });

  const isComplete = status?.status === "completed";
  const isFailed = status?.status === "failed";

  // Only fetch dashboard data when analysis is complete
  const { data: overview } = useQuery({
    queryKey: ["overview", id],
    queryFn: () => getOverview(id),
    enabled: isComplete,
  });

  const { data: competitorsData } = useQuery({
    queryKey: ["competitors", id],
    queryFn: () => getCompetitors(id),
    enabled: isComplete,
  });

  const { data: citationsData } = useQuery({
    queryKey: ["citations", id],
    queryFn: () => getCitations(id),
    enabled: isComplete,
  });

  const { data: historyData } = useQuery({
    queryKey: ["history", id],
    queryFn: () => getHistory(id),
    enabled: isComplete,
  });

  const { data: promptsData } = useQuery({
    queryKey: ["prompts", id],
    queryFn: () => getPromptResults(id),
    enabled: isComplete,
  });

  // Loading state
  if (!status || (!isComplete && !isFailed)) {
    return (
      <div className="min-h-screen flex flex-col">
        <DashboardHeader brandName={status?.brand_name} status={status?.status} />
        <main className="flex-1 container mx-auto px-4 py-12">
          <div className="flex flex-col items-center justify-center gap-6 py-20">
            <Loader2 className="h-12 w-12 animate-spin text-muted-foreground" />
            <div className="text-center space-y-2">
              <h2 className="text-xl font-semibold">
                {status?.status === "discovering"
                  ? "Discovering competitors..."
                  : status?.status === "analyzing"
                    ? "Analyzing AI search visibility..."
                    : "Starting analysis..."}
              </h2>
              <p className="text-muted-foreground">
                This may take a minute. We&apos;re querying 4 AI search engines.
              </p>
            </div>
            <Badge variant={STATUS_VARIANT[status?.status || "pending"] || "outline"}>
              {status?.status || "pending"}
            </Badge>
          </div>
        </main>
      </div>
    );
  }

  // Error state
  if (isFailed) {
    return (
      <div className="min-h-screen flex flex-col">
        <DashboardHeader brandName={status?.brand_name} status="failed" />
        <main className="flex-1 container mx-auto px-4 py-12">
          <div className="flex flex-col items-center justify-center gap-4 py-20">
            <Badge variant="destructive">Analysis Failed</Badge>
            <p className="text-muted-foreground">
              Something went wrong. Please try again.
            </p>
            <Link href="/">
              <Button>Back to Home</Button>
            </Link>
          </div>
        </main>
      </div>
    );
  }

  // Dashboard
  const competitors = competitorsData?.competitors || [];
  const citations = citationsData?.citations || [];
  const history = historyData?.entries || [];
  const prompts = promptsData?.prompts || [];

  return (
    <div className="min-h-screen flex flex-col">
      <DashboardHeader
        brandName={overview?.brand_name}
        brandUrl={overview?.brand_url}
        status="completed"
      />

      <main className="flex-1 container mx-auto px-4 py-8">
        {/* Score cards row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <VisibilityScoreCard
            score={overview?.overall_visibility || 0}
            label="Overall Visibility"
            subtitle={`Across ${overview?.engines.length || 0} engines`}
          />
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Share of Voice</p>
              <p className="text-4xl font-bold mt-1">
                {(overview?.overall_sov || 0).toFixed(1)}%
              </p>
              <p className="text-xs text-muted-foreground mt-2">
                Among {overview?.competitor_count || 0} competitors
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Total Citations</p>
              <p className="text-4xl font-bold mt-1">
                {overview?.total_citations || 0}
              </p>
              <p className="text-xs text-muted-foreground mt-2">
                From {overview?.prompt_count || 0} search prompts
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Competitors Found</p>
              <p className="text-4xl font-bold mt-1">
                {overview?.competitor_count || 0}
              </p>
              <p className="text-xs text-muted-foreground mt-2">
                Discovered via Exa AI
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Engine breakdown */}
        <div className="mb-8">
          <h3 className="text-lg font-semibold mb-4">Engine Breakdown</h3>
          <EngineBreakdown engines={overview?.engines || []} />
        </div>

        {/* Tabbed content */}
        <Tabs defaultValue="competitors" className="space-y-6">
          <TabsList>
            <TabsTrigger value="competitors">Competitors</TabsTrigger>
            <TabsTrigger value="citations">Citations</TabsTrigger>
            <TabsTrigger value="prompts">Prompts</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>

          <TabsContent value="competitors" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <CompetitorTable competitors={competitors} />
              </div>
              <ShareOfVoiceChart competitors={competitors} />
            </div>
          </TabsContent>

          <TabsContent value="citations" className="space-y-6">
            <TopCitedDomains citations={citations} />
            <CitationSourcesTable
              citations={citations}
              total={citationsData?.total || 0}
            />
          </TabsContent>

          <TabsContent value="prompts">
            <PromptResults prompts={prompts} />
          </TabsContent>

          <TabsContent value="history">
            <HistoryChart entries={history} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}

function DashboardHeader({
  brandName,
  brandUrl,
  status,
}: {
  brandName?: string | null;
  brandUrl?: string;
  status?: string;
}) {
  return (
    <header className="border-b">
      <div className="container mx-auto px-4 py-4 flex items-center gap-4">
        <Link href="/">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
        </Link>
        <Separator orientation="vertical" className="h-6" />
        <div className="flex-1">
          <h1 className="text-lg font-semibold">
            {brandName || "Analysis"}
          </h1>
          {brandUrl && (
            <a
              href={brandUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-muted-foreground hover:underline flex items-center gap-1"
            >
              {brandUrl}
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
        {status && (
          <Badge variant={STATUS_VARIANT[status] || "outline"}>
            {status}
          </Badge>
        )}
      </div>
    </header>
  );
}
