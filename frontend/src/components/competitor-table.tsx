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
import type { Competitor } from "@/lib/types";
import { ENGINE_LABELS } from "@/lib/types";

interface Props {
  competitors: Competitor[];
}

export function CompetitorTable({ competitors }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Competitor Rankings
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8">#</TableHead>
              <TableHead>Brand</TableHead>
              <TableHead className="text-right">Visibility</TableHead>
              <TableHead className="text-right">SOV</TableHead>
              <TableHead className="text-right">Citations</TableHead>
              <TableHead className="text-right">Avg Position</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {competitors.map((c, i) => (
              <TableRow
                key={c.id}
                className={c.is_primary ? "bg-primary/5 font-medium" : ""}
              >
                <TableCell className="text-muted-foreground">
                  {i + 1}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <span>{c.name}</span>
                    {c.is_primary && (
                      <Badge variant="secondary" className="text-xs">
                        Your Brand
                      </Badge>
                    )}
                    {c.url && (
                      <a
                        href={c.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-muted-foreground hover:text-foreground"
                      >
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                  {c.domain && (
                    <span className="text-xs text-muted-foreground">
                      {c.domain}
                    </span>
                  )}
                </TableCell>
                <TableCell className="text-right">
                  <span className="font-mono">
                    {(c.visibility_score || 0).toFixed(1)}
                  </span>
                </TableCell>
                <TableCell className="text-right">
                  {(c.share_of_voice || 0).toFixed(1)}%
                </TableCell>
                <TableCell className="text-right">
                  {c.citation_count || 0}
                </TableCell>
                <TableCell className="text-right">
                  {c.avg_position ? c.avg_position.toFixed(1) : "-"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
