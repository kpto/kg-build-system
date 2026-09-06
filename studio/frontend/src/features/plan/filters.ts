/**
 * Filter predicates, counts and the staleness rule — the plan tab's pure half.
 *
 * The strip and the canvas both read these, so what the counts say and what the
 * canvas draws can never disagree.
 */

import { entityRef, parseRef } from "@/lib/ids";
import type { PlanCounts, PlanFilters, StepEdge, StepKind, StepNode } from "./types";
import { isMaterialised, stepRef } from "./detail";

export const EMPTY_FILTERS: PlanFilters = {
  modules: [],
  kinds: [],
  query: "",
  onlySelected: false,
};

export function filtersActive(filters: PlanFilters): boolean {
  return (
    filters.modules.length > 0 ||
    filters.kinds.length > 0 ||
    filters.query.trim().length > 0 ||
    filters.onlySelected
  );
}

/** Case-insensitive match on the labels a user would actually type. */
export function matchesQuery(node: StepNode, query: string): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  const haystack = [
    node.label,
    node.id,
    node.component ?? "",
    node.kind,
    node.module_id,
    node.relation ?? "",
    ...(node.notes ?? []),
  ]
    .join(" ")
    .toLowerCase();
  return haystack.includes(needle);
}

/** A step "touches" the selected ref when it is that entity, or belongs to it. */
export function touchesRef(node: StepNode, selectedRef: string | null): boolean {
  if (!selectedRef) return false;
  const own = stepRef(node);
  if (!own) return false;
  if (own === selectedRef || entityRef(own) === entityRef(selectedRef)) return true;
  // A problem's ref may address a part (`component:site.property.city`); the step
  // that compiled that part still belongs to the same entity.
  const parsed = parseRef(selectedRef);
  const nodeParsed = parseRef(own);
  return Boolean(parsed && nodeParsed && parsed.kind === nodeParsed.kind && parsed.id === nodeParsed.id);
}

export function stepMatches(
  node: StepNode,
  filters: PlanFilters,
  selectedRef: string | null,
): boolean {
  if (filters.modules.length > 0 && !filters.modules.includes(node.module_id)) return false;
  if (filters.kinds.length > 0 && !filters.kinds.includes(node.kind as StepKind)) return false;
  if (!matchesQuery(node, filters.query)) return false;
  if (filters.onlySelected && !touchesRef(node, selectedRef)) return false;
  return true;
}

export interface VisibleGraph {
  readonly nodes: readonly StepNode[];
  readonly edges: readonly StepEdge[];
}

/** A connection survives only when both endpoints survive: the canvas never draws
 * an edge into empty space. */
export function filterGraph(
  nodes: readonly StepNode[],
  edges: readonly StepEdge[],
  filters: PlanFilters,
  selectedRef: string | null,
): VisibleGraph {
  const kept = nodes.filter((node) => stepMatches(node, filters, selectedRef));
  const visible = new Set(kept.map((node) => node.id));
  return {
    nodes: kept,
    edges: edges.filter((edge) => visible.has(edge.from_step) && visible.has(edge.to_step)),
  };
}

/** The strip's summary line; `total` is the unfiltered whole, for "12 of 60". */
export function countGraph(nodes: readonly StepNode[], edges: readonly StepEdge[]): PlanCounts {
  const components = new Set<string>();
  let materialised = 0;
  let withSql = 0;
  for (const node of nodes) {
    const ref = stepRef(node);
    if (ref) components.add(entityRef(ref) ?? ref);
    if (isMaterialised(node)) materialised += 1;
    if (typeof node.sql === "string" && node.sql.trim().length > 0) withSql += 1;
  }
  return {
    steps: nodes.length,
    connections: edges.length,
    materialised,
    withSql,
    components: components.size,
  };
}

/* ----------------------------------------------------------------- freshness */

export type StalenessLevel = "fresh" | "stale" | "unknown";

export interface Staleness {
  readonly level: StalenessLevel;
  readonly state: string;
  readonly message: string | null;
}

/**
 * The plan is compiled output, so anything other than a clean generation means the
 * DAG on screen may not be the DAG the framework would build now. A plan with no
 * status model behind it (mock mode, or a backend that never sent one) reports
 * `unknown` rather than claiming to be fresh.
 */
export function staleness(
  generationState: string | null | undefined,
  options: { readonly mock?: boolean; readonly planPresent?: boolean } = {},
): Staleness {
  const state = generationState ?? "never";
  if (options.mock) {
    return { level: "unknown", state, message: "Mock project — nothing has been compiled." };
  }
  if (options.planPresent === false) {
    return { level: "unknown", state, message: null };
  }
  if (state === "clean") return { level: "fresh", state, message: null };
  if (state === "never") {
    return { level: "stale", state, message: "The project has never been generated, so this plan predates nothing." };
  }
  const reason =
    state === "running"
      ? "regeneration is running now"
      : state === "failed"
        ? "the last generation failed"
        : state === "done"
          ? "generation just completed"
          : "the project has unpublished edits";
  return {
    level: "stale",
    state,
    message: `Generation is ${state} — ${reason}, so this plan may be stale.`,
  };
}

/** `sha256:0c6b5dda…` display form; the full value stays in the tooltip. */
export function shortFingerprint(fingerprint: string | null | undefined): string {
  if (!fingerprint) return "no fingerprint";
  return fingerprint.length > 12 ? fingerprint.slice(0, 12) : fingerprint;
}
