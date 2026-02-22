"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createAnalysis } from "@/lib/api";

export function BrandInput() {
  const [url, setUrl] = useState("");
  const router = useRouter();

  const mutation = useMutation({
    mutationFn: (brandUrl: string) => createAnalysis(brandUrl),
    onSuccess: (data) => {
      router.push(`/dashboard/${data.id}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    let normalizedUrl = url.trim();
    if (
      !normalizedUrl.startsWith("http://") &&
      !normalizedUrl.startsWith("https://")
    ) {
      normalizedUrl = `https://${normalizedUrl}`;
    }

    mutation.mutate(normalizedUrl);
  };

  return (
    <form onSubmit={handleSubmit} className="flex w-full max-w-xl gap-3">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="text"
          placeholder="Enter your brand URL (e.g., notion.so)"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="pl-10 h-12"
          disabled={mutation.isPending}
        />
      </div>
      <Button type="submit" size="lg" disabled={mutation.isPending || !url.trim()}>
        {mutation.isPending ? "Starting..." : "Analyze"}
      </Button>
    </form>
  );
}
