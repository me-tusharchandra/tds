"use client";

import { ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
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
}

const ENGINE_BADGE_VARIANT: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  openai: "default",
  gemini: "secondary",
  perplexity: "outline",
  exa: "secondary",
};

export function CitationSourcesTable({ citations, total }: Props) {
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
              <TableHead>Matched Brand</TableHead>
              <TableHead className="text-right">Position</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {citations.slice(0, 50).map((c) => (
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
                  {c.competitor_name ? (
                    <Badge variant="secondary">{c.competitor_name}</Badge>
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
        {total > 50 && (
          <p className="text-xs text-muted-foreground mt-3 text-center">
            Showing 50 of {total} citations
          </p>
        )}
      </CardContent>
    </Card>
  );
}
