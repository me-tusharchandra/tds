"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Citation } from "@/lib/types";
import { ENGINE_LABELS } from "@/lib/types";

interface Props {
  citations: Citation[];
  total: number;
  brandName?: string | null;
}

const PAGE_SIZE = 25;

const ENGINE_BADGE_VARIANT: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  openai: "default",
  gemini: "secondary",
  perplexity: "outline",
  exa: "secondary",
};

export function CitationSourcesTable({ citations, total, brandName }: Props) {
  const [page, setPage] = useState(0);
  const totalPages = Math.ceil(citations.length / PAGE_SIZE);
  const start = page * PAGE_SIZE;
  const paginated = citations.slice(start, start + PAGE_SIZE);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Citation Sources
          </CardTitle>
          <Badge variant="outline">{total} total</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Engine</TableHead>
              <TableHead>Source</TableHead>
              <TableHead>Mentioned Brands</TableHead>
              <TableHead className="text-right">Position</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {paginated.map((c) => (
              <TableRow key={c.id}>
                <TableCell>
                  <Badge variant={ENGINE_BADGE_VARIANT[c.engine] || "outline"}>
                    {ENGINE_LABELS[c.engine] || c.engine}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="max-w-md">
                    <a
                      href={c.cited_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-medium hover:underline flex items-center gap-1"
                    >
                      {c.cited_title || c.cited_domain || c.cited_url}
                      <ExternalLink className="h-3 w-3 shrink-0" />
                    </a>
                    <p className="text-xs text-muted-foreground truncate">
                      {c.cited_domain}
                    </p>
                    {c.snippet && (
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                        {c.snippet}
                      </p>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  {(c.mentioned_brands?.length > 0) ? (
                    <div className="flex flex-wrap gap-1">
                      {c.mentioned_brands.slice(0, 3).map((b) => (
                        <Badge
                          key={b}
                          variant={brandName && b.toLowerCase() === brandName.toLowerCase() ? "default" : "secondary"}
                          className="text-xs"
                        >
                          {b}
                        </Badge>
                      ))}
                      {c.mentioned_brands.length > 3 && (
                        <Badge variant="outline" className="text-xs">
                          +{c.mentioned_brands.length - 3} more
                        </Badge>
                      )}
                    </div>
                  ) : c.competitor_name ? (
                    <Badge variant="secondary" className="text-xs">{c.competitor_name}</Badge>
                  ) : (
                    <span className="text-xs text-muted-foreground">-</span>
                  )}
                </TableCell>
                <TableCell className="text-right font-mono">
                  {c.position || "-"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4">
            <p className="text-xs text-muted-foreground">
              Showing {start + 1}–{Math.min(start + PAGE_SIZE, citations.length)} of {citations.length} citations
            </p>
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              {Array.from({ length: totalPages }, (_, i) => (
                <Button
                  key={i}
                  variant={i === page ? "default" : "outline"}
                  size="sm"
                  className="w-8"
                  onClick={() => setPage(i)}
                >
                  {i + 1}
                </Button>
              ))}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page === totalPages - 1}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
