"use client";

import clsx from "clsx";

import type { IconName } from "@/components/ui";
import { Icon, Tooltip } from "@/components/ui";
import type { ProblemTier, TabArea } from "@/lib/types";
import { TAB_AREAS, TAB_LABEL } from "@/lib/types";

const AREA_ICON: Record<TabArea, IconName> = {
  topology: "topology",
  contracts: "contracts",
  projections: "projections",
  bindings: "bindings",
  sources: "sources",
  modules: "modules",
  plan: "plan",
};

export interface TabBadge {
  errors: number;
  warnings: number;
}

export interface NavRailProps {
  area: TabArea;
  onSelect(area: TabArea): void;
  /** Per-area problem counts, so a tab can light up without opening it. */
  badges?: Partial<Record<TabArea, TabBadge>>;
}

/**
 * The left rail: the seven areas, in key order.
 *
 * `1`–`7` select them (handled by the shell), so the number is shown on the tooltip
 * and the active state is a bar on the inside edge rather than a filled block — the
 * rail must read as navigation, not as content.
 */
export function NavRail({ area, onSelect, badges }: NavRailProps) {
  return (
    <nav
      aria-label="Studio areas"
      role="tablist"
      aria-orientation="vertical"
      className="flex w-11 shrink-0 flex-col items-center gap-0.5 border-r border-edge bg-surface py-1.5"
    >
      {TAB_AREAS.map((tab, index) => {
        const active = tab === area;
        const badge = badges?.[tab];
        const tone: ProblemTier | null =
          badge && badge.errors > 0 ? "types" : badge && badge.warnings > 0 ? "build" : null;
        return (
          <Tooltip
            key={tab}
            side="right"
            content={
              <span>
                {TAB_LABEL[tab]}
                <span className="ml-1.5 text-faint">{index + 1}</span>
                {badge && badge.errors + badge.warnings > 0
                  ? ` · ${badge.errors} error${badge.errors === 1 ? "" : "s"}, ${badge.warnings} warning${badge.warnings === 1 ? "" : "s"}`
                  : ""}
              </span>
            }
          >
            <button
              type="button"
              role="tab"
              id={`rail-${tab}`}
              aria-label={TAB_LABEL[tab]}
              aria-selected={active}
              aria-controls={`panel-${tab}`}
              tabIndex={active ? 0 : -1}
              onClick={() => onSelect(tab)}
              className={clsx(
                "relative flex h-9 w-9 items-center justify-center rounded-md border transition-colors",
                active
                  ? "border-edge-strong bg-raised text-ink"
                  : "border-transparent text-muted hover:bg-raised hover:text-ink",
              )}
            >
              <Icon name={AREA_ICON[tab]} size={17} />
              <span
                aria-hidden
                className={clsx(
                  "absolute right-1 top-0.5 font-mono text-[8px] leading-none",
                  active ? "text-muted" : "text-faint",
                )}
              >
                {index + 1}
              </span>
              {active && (
                <span aria-hidden className="absolute -right-[7px] top-1.5 bottom-1.5 w-0.5 rounded bg-info" />
              )}
              {tone && (
                <span
                  aria-hidden
                  className={clsx(
                    "absolute bottom-1 right-1 h-1.5 w-1.5 rounded-full",
                    tone === "types" ? "bg-danger" : "bg-warn",
                  )}
                />
              )}
            </button>
          </Tooltip>
        );
      })}
    </nav>
  );
}
