"use client";

import { severityColor } from "@/shared/ui/theme";
import type {
  SemanticsBadgeKind,
  SemanticsBadgeModel,
  SemanticsLegendEntryModel,
} from "@/diagnosis/semantics/model/SemanticsModel";

const BADGE_DOT: Record<SemanticsBadgeKind, string> = {
  traced: "bg-source",
  literal: "bg-faint",
  fallback: "bg-accent-strong",
  "multi-source": "bg-transform",
  risk: "bg-post",
  impact: "bg-asset",
};

/**
 * One audit fact as a 6px semantic dot plus a muted label.
 *
 * `dotOnly` keeps a dense property row to a status mark; the label and its
 * meaning stay in the title. The audit key carries the vocabulary.
 */
export function SemanticsBadge({
  badge,
  dotOnly = false,
}: {
  badge: SemanticsBadgeModel;
  dotOnly?: boolean;
}) {
  const color = badge.severity ? severityColor[badge.severity] : undefined;
  return (
    <span
      className="inline-flex shrink-0 items-center gap-1 text-[9px] leading-none text-muted"
      title={badge.title}
    >
      <span
        aria-hidden
        className={`size-1.5 shrink-0 rounded-full ${color ? "" : BADGE_DOT[badge.kind]}`}
        style={color ? { backgroundColor: color } : undefined}
      />
      {dotOnly ? <span className="sr-only">{badge.label}</span> : badge.label}
    </span>
  );
}

/**
 * The badge vocabulary, stated once for the whole blueprint surface.
 *
 * The card rows keep only the dot; the legend pairs each dot with its sentence
 * case label so colour is never the only explanation.
 */
export function SemanticsBadgeLegend({
  entries,
  className = "",
}: {
  entries: SemanticsLegendEntryModel[];
  className?: string;
}) {
  return (
    <div
      data-testid="bp-badge-legend"
      className={`flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 ${className}`}
    >
      <span className="text-[9px] text-faint">Audit key</span>
      {entries.map((entry) => (
        <span key={entry.id} title={entry.meaning}>
          <SemanticsBadge
            badge={{
              id: entry.id,
              label: entry.label,
              kind: entry.kind,
              title: entry.meaning,
            }}
          />
        </span>
      ))}
    </div>
  );
}
