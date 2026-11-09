"use client";

import { memo, useCallback, useEffect, useState } from "react";
import { ChevronDown, ShieldQuestion } from "lucide-react";
import { AnnotationPopover } from "@/shared/ui/AnnotationPopover";
import { cx, groupPalette } from "@/shared/ui/theme";
import type {
  SemanticsEntityModel,
  SemanticsModel,
} from "@/diagnosis/semantics/model/SemanticsModel";
import { SemanticsBadgeLegend } from "@/diagnosis/semantics/view/SemanticsBadges";
import { SemanticsPropertyRow } from "@/diagnosis/semantics/view/SemanticsPropertyRow";

function defaultCollapsed(model: SemanticsModel): Record<string, boolean> {
  return Object.fromEntries(
    model.cards.defaultCollapsedGroupIds.map((parent) => [parent, true]),
  );
}

interface GridCardProps {
  entity: SemanticsEntityModel;
  focused: boolean;
  dimmed: boolean;
  metaGraph: SemanticsModel["metaGraph"];
  onToggleFocus: (itemKey: string) => void;
}

const GridCard = memo(function GridCard({
  entity,
  focused,
  dimmed,
  metaGraph,
  onToggleFocus,
}: GridCardProps) {
  const review = entity.actions.find((action) => action.id === "open-review");

  return (
    <div
      data-testid={`bp-${entity.kind}-${entity.name}`}
      data-level="row-group"
      role="group"
      data-selected={entity.selected ? "true" : undefined}
      data-focused={focused ? "true" : undefined}
      data-dimmed={dimmed ? "true" : undefined}
      className={cx(
        "group/entity mb-1 last:mb-0",
        dimmed && "opacity-35 saturate-50",
      )}
      aria-label={`${entity.kind} ${entity.name}: ${entity.description}`}
    >
      <div
        data-level="row"
        data-selected={entity.selected ? "true" : undefined}
        className={cx(
          "ui-row relative min-h-[26px] gap-2",
          entity.selected && "ui-selected-row",
        )}
      >
        <span
          aria-hidden
          className={cx(
            "size-1.5 shrink-0",
            entity.kind === "edge" ? "rotate-45" : "rounded-full",
          )}
          style={{
            backgroundColor:
              groupPalette[entity.paletteIndex % groupPalette.length],
          }}
        />
        <h3
          className={cx(
            "min-w-0 max-w-[36%] shrink-0 truncate font-mono text-[11px] font-medium",
            entity.selected ? "text-white" : "text-text",
          )}
          title={entity.name}
        >
          {entity.name}
        </h3>
        <p
          className="min-w-0 flex-1 truncate text-[10px] text-muted"
          title={entity.description}
        >
          {entity.description}
        </p>
        {focused ? (
          <span className="shrink-0 text-[9px] text-accent-strong">focused</span>
        ) : null}
        <span className="ui-row-meta shrink-0">
          {entity.propertyCount} props
        </span>
        <span className="pointer-events-none absolute top-1/2 right-1 z-10 flex -translate-y-1/2 items-center gap-1 rounded-[3px] bg-panel px-1 py-0.5 opacity-0 transition-opacity group-hover/entity:pointer-events-auto group-hover/entity:opacity-100 group-focus-within/entity:pointer-events-auto group-focus-within/entity:opacity-100">
          <button
            type="button"
            data-testid={`review-entity-${entity.name}`}
            onClick={() => review?.run()}
            disabled={!review}
            className="ui-button ui-button-ghost min-h-[20px] shrink-0 px-1.5 text-[9px]"
            title={
              review
                ? (review.title ?? `Open review for ${entity.kind} ${entity.name}`)
                : "Review surface is not wired in this shell"
            }
          >
            <ShieldQuestion className="size-3" aria-hidden />
            Review
          </button>
          <button
            type="button"
            data-testid={`bp-card-focus-${entity.name}`}
            aria-pressed={focused}
            onClick={() => onToggleFocus(entity.key)}
            className="ui-button ui-button-ghost min-h-[20px] shrink-0 px-1.5 text-[9px]"
            title={
              focused
                ? `Clear focus from ${entity.kind} ${entity.name}`
                : `Focus ${entity.kind} ${entity.name} in the card index`
            }
          >
            {focused ? "Unfocus" : "Focus"}
          </button>
          <AnnotationPopover
            annotations={entity.annotations}
            context={{ kind: entity.kind, component: entity.name }}
            metaGraph={metaGraph}
            compact
          />
        </span>
      </div>

      {entity.properties.map((property) => (
        <SemanticsPropertyRow
          key={property.id}
          row={property}
          metaGraph={metaGraph}
        />
      ))}
      {!entity.propertyCount ? (
        <div className="ui-row text-faint">
          <span className="text-[9px]">no properties declared</span>
        </div>
      ) : null}
    </div>
  );
});

