"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import type { PromptResult } from "@/lib/types";
import { ENGINE_LABELS } from "@/lib/types";

interface Props {
  prompts: PromptResult[];
}

export function PromptResults({ prompts }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Results by Prompt
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Accordion type="multiple" className="space-y-2">
          {prompts.map((p) => (
            <AccordionItem key={p.prompt_id} value={p.prompt_id}>
              <AccordionTrigger className="text-sm text-left">
                <div className="flex items-center gap-2 flex-1 mr-4">
                  <span className="flex-1">{p.prompt_text}</span>
                  {p.category && (
                    <Badge variant="outline" className="text-xs shrink-0">
                      {p.category}
                    </Badge>
                  )}
                  <Badge variant="secondary" className="text-xs shrink-0">
                    {p.citations.length} citations
                  </Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                {p.citations.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-2">
                    No citations found for this prompt.
                  </p>
                ) : (
                  <div className="space-y-2 pt-2">
                    {p.citations.map((c) => (
                      <div
                        key={c.id}
                        className="flex items-start gap-3 text-sm border rounded-md p-3"
                      >
                        <Badge
                          variant="outline"
                          className="text-xs shrink-0 mt-0.5"
                        >
                          {ENGINE_LABELS[c.engine] || c.engine}
                        </Badge>
                        <div className="flex-1 min-w-0">
                          <a
                            href={c.cited_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-medium hover:underline block truncate"
                          >
                            {c.cited_title || c.cited_url}
                          </a>
                          <p className="text-xs text-muted-foreground">
                            {c.cited_domain}
                          </p>
                          {c.competitor_name && (
                            <Badge
                              variant="secondary"
                              className="text-xs mt-1"
                            >
                              {c.competitor_name}
                            </Badge>
                          )}
                        </div>
                        <span className="font-mono text-xs text-muted-foreground shrink-0">
                          #{c.position}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </CardContent>
    </Card>
  );
}
