"use client";

import { useMemo, useState } from "react";
import {
  ArrowUpRight,
  Braces,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  ChevronsDown,
  ChevronsUp,
  Database,
  FolderTree,
  GitBranch,
  Layers3,
  Network,
  Search,
  Workflow,
  X,
} from "lucide-react";
import { PanelHeader } from "@/shared/ui/PanelHeader";
import { Row } from "@/shared/ui/Row";
import { Section } from "@/shared/ui/Section";
import { cx } from "@/shared/ui/theme";
import type { IconToken } from "@/shared/model/hierarchy";
import { filterNavigatorModel } from "@/navigation/model/buildNavigatorModel";
import type {
  NavigatorModel,
  NavigatorRow,
} from "@/navigation/model/NavigatorModel";

type IconComponent = typeof FolderTree;

const ICONS: Partial<Record<IconToken, IconComponent>> = {
  outliner: FolderTree,
  workflow: Workflow,
  navigator: Network,
  branch: GitBranch,
  asset: Database,
  binding: GitBranch,
  field: Braces,
  layers: Layers3,
  trace: Braces,
  open: ArrowUpRight,
  expand: ChevronDown,
  collapse: ChevronUp,
};

function RowIcon({ token }: { token?: IconToken }) {
  if (!token) return null;
  const Icon = ICONS[token];
  if (!Icon) return null;
  return <Icon className="size-3 shrink-0 text-faint" aria-hidden />;
}

function countLabel(count: number, total: number): string {
  return count === total ? `${count}` : `${count}/${total}`;
}

function hasSelectedDescendant(row: NavigatorRow): boolean {
  if (row.selected) return true;
  return Boolean(row.children?.some(hasSelectedDescendant));
}

const treeSummary = "ui-outliner-row group/row w-full cursor-pointer list-none justify-start";
const treeButton = "ui-outliner-row w-full justify-start";

function TreeRow({
  row,
  filtering,
}: {
  row: NavigatorRow;
  filtering: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const autoOpen =
    filtering || Boolean(row.openOnSelection && hasSelectedDescendant(row));
  const isOpen = autoOpen || expanded;
  const primary = row.actions?.find((entry) => entry.id !== "toggle-group");
  const toggle = row.actions?.find((entry) => entry.id === "toggle-group");
  const groupTestId = toggle ? `group-chip-${row.label}` : undefined;

  if (row.kind === "label") {
    return (
      <>
        <Row className="min-h-[24px] border-b-0 bg-panel">
          <span className="flex-1 text-[10.5px] font-medium text-ink-soft">
            {row.label}
          </span>
          {row.count !== undefined && row.total !== undefined ? (
            <span className="ui-section-count">
              {countLabel(row.count, row.total)}
            </span>
          ) : null}
        </Row>
        {row.children?.map((child) => (
          <TreeRow key={child.id} row={child} filtering={filtering} />
        ))}
        {!row.children?.length && row.empty ? (
          <p className="ui-hint px-2 py-1">{row.empty}</p>
        ) : null}
      </>
    );
  }

  if (row.kind === "member") {
    if (row.detail) {
      return (
        <p
          className="truncate px-2 py-0.5 font-mono text-[8.5px] text-faint"
          title={row.title ?? row.detail}
        >
          {row.detail}
        </p>
      );
    }
    return (
      <p
        className="truncate px-2 py-1 text-[10px] leading-relaxed text-muted"
        title={row.title ?? row.label}
      >
        {row.label}
      </p>
    );
  }

  if (row.kind === "group" || row.kind === "entity" || row.kind === "asset" || row.kind === "owner") {
    return (
      <details
        open={isOpen}
        onToggle={(event) => setExpanded(event.currentTarget.open)}
        className="group/tree"
      >
        <summary
          className={cx(treeSummary, row.selected && "ui-selected-row")}
          data-level="row"
          data-selected={row.selected || undefined}
          data-testid={groupTestId}
          title={row.kind === "entity" ? "Click to inspect and expand this entity" : undefined}
          onClick={
            row.kind === "entity"
              ? () => {
                  if (primary) primary.run();
                }
              : undefined
          }
        >
          <ChevronRight
            className="size-3 shrink-0 text-faint transition-transform group-open/tree:rotate-90"
            aria-hidden
          />
          <RowIcon token={row.icon} />
          <span className="min-w-0 flex-1 truncate text-[10.5px] text-ink-soft">
            {row.label}
          </span>
          {row.meta !== undefined ? (
            <span className="ui-row-meta ml-auto">{row.meta}</span>
          ) : null}
          {toggle ? (
            <button
              type="button"
              data-testid={`group-toggle-${row.label}`}
              aria-expanded={!row.collapsed}
              aria-label={`${row.collapsed ? "Expand" : "Collapse"} ${row.label}`}
              title={`${row.collapsed ? "Expand" : "Collapse"} ${row.label}`}
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                toggle.run();
              }}
              className="ui-icon-button ui-focus-ring size-5 shrink-0 opacity-0 group-hover/row:opacity-100 group-focus-within/row:opacity-100 focus-visible:opacity-100"
            >
              {row.collapsed ? (
                <ChevronDown className="size-3" aria-hidden />
              ) : (
                <ChevronUp className="size-3" aria-hidden />
              )}
            </button>
          ) : null}
          {primary && row.kind !== "entity" ? (
            <button
              type="button"
              aria-label={primary.label}
              title={primary.title ?? primary.label}
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                primary.run();
              }}
              className="ui-icon-button ui-focus-ring size-5 shrink-0 opacity-0 group-hover/row:opacity-100 group-focus-within/row:opacity-100 focus-visible:opacity-100"
            >
              <ArrowUpRight className="size-3" aria-hidden />
            </button>
          ) : null}
        </summary>
        {isOpen ? (
          <div className="ml-3 border-l border-line-soft/70 pl-1">
            {row.children?.map((child) => (
              <TreeRow key={child.id} row={child} filtering={filtering} />
            ))}
            {!row.children?.length && row.empty ? (
              <p className="ui-hint px-2 py-1">{row.empty}</p>
            ) : null}
          </div>
        ) : null}
      </details>
    );
  }

  return (
    <button
      type="button"
      data-level="row"
      data-selected={row.selected || undefined}
      onClick={() => primary?.run()}
      title={row.title}
      className={cx(treeButton, row.selected && "ui-selected-row")}
    >
      <RowIcon token={row.icon} />
      <span className="min-w-0 flex-1 truncate font-mono text-[10.5px]">
        {row.label}
      </span>
      {row.meta ? (
        <span className="ui-row-meta max-w-[8.5rem] truncate">{row.meta}</span>
      ) : null}
    </button>
  );
}