function groupRiskCount(model: SemanticsModel, groupId: string): number {
  const group = model.cards.groups.find((entry) => entry.id === groupId);
  if (!group) return 0;
  return group.entities.reduce((total, entity) => {
    const entityRisks = entity.properties.reduce(
      (sum, property) =>
        sum +
        (property.badges.find((badge) => badge.kind === "risk")?.value ?? 0),
      0,
    );
    return total + entityRisks;
  }, 0);
}

export interface SemanticsGridProps {
  model: SemanticsModel;
}

/**
 * Audit-readable blueprint overview.
 *
 * Each parent group is a sticky rounded section band; every entity below it is
 * a subject row with one 28px label row and 26px property rows, so the index
 * reads as group -> entity -> property -> field rather than a stack of cards.
 * A reviewer can jump to property lineage from any property row, and a large
 * index mounts one group by default.
 */
export function SemanticsGrid({ model }: SemanticsGridProps) {
  const { cards } = model;
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>(() =>
    defaultCollapsed(model),
  );
  const [focusedKey, setFocusedKey] = useState<string | null>(null);

  // A new blueprint is a new index; the campaign rebuilds `sourceKey` only when
  // the blueprint changes. Selection changes do not reset the reader's groups.
  useEffect(() => {
    setCollapsed(defaultCollapsed(model));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cards.sourceKey]);

  // A new selected subject always reveals its group, even after Collapse all.
  useEffect(() => {
    const parent = cards.focusGroupId;
    if (!parent) return;
    setCollapsed((current) => {
      if (!current[parent]) return current;
      return { ...current, [parent]: false };
    });
  }, [cards.focusGroupId]);

  const toggleCardFocus = useCallback((itemKey: string) => {
    setFocusedKey((current) => (current === itemKey ? null : itemKey));
  }, []);

  const focusedKeyExists = focusedKey
    ? cards.groups.some((group) =>
        group.entities.some((entity) => entity.key === focusedKey),
      )
    : false;
  const activeFocusedKey = focusedKeyExists ? focusedKey : null;
  const focusedName = activeFocusedKey?.split(":").slice(1).join(":");
  const allGroupsCollapsed =
    cards.groups.length > 0 &&
    cards.groups.every((group) => Boolean(collapsed[group.id]));

  const toggleGroup = (parent: string) => {
    setCollapsed((current) => ({
      ...current,
      [parent]: !current[parent],
    }));
  };
  const collapseAll = () => {
    setCollapsed(
      Object.fromEntries(cards.groups.map((group) => [group.id, true])),
    );
  };
  const expandAll = () => {
    setCollapsed({});
  };

  return (
    <div
      data-testid="blueprint-grid"
      className="thin-scrollbar h-full w-full overflow-y-auto bg-panel"
    >
      <div
        data-testid="bp-grid-toolbar"
        className="flex min-w-0 flex-col gap-1 border-b border-line-soft bg-panel px-2 py-1"
      >
        <div className="flex min-w-0 items-center gap-2">
          <span className="shrink-0 text-[9px] text-faint">Groups</span>
          <span
            data-testid="bp-group-total"
            className="ui-section-count shrink-0"
          >
            {cards.groupCount}
          </span>
          <button
            type="button"
            data-testid="bp-collapse-all"
            onClick={collapseAll}
            disabled={!cards.groups.length}
            className="ui-button ui-button-ghost min-h-[22px] px-1.5 text-[9px]"
          >
            Collapse all
          </button>
          <button
            type="button"
            data-testid="bp-expand-all"
            onClick={expandAll}
            disabled={!cards.groups.length}
            className="ui-button ui-button-ghost min-h-[22px] px-1.5 text-[9px]"
          >
            Expand all
          </button>
          {activeFocusedKey ? (
            <>
              <span
                data-testid="bp-focus-state"
                className="inline-flex shrink-0 items-center gap-1 text-[9px] text-accent-strong"
                title={`Focused card: ${activeFocusedKey}`}
              >
                <span className="size-1.5 rounded-full bg-accent-strong" aria-hidden />
                Focus · {focusedName}
              </span>
              <button
                type="button"
                data-testid="bp-focus-clear"
                onClick={() => setFocusedKey(null)}
                className="ui-button ui-button-ghost min-h-[22px] px-1.5 text-[9px]"
              >
                Clear focus
              </button>
            </>
          ) : null}
          <p
            data-testid="blueprint-cards-hint"
            className="ml-auto hidden min-w-0 truncate text-[9px] text-faint 2xl:block"
          >
            {model.overlay.hints.cards}
          </p>
          <span className="ml-auto shrink-0 font-mono text-[9px] text-faint tabular-nums 2xl:ml-0">
            {cards.entityCount} entities · {cards.propertyCount} properties
          </span>
        </div>
        <SemanticsBadgeLegend entries={model.overlay.auditKey.legend} />
      </div>

      {allGroupsCollapsed ? (
        <div
          data-testid="bp-all-collapsed"
          className="ui-row flex-wrap justify-between gap-2 px-2 py-1"
        >
          <p className="text-[9px] text-faint">
            All {cards.groups.length} groups collapsed · {cards.entityCount}{" "}
            entities hidden.
          </p>
          <button
            type="button"
            data-testid="bp-expand-all-empty"
            onClick={expandAll}
            className="ui-button min-h-[22px] px-1.5 text-[9px]"
          >
            Expand all
          </button>
        </div>
      ) : null}

      <div>
        {cards.groups.map((group) => {
          const isCollapsed = Boolean(collapsed[group.id]);
          const tone = groupPalette[group.paletteIndex % groupPalette.length];
          const risks = groupRiskCount(model, group.id);
          return (
            <section
              key={group.parent}
              data-testid={`bp-grid-group-${group.parent}`}
              data-level="section"
              data-state={isCollapsed ? "collapsed" : "expanded"}
              className="ui-section overflow-visible"
              aria-label={`${group.parent}: ${group.question}`}
            >
              <button
                type="button"
                data-testid={`bp-group-toggle-${group.parent}`}
                aria-expanded={!isCollapsed}
                aria-label={`${group.parent}: ${group.question} ${group.count} entities, ${group.propertyCount} properties.`}
                data-collapsible="true"
                onClick={() => toggleGroup(group.parent)}
                className="ui-section-header group/group sticky top-0 z-20 w-full rounded-t-[3px] border-b border-line-soft bg-panel-raised"
              >
                <ChevronDown
                  className={cx(
                    "size-3 shrink-0 text-faint transition-transform duration-150 group-hover/group:text-muted",
                    isCollapsed && "-rotate-90",
                  )}
                  aria-hidden
                />
                <span
                  aria-hidden
                  className="h-3.5 w-[3px] shrink-0 rounded-sm"
                  style={{ backgroundColor: tone }}
                />
                <span
                  role="heading"
                  aria-level={2}
                  className="ui-section-title min-w-0 truncate"
                >
                  {group.title}
                </span>
                <span
                  data-testid={`bp-group-count-${group.parent}`}
                  className="ui-section-count shrink-0"
                >
                  {group.count}
                </span>
                <span className="shrink-0 font-mono text-[9px] text-faint tabular-nums">
                  {group.propertyCount} props
                </span>
                {risks > 0 ? (
                  <span
                    className="inline-flex shrink-0 items-center gap-1 text-[9px] text-muted"
                    title={`${risks} audit finding${risks === 1 ? "" : "s"} in this group`}
                  >
                    <span className="size-1.5 rounded-full bg-post" aria-hidden />
                    {risks} risks
                  </span>
                ) : null}
                <span className="ml-auto flex shrink-0 items-center gap-1 text-[9px] text-faint transition-colors group-hover/group:text-muted">
                  {isCollapsed ? "Expand" : "Collapse"}
                  <ChevronDown
                    className={cx(
                      "size-3 transition-transform duration-150",
                      isCollapsed && "-rotate-90",
                    )}
                    aria-hidden
                  />
                </span>
              </button>
              {!isCollapsed ? (
                <div className="ui-section-body px-1 py-1">
                  {group.entities.map((entity) => {
                    const focused = activeFocusedKey === entity.key;
                    return (
                      <GridCard
                        key={entity.key}
                        entity={entity}
                        focused={focused}
                        dimmed={Boolean(activeFocusedKey) && !focused}
                        metaGraph={model.metaGraph}
                        onToggleFocus={toggleCardFocus}
                      />
                    );
                  })}
                </div>
              ) : null}
            </section>
          );
        })}
      </div>

      {cards.empty ? (
        <div className="px-3 py-3">
          <p className="text-[10px] font-medium text-muted">
            {cards.empty.title}
          </p>
          <p className="ui-hint">{cards.empty.hint}</p>
        </div>
      ) : null}
    </div>
  );
}
