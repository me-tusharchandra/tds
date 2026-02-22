"use client";

import { CheckCircle2, XCircle } from "lucide-react";
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
  brandName: string | null;
}

export function TopCitedDomains({ citations, brandName }: Props) {
  // Aggregate citations per domain, tracking which brands are mentioned
  const domainData: Record<
    string,
    {
      count: number;
      engines: Set<string>;
      hasBrand: boolean;
      // brand name -> citation count from this domain (from mentioned_brands + competitor_name)
      brands: Record<string, number>;
    }
  > = {};

  for (const c of citations) {
    const domain = c.cited_domain || "unknown";
    if (!domainData[domain]) {
      domainData[domain] = {
        count: 0,
        engines: new Set(),
        hasBrand: false,
        brands: {},
      };
    }
    const d = domainData[domain];
    d.count += 1;
    d.engines.add(c.engine);

    // Collect brands from mentioned_brands (primary source)
    const mentionedBrands = c.mentioned_brands || [];
    if (mentionedBrands.length > 0) {
      for (const b of mentionedBrands) {
        d.brands[b] = (d.brands[b] || 0) + 1;
        if (brandName && b.toLowerCase() === brandName.toLowerCase()) {
          d.hasBrand = true;
        }
      }
    } else if (c.competitor_name) {
      // Fallback to competitor_name (URL-match) for old data
      d.brands[c.competitor_name] = (d.brands[c.competitor_name] || 0) + 1;
      if (brandName && c.competitor_name === brandName) {
        d.hasBrand = true;
      }
    }
  }

  const data = Object.entries(domainData)
    .map(([domain, d]) => ({
      domain,
      count: d.count,
      engines: Array.from(d.engines).sort(),
      hasBrand: d.hasBrand,
      competitors: Object.entries(d.brands)
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count),
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);

  if (data.length === 0) {
    return null;
  }

  const brandPresent = data.filter((d) => d.hasBrand).length;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Your Brand in Top Cited Sources
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          {brandName ? (
            <>
              <span className="font-medium">{brandName}</span> appears in{" "}
              <span className="font-medium">
                {brandPresent} of {data.length}
              </span>{" "}
              top cited domains
            </>
          ) : (
            "Top domains cited by AI engines across all prompts"
          )}
        </p>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8">#</TableHead>
              <TableHead>Domain</TableHead>
              <TableHead className="text-right">Citations</TableHead>
              <TableHead className="text-center">Engines</TableHead>
              <TableHead>Cited Brands</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((d, i) => (
              <TableRow
                key={d.domain}
                className={d.hasBrand ? "bg-green-50 dark:bg-green-950/20" : ""}
              >
                <TableCell className="text-muted-foreground font-mono">
                  {i + 1}
                </TableCell>
                <TableCell className="font-medium">{d.domain}</TableCell>
                <TableCell className="text-right font-mono">
                  {d.count}
                </TableCell>
                <TableCell className="text-center">
                  <div className="relative group/engines inline-block">
                    <span className="text-xs text-muted-foreground cursor-default">
                      {d.engines.length} engine{d.engines.length !== 1 && "s"}
                    </span>
                    <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1 hidden group-hover/engines:flex flex-wrap gap-1 bg-popover border rounded-md shadow-md p-2 z-10 min-w-max">
                      {d.engines.map((e) => (
                        <Badge key={e} variant="outline" className="text-xs whitespace-nowrap">
                          {ENGINE_LABELS[e] || e}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  {d.competitors.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {d.competitors.map((comp) => (
                        <Badge
                          key={comp.name}
                          variant={
                            brandName && comp.name === brandName
                              ? "default"
                              : "secondary"
                          }
                          className="text-xs"
                        >
                          {comp.name}
                          {comp.count > 1 && (
                            <span className="ml-1 opacity-70">
                              x{comp.count}
                            </span>
                          )}
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <span className="text-xs text-muted-foreground">-</span>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
