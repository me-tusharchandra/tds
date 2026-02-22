"use client";

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
import type { BrandMention } from "@/lib/types";
import { ENGINE_LABELS } from "@/lib/types";

interface Props {
  brands: BrandMention[];
  total: number;
  limit?: number;
}

export function BrandMentionsTable({ brands, total, limit }: Props) {
  // When limit is set, show top N but always include the primary brand
  let display = brands;
  if (limit && brands.length > limit) {
    const top = brands.slice(0, limit);
    const primaryInTop = top.some((b) => b.is_primary);
    if (!primaryInTop) {
      const primary = brands.find((b) => b.is_primary);
      if (primary) {
        display = [...top, primary];
      } else {
        display = top;
      }
    } else {
      display = top;
    }
  }

  if (display.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Brand Mentions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No brand mentions found. This data is available for new analyses.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Brand Mentions ({total})
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          Brands recommended by AI engines in their responses, ranked by
          frequency
        </p>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8">#</TableHead>
              <TableHead>Brand</TableHead>
              <TableHead className="text-right">Mentions</TableHead>
              <TableHead className="text-right">Avg Position</TableHead>
              <TableHead className="text-right">Presence</TableHead>
              <TableHead>Engines</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {display.map((b, i) => (
              <TableRow
                key={b.normalized_name}
                className={b.is_primary ? "bg-primary/5 font-medium" : ""}
              >
                <TableCell className="text-muted-foreground font-mono">
                  {i + 1}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1.5">
                    <span className="font-medium">{b.brand_name}</span>
                    {b.is_primary && (
                      <Badge variant="secondary" className="text-xs">
                        Your Brand
                      </Badge>
                    )}
                    {b.competitor_name &&
                      b.competitor_name !== b.brand_name && (
                        <span className="text-xs text-muted-foreground">
                          ({b.competitor_name})
                        </span>
                      )}
                  </div>
                  {b.sample_contexts.length > 0 && (
                    <p className="text-xs text-muted-foreground truncate max-w-xs">
                      {b.sample_contexts[0]}
                    </p>
                  )}
                </TableCell>
                <TableCell className="text-right font-mono font-medium">
                  {b.mention_count}
                </TableCell>
                <TableCell className="text-right font-mono">
                  {b.avg_position?.toFixed(1) || "-"}
                </TableCell>
                <TableCell className="text-right font-mono">
                  {b.presence_rate != null ? `${b.presence_rate}%` : "-"}
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {b.engines.map((e) => (
                      <Badge key={e} variant="outline" className="text-xs">
                        {ENGINE_LABELS[e] || e}
                      </Badge>
                    ))}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
