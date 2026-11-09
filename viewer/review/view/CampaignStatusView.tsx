"use client";

import type { CampaignCounts } from "@/shared/model/campaign";
import type { CampaignStatusModel } from "@/review/model/CampaignModel";

interface CampaignStatusViewProps {
  model: CampaignStatusModel;
}

const COUNT_ORDER: Array<[keyof CampaignCounts, string]> = [
  ["assets", "assets"],
  ["tables", "tables"],
  ["projections", "projections"],
  ["nodes", "nodes"],
  ["edges", "edges"],
  ["bindings", "bindings"],
  ["steps", "steps"],
  ["connections", "connections"],
];

/**
 * Window status: campaign counts, review progress, score, impact and build mode.
 *
 * Every value is read from the injected status model; the view formats it.
 */
export function CampaignStatusView({ model }: CampaignStatusViewProps) {
  const { build } = model;
  return (
    <footer
      data-testid="status-bar"
      data-level="status"
      className="flex h-7 shrink-0 items-center gap-3 overflow-hidden border-t border-line-soft bg-inset px-3 font-mono text-[10px] text-faint"
    >
      {COUNT_ORDER.map(([key, label]) => (
        <span key={key} className="flex shrink-0 items-center gap-1 whitespace-nowrap">
          <span className="font-mono text-muted">{model.counts[key]}</span>
          {label}
        </span>
      ))}
      <span className="flex shrink-0 items-center gap-1 whitespace-nowrap">
        <span className="font-mono text-muted">
          {model.review.resolved}/{model.review.total}
        </span>
        review
      </span>
      {model.score !== undefined ? (
        <span className="flex shrink-0 items-center gap-1 whitespace-nowrap">
          score <span className="font-mono text-accent">{Math.round(model.score)}</span>
        </span>
      ) : null}
      {model.impact ? (
        <span className="flex shrink-0 items-center gap-1 whitespace-nowrap">
          impact <span className="font-mono text-muted">{model.impact}</span>
        </span>
      ) : null}
      <span
        className={`ml-auto min-w-0 truncate text-right font-mono ${build.failures > 0 ? "text-critical" : "text-faint"}`}
      >
        {build.failures > 0
          ? `${build.failures} build failure(s)`
          : build.compileOnly
            ? "compile only · not executed"
            : "build healthy"}
        {build.metaComponents
          ? ` · meta-graph ${build.metaComponents} components`
          : ""}
      </span>
    </footer>
  );
}
