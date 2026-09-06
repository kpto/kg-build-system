"use client";

/**
 * Staleness banner for a compiled artifact.
 *
 * The plan is the output of a compile pass; if the project's generation state is
 * anything but `clean`, what is on screen may no longer be what the framework would
 * produce. The banner says so in those terms and offers the one fix — recompile —
 * which is `GET /api/plan?refresh=1`.
 */

import { Button, Chip } from "@/components/ui";
import type { Staleness } from "./filters";

export interface StaleBannerProps {
  readonly stale: Staleness;
  readonly refreshing: boolean;
  readonly errors: number;
  readonly onRefresh: () => void;
}

export function StaleBanner({ stale, refreshing, errors, onRefresh }: StaleBannerProps) {
  if (stale.level === "fresh") return null;

  const stalePlan = stale.level === "stale";
  return (
    <div
      role="status"
      data-plan-stale={stalePlan ? "true" : "false"}
      className="flex shrink-0 flex-wrap items-center gap-2 border-b border-edge bg-warn/10 px-2.5 py-1.5 text-[12px]"
    >
      <span className={stalePlan ? "text-warn" : "text-muted"}>
        {stale.message ?? "This plan has no generation state behind it."}
      </span>
      <Chip tone="neutral" title="status.generation.state">
        generation: {stale.state}
      </Chip>
      {errors > 0 && (
        <Chip tone="danger" title="the compile pass reported errors">
          {errors} compile error{errors === 1 ? "" : "s"}
        </Chip>
      )}
      <Button
        size="sm"
        variant="primary"
        className="ml-auto"
        disabled={refreshing}
        onClick={onRefresh}
        title="GET /api/plan?refresh=1 — re-run the compile pass and redraw"
      >
        {refreshing ? "recompiling…" : "recompile"}
      </Button>
    </div>
  );
}
