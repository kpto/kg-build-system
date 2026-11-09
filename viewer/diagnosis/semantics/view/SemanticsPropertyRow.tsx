"use client";

import { ChevronRight } from "lucide-react";
import { AnnotationPopover } from "@/shared/ui/AnnotationPopover";
import { cx } from "@/shared/ui/theme";
import type { MetaGraphIndex } from "@/lib/types";
import type { SemanticsPropertyRowModel } from "@/diagnosis/semantics/model/SemanticsModel";
import { SemanticsBadge } from "@/diagnosis/semantics/view/SemanticsBadges";

export interface SemanticsPropertyRowProps {
  row: SemanticsPropertyRowModel;
  metaGraph: MetaGraphIndex;
  /** `panel` is the full-width Cards row; `node` is the compressed canvas row. */
  variant?: "panel" | "node";
}

/**
 * One whole-row lineage target shared by the Cards index and the Graph cards.
 *
 * The row is an Outliner/Properties line rather than a nested card. It owns the
 * click, the annotation pill stays a separate control, and the audit marks are
 * right-aligned: a status dot, then impact only when it is greater than zero.
 */
export function SemanticsPropertyRow({
  row,
  metaGraph,
  variant = "panel",
}: SemanticsPropertyRowProps) {
  const compact = variant === "node";
  const sourceTitle = row.source.title ?? row.source.value;
  const openLineage = row.actions.find(
    (action) => action.id === "open-lineage",
  );
  const detailTitle =
    row.description ??
    `${row.name} · ${row.source.title ?? row.source.value}`;

  const status = row.badges.filter(
    (badge) =>
      badge.kind !== "impact" &&
      (badge.kind !== "risk" || (badge.value ?? 0) > 0) &&
      (!compact ||
        (badge.kind !== "literal" &&
          badge.kind !== "fallback" &&
          badge.kind !== "multi-source")),
  );
  const impact = row.badges.find(
    (badge) => badge.kind === "impact" && (badge.value ?? 0) > 0,
  );

  return (
    <div
      data-testid={`bp-property-row-${row.component}-${row.name}`}
      data-level="row"
      data-selected={row.selected ? "true" : undefined}
      title={detailTitle}
      className="ui-row group/property relative min-w-0 gap-2"
    >
      <button
        type="button"
        data-testid={`bp-property-${row.component}-${row.name}`}
        onClick={() => openLineage?.run()}
        disabled={!openLineage}
        aria-label={`Open lineage for ${row.component}.${row.name}`}
        title={detailTitle}
        className="ui-focus-ring absolute inset-0 z-0"
      />

      <span
        className={cx(
          "pointer-events-none relative z-10 min-w-0 truncate font-mono",
          compact ? "flex-1 text-[9px]" : "w-[26%] max-w-[210px] shrink-0 text-[10px]",
          row.selected ? "text-accent" : "text-text",
        )}
      >
        {row.name}
      </span>

      {!compact && row.typeLabel ? (
        <span
          className="pointer-events-none relative z-10 w-[54px] shrink-0 truncate font-mono text-[9px] text-faint"
          title={`Value type: ${row.typeLabel}`}
        >
          {row.typeLabel}
        </span>
      ) : null}

      {!compact ? (
        <span
          className="pointer-events-none relative z-10 min-w-0 flex-1 truncate text-[9px] text-muted"
          title={sourceTitle}
        >
          {row.source.value}
        </span>
      ) : null}

      <span
        className={cx(
          "pointer-events-none relative z-10 flex shrink-0 items-center justify-end gap-2",
          compact ? "max-w-[45%]" : "ml-auto max-w-[34%]",
        )}
      >
        {status.map((badge) => (
          <SemanticsBadge key={badge.id} badge={badge} dotOnly />
        ))}
        {impact ? (
          <SemanticsBadge
            badge={{
              ...impact,
              label: `impact ${impact.value}`,
            }}
          />
        ) : null}
      </span>

      <ChevronRight
        className={cx(
          "pointer-events-none relative z-10 shrink-0 text-faint opacity-0 transition-opacity group-hover/property:opacity-100",
          compact ? "hidden" : "size-3",
        )}
        aria-hidden
      />

      <span className="relative z-20 shrink-0 opacity-0 transition-opacity group-hover/property:opacity-100 group-focus-within/property:opacity-100">
        <AnnotationPopover
          annotations={row.annotations}
          context={{
            kind: row.kind,
            component: row.component,
            property: row.name,
          }}
          metaGraph={metaGraph}
          compact
        />
      </span>
    </div>
  );
}
