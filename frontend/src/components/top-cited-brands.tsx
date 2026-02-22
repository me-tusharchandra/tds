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
import type { TopCitedBrand } from "@/lib/types";
import { ENGINE_LABELS } from "@/lib/types";

interface Props {
  brands: TopCitedBrand[];
}

export function TopCitedBrandsTable({ brands }: Props) {
  if (brands.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Top Cited Brands (from AI responses)
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          Brands most frequently referenced by AI engines across all prompts
        </p>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8">#</TableHead>
              <TableHead>Domain</TableHead>
              <TableHead className="text-right">Citations</TableHead>
              <TableHead className="text-right">Avg Position</TableHead>
              <TableHead>Engines</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {brands.map((b, i) => (
              <TableRow
                key={b.domain}
                className={b.is_primary ? "bg-primary/5 font-medium" : ""}
              >
                <TableCell className="text-muted-foreground font-mono">
                  {i + 1}
                </TableCell>
                <TableCell>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="font-medium">{b.domain}</span>
                      {b.is_primary && (
                        <Badge variant="secondary" className="text-xs">
                          Your Brand
                        </Badge>
                      )}
                      {b.sample_urls[0] && (
                        <a
                          href={b.sample_urls[0]}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-muted-foreground hover:text-foreground"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>
                    {b.sample_title && (
                      <p className="text-xs text-muted-foreground truncate max-w-xs">
                        {b.sample_title}
                      </p>
                    )}
                  </div>
                </TableCell>
                <TableCell className="text-right font-mono font-medium">
                  {b.citation_count}
                </TableCell>
                <TableCell className="text-right font-mono">
                  {b.avg_position?.toFixed(1) || "-"}
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
