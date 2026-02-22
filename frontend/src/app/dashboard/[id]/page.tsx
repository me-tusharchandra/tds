"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Check,
  Circle,
  ExternalLink,
  Loader2,
  RefreshCw,
} from "lucide-react";
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
import { BrandMentionsTable } from "@/components/brand-mentions-table";
import { EngineBreakdown } from "@/components/engine-breakdown";
import { CitationSourcesTable } from "@/components/citation-sources-table";
import { PromptResults } from "@/components/prompt-results";
import { HistoryChart } from "@/components/history-chart";
import { TopCitedDomains } from "@/components/top-cited-domains";

import {
  createAnalysis,
  getAnalysisStatus,
  getOverview,
  getCompetitors,
  getCitations,
  getHistory,
  getPromptResults,
  getBrandMentions,
} from "@/lib/api";

import type { AnalysisProgress } from "@/lib/types";
import { ENGINE_LABELS } from "@/lib/types";

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

/** Ordered pipeline steps mapped to the status that activates them. */
const PIPELINE_STEPS = [
  { key: "discovering", label: "Discovering competitors" },
  { key: "generating_prompts", label: "Generating search prompts" },
  { key: "querying_engines", label: "Querying AI engines" },
  { key: "scoring", label: "Processing results & scoring" },
] as const;

const STATUS_ORDER: Record<string, number> = {
  pending: 0,
  discovering: 1,
  generating_prompts: 2,
  querying_engines: 3,
  scoring: 4,
  completed: 5,
  failed: 5,
};

type StepState = "pending" | "in_progress" | "completed";

function getStepState(stepKey: string, currentStatus: string): StepState {
  const stepIdx = STATUS_ORDER[stepKey] ?? 0;
  const currentIdx = STATUS_ORDER[currentStatus] ?? 0;
  if (currentIdx > stepIdx) return "completed";
  if (currentIdx === stepIdx) return "in_progress";
  return "pending";
}

function StepIcon({ state }: { state: StepState }) {
  if (state === "completed")
    return <Check className="h-5 w-5 text-green-500" />;
  if (state === "in_progress")
    return <Loader2 className="h-5 w-5 animate-spin text-primary" />;
  return <Circle className="h-5 w-5 text-muted-foreground/40" />;
}

function StepDetail({
  stepKey,
  state,
  progress,
}: {
  stepKey: string;
  state: StepState;
  progress: AnalysisProgress | null | undefined;
}) {
  if (!progress) return null;

  if (stepKey === "discovering" && state === "completed" && progress.competitors_found != null) {
    return (
      <p className="ml-8 text-xs text-muted-foreground">
        Found {progress.competitors_found} competitors
      </p>
    );
  }

  if (stepKey === "generating_prompts" && state === "completed" && progress.prompts_generated != null) {
    return (
      <p className="ml-8 text-xs text-muted-foreground">
        {progress.prompts_generated} prompts generated
      </p>
    );
  }

  if (stepKey === "scoring" && state === "completed") {
    const parts: string[] = [];
    if (progress.citations_found != null) parts.push(`${progress.citations_found} citations`);
    if (progress.brands_found != null) parts.push(`${progress.brands_found} brand mentions`);
    if (parts.length > 0) {
      return (
        <p className="ml-8 text-xs text-muted-foreground">{parts.join(", ")}</p>
      );
    }
  }

  return null;
}