export interface NavigatorViewProps {
  model: NavigatorModel;
}

/**
 * The Outliner binds to an injected `NavigatorModel`.
 *
 * The filter string and the expanded/collapsed state of a tree group are view
 * state. Everything else — section questions, rows, counts, selected state and
 * the campaign actions — comes from the model.
 */
export function NavigatorView({ model }: NavigatorViewProps) {
  const [filter, setFilter] = useState("");
  const [sectionsOpen, setSectionsOpen] = useState(true);
  const [openOverrides, setOpenOverrides] = useState<Record<string, boolean>>({});
  const filtering = filter.trim().length > 0;
  const visible = useMemo(
    () => filterNavigatorModel(model, filter),
    [filter, model],
  );

  return (
    <aside
      data-testid="explorer"
      data-level="panel"
      className="ui-outliner flex h-full w-[17.5rem] shrink-0 flex-col"
    >
      <PanelHeader
        title={model.title}
        icon={<FolderTree className="size-3.5" />}
        meta={model.meta}
        actions={
          <>
            <button
              type="button"
              data-testid="outliner-collapse"
              onClick={() => {
                setSectionsOpen(false);
                setOpenOverrides({});
              }}
              aria-label={model.collapseAllLabel}
              title="Collapse all collections"
              className="ui-icon-button ui-focus-ring"
            >
              <ChevronsUp className="size-3.5" aria-hidden />
            </button>
            <button
              type="button"
              data-testid="outliner-expand"
              onClick={() => {
                setSectionsOpen(true);
                setOpenOverrides({});
              }}
              aria-label={model.expandAllLabel}
              title="Expand all collections"
              className="ui-icon-button ui-focus-ring"
            >
              <ChevronsDown className="size-3.5" aria-hidden />
            </button>
          </>
        }
      />

      <div
        className="flex h-[30px] shrink-0 items-center gap-1.5 border-b border-line-soft bg-panel px-2"
        data-level="toolbar"
      >
        <div className="relative min-w-0 flex-1">
          <Search
            className="pointer-events-none absolute top-1/2 left-2 size-3 -translate-y-1/2 text-faint"
            aria-hidden
          />
          <input
            data-testid="explorer-filter"
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Escape") setFilter("");
            }}
            aria-label={model.filterLabel}
            title={model.filterTitle}
            placeholder={model.filterPlaceholder}
            className="ui-input h-6 pr-7 pl-7 text-[10px]"
          />
          {filter ? (
            <button
              type="button"
              data-testid="explorer-filter-clear"
              onClick={() => setFilter("")}
              aria-label={model.clearFilterLabel}
              title="Clear filter"
              className="ui-icon-button ui-focus-ring absolute top-1/2 right-0.5 size-5 -translate-y-1/2"
            >
              <X className="size-3" aria-hidden />
            </button>
          ) : null}
        </div>
        {model.slice === "workflow" ? (
          <span
            data-testid="outliner-grouping"
            data-level="control"
            title={`Grouped by ${model.groupingLabel}`}
            className="ui-chip shrink-0 text-[9px] text-muted"
          >
            by {model.groupingLabel}
          </span>
        ) : null}
      </div>

      <div className="thin-scrollbar min-h-0 flex-1 overflow-y-auto">
        {filtering && visible.empty ? (
          <div
            className="px-3 py-4"
            data-level="section"
            aria-label="Are there matching subjects in this slice?"
          >
            <p className="ui-section-title">
              {visible.noMatches?.title ?? "No matches"}
            </p>
            <p className="ui-hint mt-1">
              {visible.noMatches?.hint ?? "No subjects match the filter."}
            </p>
          </div>
        ) : null}

        {visible.sections.map((entry) => (
          <Section
            key={entry.id}
            title={entry.title}
            question={entry.question}
            count={countLabel(entry.count, entry.total)}
            collapsible
            open={filtering || (openOverrides[entry.id] ?? sectionsOpen)}
            onOpenChange={(open) =>
              setOpenOverrides((current) => ({ ...current, [entry.id]: open }))
            }
            testId={`outliner-${entry.id}`}
          >
            {entry.rows.map((row) => (
              <TreeRow key={row.id} row={row} filtering={filtering} />
            ))}
            {!entry.rows.length && entry.empty ? (
              <p className="ui-hint px-2 py-2">{entry.empty}</p>
            ) : null}
          </Section>
        ))}
      </div>
    </aside>
  );
}
