"use client";

/**
 * The plan's filter strip and toolbar.
 *
 * One row: module chips, kind chips, a component search, the "only steps that
 * touch the selected component" switch, the counts summary, then the view controls
 * (re-layout, spacing, zoom-to-fit). The counts come from the same pure predicates
 * the canvas filters with, so the summary line and the drawing cannot disagree.
 */

import { clsx } from "clsx";

import { Button, Chip, IconButton, TextInput, Toggle, Tooltip } from "@/components/ui";
import { RefreshIcon, SearchIcon } from "@/components/ui";
import type { PlanCounts, PlanFilters, PlanModule, StepKind } from "./types";
import { EMPTY_FILTERS, filtersActive } from "./filters";
import { KIND_LABEL } from "./detail";
import { TOKEN } from "./tokens";

export interface FilterStripProps {
  readonly modules: readonly PlanModule[];
  readonly kinds: readonly StepKind[];
  readonly kindCounts: ReadonlyMap<StepKind, number>;
  readonly moduleCounts: ReadonlyMap<string, number>;
  readonly filters: PlanFilters;
  readonly counts: PlanCounts;
  readonly totals: PlanCounts;
  readonly colors: ReadonlyMap<string, string>;
  readonly selectedRef: string | null;
  readonly stayOnPlan: boolean;
  readonly onStayOnPlan: (value: boolean) => void;
  readonly spacing: number;
  readonly loading: boolean;
  /** Present only with a backend: mock mode has nothing to execute. */
  readonly onBuild?: () => void;
  readonly building?: boolean;
  /** `status.build.state`, so the button can say what the last run did. */
  readonly buildState?: string;
  readonly onFilters: (next: PlanFilters) => void;
  readonly onSpacing: (value: number) => void;
  readonly onRelayout: () => void;
  readonly onFit: () => void;
  readonly onRefresh: () => void;
}

function toggle<T>(list: readonly T[], value: T): T[] {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
}

export function FilterStrip({
  modules,
  kinds,
  kindCounts,
  moduleCounts,
  filters,
  counts,
  totals,
  colors,
  selectedRef,
  stayOnPlan,
  onStayOnPlan,
  spacing,
  loading,
  onFilters,
  onSpacing,
  onRelayout,
  onFit,
  onRefresh,
  onBuild,
  building,
  buildState,
}: FilterStripProps) {
  const set = (patch: Partial<PlanFilters>) => onFilters({ ...filters, ...patch });
  const componentCount = selectedRef ? ` · ${selectedRef}` : "";

  return (
    <div className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-1.5 border-b border-edge bg-surface px-2 py-1.5">
      <div className="flex min-w-0 flex-wrap items-center gap-1" role="group" aria-label="Filter by module">
        {modules.map((module) => {
          const active = filters.modules.includes(module.id);
          const color = colors.get(module.id) ?? TOKEN.muted;
          return (
            <button
              key={module.id}
              type="button"
              aria-pressed={active}
              title={`${module.role ?? "module"} · ${moduleCounts.get(module.id) ?? 0} steps`}
              onClick={() => set({ modules: toggle(filters.modules, module.id) })}
              className={clsx(
                "studio-chip max-w-[13rem] cursor-pointer",
                !active && filters.modules.length > 0 && "opacity-45",
              )}
            >
              <span aria-hidden className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: color }} />
              <span className="truncate">{module.label || module.id}</span>
              <span className="text-faint">{moduleCounts.get(module.id) ?? 0}</span>
            </button>
          );
        })}
      </div>

      <span aria-hidden className="h-4 w-px bg-edge" />

      <div className="flex min-w-0 flex-wrap items-center gap-1" role="group" aria-label="Filter by step kind">
        {kinds.map((kind) => (
          <Chip
            key={kind}
            plain
            active={filters.kinds.includes(kind)}
            title={`${kindCounts.get(kind) ?? 0} steps of this kind`}
            onClick={() => set({ kinds: toggle(filters.kinds, kind) })}
          >
            {KIND_LABEL[kind] ?? kind}
            <span className="text-faint">{kindCounts.get(kind) ?? 0}</span>
          </Chip>
        ))}
      </div>

      <span aria-hidden className="h-4 w-px bg-edge" />

      <div className="relative w-44">
        <span className="pointer-events-none absolute left-1.5 top-1/2 -translate-y-1/2 text-faint">
          <SearchIcon size={12} />
        </span>
        <TextInput
          value={filters.query}
          placeholder="component or label"
          aria-label="Filter steps by component, label or relation"
          className="!pl-6"
          onChange={(event) => set({ query: event.target.value })}
        />
      </div>

      <Toggle
        label="only selected"
        description={`show only the steps that touch ${selectedRef ?? "the selected component"}`}
        checked={filters.onlySelected}
        disabled={!selectedRef}
        onChange={(checked) => set({ onlySelected: checked })}
      />
      <Toggle
        label="stay on plan"
        description="keep the plan visible when a step selects its IR ref (the shell otherwise jumps to the tab that owns the ref)"
        checked={stayOnPlan}
        onChange={onStayOnPlan}
      />

      {filtersActive(filters) && (
        <Button size="sm" variant="ghost" onClick={() => onFilters({ ...EMPTY_FILTERS })}>
          clear
        </Button>
      )}

      <div className="ml-auto flex items-center gap-3">
        <p className="font-mono text-[10px] text-muted" data-plan-counts="true">
          <span className="text-ink">{counts.steps}</span>
          <span className="text-faint">/{totals.steps} steps · </span>
          <span className="text-ink">{counts.connections}</span>
          <span className="text-faint">/{totals.connections} links · </span>
          <span className="text-ink">{counts.materialised}</span>
          <span className="text-faint"> materialised · </span>
          <span className="text-ink">{counts.withSql}</span>
          <span className="text-faint"> with SQL · </span>
          <span className="text-ink">{counts.components}</span>
          <span className="text-faint"> components{componentCount}</span>
        </p>

        <label className="flex items-center gap-1 font-mono text-[10px] text-faint" title="Lane and column spacing">
          spacing
          <input
            type="range"
            min={0}
            max={100}
            value={spacing}
            aria-label="Lane and column spacing"
            onChange={(event) => onSpacing(Number(event.target.value))}
            className="h-1 w-20 accent-[var(--color-info)]"
          />
        </label>

        <Tooltip content="Recompute the layered layout (deterministic: the same plan lays out the same way)" side="bottom">
          <IconButton label="Re-layout" icon={<RefreshIcon size={13} />} onClick={onRelayout} />
        </Tooltip>
        <Button size="sm" onClick={onFit} title="Frame the whole graph">
          zoom to fit
        </Button>
        <Button size="sm" variant={loading ? "primary" : "default"} onClick={onRefresh} disabled={loading}>
          {loading ? "loading…" : "recompile"}
        </Button>
        {onBuild && (
          <Tooltip
            content="Execute the compiled workflow and write the artifacts (DuckDB → graph.jsonl, meta graph, imports)"
            side="bottom"
          >
            <Button size="sm" onClick={onBuild} disabled={building}>
              {building
                ? "building…"
                : buildState === "done"
                  ? "build again"
                  : buildState === "failed"
                    ? "retry build"
                    : "run build"}
            </Button>
          </Tooltip>
        )}
      </div>
    </div>
  );
}