function EngineSubRows({
  state,
  progress,
}: {
  state: StepState;
  progress: AnalysisProgress | null | undefined;
}) {
  if (state === "pending" || !progress?.engines) return null;

  return (
    <div className="ml-8 mt-1 space-y-1">
      {Object.entries(progress.engines).map(([engine, counts]) => {
        const label = ENGINE_LABELS[engine] || engine;
        const done = counts.completed >= counts.total;
        return (
          <div key={engine} className="flex items-center gap-2 text-sm">
            {done ? (
              <Check className="h-3.5 w-3.5 text-green-500" />
            ) : state === "in_progress" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
            ) : (
              <Check className="h-3.5 w-3.5 text-green-500" />
            )}
            <span className={done || state === "completed" ? "text-muted-foreground" : ""}>
              {label}
            </span>
            <span className="text-xs text-muted-foreground">
              {counts.completed}/{counts.total}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function DashboardPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const [isRegenerating, setIsRegenerating] = useState(false);

  async function handleRegenerate() {
    const brandUrl = overview?.brand_url;
    if (!brandUrl) return;
    setIsRegenerating(true);
    try {
      const result = await createAnalysis(brandUrl);
      router.push(`/dashboard/${result.id}`);
    } catch {
      setIsRegenerating(false);
    }
  }

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

  const { data: brandMentionsData } = useQuery({
    queryKey: ["brand-mentions", id],
    queryFn: () => getBrandMentions(id),
    enabled: isComplete,
  });

  // Loading state — step-by-step progress panel
  if (!status || (!isComplete && !isFailed)) {
    const currentStatus = status?.status || "pending";
    const progress = status?.progress ?? null;

    return (
      <div className="min-h-screen flex flex-col">
        <DashboardHeader brandName={status?.brand_name} status={currentStatus} />
        <main className="flex-1 container mx-auto px-4 py-12">
          <div className="flex flex-col items-center justify-center gap-8 py-12">
            <div className="text-center space-y-2">
              <h2 className="text-xl font-semibold">Analyzing AI search visibility</h2>
              <p className="text-muted-foreground">
                This may take a minute. We&apos;re querying 4 AI search engines.
              </p>
            </div>

            <Card className="w-full max-w-md">
              <CardContent className="pt-6 space-y-4">
                {PIPELINE_STEPS.map((step) => {
                  const state = getStepState(step.key, currentStatus);
                  return (
                    <div key={step.key}>
                      <div className="flex items-center gap-3">
                        <StepIcon state={state} />
                        <span
                          className={
                            state === "pending"
                              ? "text-muted-foreground"
                              : state === "in_progress"
                                ? "font-medium"
                                : ""
                          }
                        >
                          {step.label}
                        </span>
                      </div>
                      <StepDetail stepKey={step.key} state={state} progress={progress} />
                      {step.key === "querying_engines" && (
                        <EngineSubRows state={state} progress={progress} />
                      )}
                    </div>
                  );
                })}
              </CardContent>
            </Card>

            <Badge variant={STATUS_VARIANT[currentStatus] || "outline"}>
              {currentStatus.replace(/_/g, " ")}
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
        onRegenerate={handleRegenerate}
        isRegenerating={isRegenerating}
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
              <p className="text-sm text-muted-foreground">Brand Visibility</p>
              <p className="text-4xl font-bold mt-1">
                {(overview?.overall_visibility || 0).toFixed(1)}%
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

        {/* Tabbed content */}
        <Tabs defaultValue="competitors" className="space-y-6">
          <TabsList>
            <TabsTrigger value="competitors">Competitors</TabsTrigger>
            <TabsTrigger value="brands">Brands</TabsTrigger>
            <TabsTrigger value="engines">Engines</TabsTrigger>
            <TabsTrigger value="citations">Citations</TabsTrigger>
            <TabsTrigger value="prompts">Prompts</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>

          <TabsContent value="competitors" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <CompetitorTable competitors={competitors} />
              </div>
              <ShareOfVoiceChart competitors={competitors} brands={brandMentionsData?.brands || []} />
            </div>
            <BrandMentionsTable
              brands={brandMentionsData?.brands || []}
              total={brandMentionsData?.total || 0}
              limit={5}
            />
          </TabsContent>

          <TabsContent value="brands">
            <BrandMentionsTable
              brands={brandMentionsData?.brands || []}
              total={brandMentionsData?.total || 0}
            />
          </TabsContent>

          <TabsContent value="engines">
            <EngineBreakdown engines={overview?.engines || []} />
          </TabsContent>

          <TabsContent value="citations" className="space-y-6">
            <TopCitedDomains citations={citations} brandName={overview?.brand_name || null} />
            <CitationSourcesTable
              citations={citations}
              total={citationsData?.total || 0}
              brandName={overview?.brand_name || null}
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
  onRegenerate,
  isRegenerating,
}: {
  brandName?: string | null;
  brandUrl?: string;
  status?: string;
  onRegenerate?: () => void;
  isRegenerating?: boolean;
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
        <div className="flex items-center gap-2">
          {status === "completed" && onRegenerate && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRegenerate}
              disabled={isRegenerating}
            >
              {isRegenerating ? (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-1" />
              )}
              Re-analyze
            </Button>
          )}
          {status && (
            <Badge variant={STATUS_VARIANT[status] || "outline"}>
              {status}
            </Badge>
          )}
        </div>
      </div>
    </header>
  );
}
