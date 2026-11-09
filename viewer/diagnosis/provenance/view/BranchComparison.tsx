"use client";

import type { ReactNode } from "react";
import { cx } from "@/shared/ui/theme";
import type {
  ProvenanceBranchComparisonModel,
  ProvenanceBranchModel,
} from "@/diagnosis/provenance/model/ProvenanceModel";
import { ExpressionSyntax } from "@/diagnosis/provenance/view/ExpressionSyntax";

function CompareField({
  label,
  tone,
  children,
}: {
  label: string;
  tone: string;
  children: ReactNode;
}) {
  return (
    <div data-level="field" className="ui-field min-w-0">
      <span className={cx("ui-field-label", tone)}>{label}</span>
      <span className="ui-field-value min-w-0">{children}</span>
    </div>
  );
}

function LegendDot({ tone }: { tone: string }) {
  const color =
    tone === "source"
      ? "bg-source"
      : tone === "asset"
        ? "bg-asset"
        : tone === "accent"
          ? "bg-accent"
          : tone === "transform"
            ? "bg-transform"
            : "bg-target";
  return <span className={`size-1.5 rounded-full ${color}`} aria-hidden />;
}

function BranchColumn({ branch }: { branch: ProvenanceBranchModel }) {
  return (
    <div data-testid={`branch-${branch.index}`} className="min-w-0">
      <div className="ui-row" data-level="row">
        <span className="ui-section-count shrink-0">{branch.ordinal}</span>
        <span className="ui-section-title shrink-0">branch</span>
        <span className="ui-chip ml-auto shrink-0 border-accent/40 bg-accent/10 tnum font-mono text-[9px] text-accent">
          #{branch.bindingIndex}
        </span>
      </div>

      <CompareField label="source" tone="text-source">
        {branch.source.value}
      </CompareField>
      <CompareField label="asset" tone="text-asset">
        {branch.asset.value}
      </CompareField>
      <CompareField label="binding" tone="text-accent">
        {branch.binding.value}
      </CompareField>
      <CompareField label="identity" tone="text-transform">
        <span className="break-all text-muted">{branch.identity.value}</span>
      </CompareField>
      <CompareField label="field map" tone="text-source">
        <span className="text-text">{branch.fieldMap.value}</span>
        <span className="mt-0.5 block break-words text-faint">
          <ExpressionSyntax
            expression={branch.expression}
            className="font-mono"
          />
        </span>
      </CompareField>
      <CompareField label="target" tone="text-target">
        {branch.targets.length ? (
          <span className="flex flex-wrap gap-1">
            {branch.targets.map((target) => (
              <span
                key={target}
                className="ui-chip whitespace-normal break-all font-mono text-[9px] text-target"
              >
                {target}
              </span>
            ))}
          </span>
        ) : (
          <span className="text-faint">{branch.targetFallback}</span>
        )}
      </CompareField>
    </div>
  );
}

export interface BranchComparisonProps {
  model: ProvenanceBranchComparisonModel;
}

/**
 * Side-by-side comparison of the blueprint branches that feed one property.
 *
 * This is a row group inside the Lineage inspector section, not a pair of
 * cards: each branch is a subject row followed by inset fields for source,
 * asset, binding, identity, field mapping and target. The branch columns are
 * separated by a 1px rule, never by elevation.
 */
export function BranchComparison({ model }: BranchComparisonProps) {
  return (
    <div
      data-level="section"
      role="region"
      aria-label={model.question}
      className="min-w-0 border-b border-line-soft last:border-b-0"
    >
      <div className="ui-section-header border-b border-line-soft bg-panel">
        <h3 className="ui-section-title shrink-0">{model.title}</h3>
        <span className="ui-row-meta hidden min-w-0 truncate sm:inline">
          {model.meta}
        </span>
        <span className="ui-section-count ml-auto shrink-0">
          {model.countLabel}
        </span>
      </div>

      <div
        data-testid="branch-comparison-legend"
        className="ui-row-meta flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-line-soft px-2 py-1"
      >
        {model.legend.map((entry) => (
          <span key={entry.id} className="inline-flex items-center gap-1">
            <LegendDot tone={entry.tone} /> {entry.label}
          </span>
        ))}
      </div>

      <div
        data-testid="branch-comparison"
        className="grid divide-y divide-line-soft md:grid-cols-2 md:divide-x md:divide-y-0"
      >
        {model.branches.map((branch) => (
          <BranchColumn key={branch.id} branch={branch} />
        ))}
      </div>
    </div>
  );
}
