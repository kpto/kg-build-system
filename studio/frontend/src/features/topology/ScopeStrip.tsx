"use client";

import { useMemo, useState } from "react";
import clsx from "clsx";

import { PlusIcon, SearchIcon, TextInput } from "@/components/ui";
import type { Component } from "@/lib/ir";
import type { TopologyFilters } from "./logic";

type TopologyGlyph = "node" | "category" | "template" | "hierarchy";

export interface ScopeStripProps {
  components: readonly Component[];
  filters: TopologyFilters;
  onFiltersChange(filters: TopologyFilters): void;
  onAddNode(): void;
  /** Focus a component: select its ref and centre it on the canvas. */
  onLocate(ref: string, id: string): void;
}

/**
 * The left scope strip: what is drawn, and a jump-to box.
 *
 * Filtering is presentation only — hiding a tier never edits the document. The search
 * selects a component and centres it, which is how you find a node in a large graph
 * without dragging the viewport around.
 */
export function ScopeStrip({ components, filters, onFiltersChange, onAddNode, onLocate }: ScopeStripProps) {
  const [query, setQuery] = useState("");

  const results = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return [];
    return components
      .filter(
        (component) =>
          component.name.toLowerCase().includes(needle) ||
          component.declaration_name.toLowerCase().includes(needle) ||
          (component.label ?? "").toLowerCase().includes(needle),
      )
      .slice(0, 12);
  }, [components, query]);

  const toggle = (key: keyof TopologyFilters) =>
    onFiltersChange({ ...filters, [key]: !filters[key] });

  return (
    <aside className="flex w-52 shrink-0 flex-col gap-2 border-r border-edge bg-surface p-2">
      <button
        type="button"
        data-testid="add-node-button"
        onClick={onAddNode}
        className="flex items-center justify-center gap-1.5 rounded-md border border-info/60 bg-info/15 px-2 py-1.5 text-[12px] font-medium text-ink hover:bg-info/25"
      >
        <PlusIcon size={14} /> Add node
      </button>

      <div className="flex flex-col gap-1">
        <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-muted">scope</p>
        <FilterChip
          label="Templates"
          glyph="template"
          active={filters.showTemplates}
          onClick={() => toggle("showTemplates")}
        />
        <FilterChip
          label="Categories"
          glyph="category"
          active={filters.showCategories}
          onClick={() => toggle("showCategories")}
        />
        <FilterChip
          label="Hierarchy links"
          glyph="hierarchy"
          active={filters.showHierarchy}
          onClick={() => toggle("showHierarchy")}
        />
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-1">
        <div className="relative">
          <SearchIcon className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-faint" />
          <TextInput
            aria-label="Find a component"
            className="pl-7"
            placeholder="find…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        <ul className="min-h-0 flex-1 overflow-auto">
          {results.map((component) => (
            <li key={component.id}>
              <button
                type="button"
                onClick={() => {
                  onLocate(`component:${component.id}`, component.id);
                  setQuery("");
                }}
                className="flex w-full items-center gap-1.5 rounded px-1.5 py-1 text-left hover:bg-raised"
              >
                <span aria-hidden className="h-2 w-2 shrink-0 rounded-full bg-node" />
                <span className="min-w-0 flex-1 truncate text-[12px] text-ink">{component.name}</span>
                <span className="shrink-0 font-mono text-[9px] uppercase text-faint">{component.tier}</span>
              </button>
            </li>
          ))}
          {query && results.length === 0 && (
            <li className="px-1.5 py-1 text-[11px] text-faint">no match</li>
          )}
        </ul>
      </div>

      <Legend />
    </aside>
  );
}

function FilterChip({
  label,
  glyph,
  active,
  onClick,
}: {
  label: string;
  glyph: TopologyGlyph;
  active: boolean;
  onClick(): void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={active}
      onClick={onClick}
      className={clsx(
        "flex items-center gap-2 rounded-md border px-2 py-1 text-[12px] transition-colors",
        active
          ? "border-edge bg-raised text-ink"
          : "border-transparent bg-transparent text-faint hover:text-muted",
      )}
    >
      <span aria-hidden className={clsx("h-2.5 w-2.5 shrink-0", glyphClass(glyph), !active && "opacity-40")} />
      <span className="flex-1 truncate text-left">{label}</span>
      <span aria-hidden className="font-mono text-[9px] text-faint">{active ? "on" : "off"}</span>
    </button>
  );
}

function glyphClass(glyph: TopologyGlyph): string {
  switch (glyph) {
    case "template":
      return "rotate-45 rounded-[2px] bg-template";
    case "category":
      return "rounded-full border border-dashed border-category";
    case "hierarchy":
      return "h-0 w-3 border-t border-dashed border-category";
    default:
      return "rounded-full bg-node";
  }
}

function Legend() {
  return (
    <div className="flex flex-col gap-0.5 border-t border-edge pt-1.5">
      <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-muted">legend</p>
      <LegendRow className="bg-node" label="concrete node" />
      <LegendRow className="border border-dashed border-category" label="category" />
      <LegendRow className="bg-template" label="template" />
      <LegendRow className="bg-relation" label="relation link" />
      <LegendRow className="bg-edgekind" label="edge category" />
      <LegendRow className="border-t border-dashed border-category" label="is-a hierarchy" />
    </div>
  );
}

function LegendRow({ className, label }: { className: string; label: string }) {
  return (
    <span className="flex items-center gap-2 text-[11px] text-muted">
      <span aria-hidden className={clsx("h-2 w-2 shrink-0 rounded", className)} />
      {label}
    </span>
  );
}
