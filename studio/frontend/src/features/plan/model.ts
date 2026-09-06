/**
 * The plan view-model: one pure function from (plan, filters, selection, spacing)
 * to everything the canvas draws.
 *
 * Keeping it pure is what makes the tab testable — layout, counts and highlighting
 * are functions of data, not of a mounted graph — and it makes the canvas a
 * projection rather than a second source of truth.
 */

import { entityRef } from "@/lib/ids";
import type { Problem } from "@/lib/types";
import type { ProjectDocument } from "@/lib/ir";
import type {
  ModuleRole,
  PlanCounts,
  PlanFilters,
  PlanLayout,
  PlanModule,
  StepDetail,
  StepEdge,
  StepNode,
} from "./types";
import { DEFAULT_SPACING, layoutPlan, type StepSize } from "./layout";
import type { LayoutSpacing } from "./types";
import { measureSteps } from "./sizing";
import { stepDetail, stepRef } from "./detail";
import { countGraph, EMPTY_FILTERS, filterGraph, staleness, type Staleness } from "./filters";
import { laneColors, moduleRole } from "./lanes";

export interface PlanModel {
  readonly nodes: readonly StepNode[];
  readonly edges: readonly StepEdge[];
  readonly visibleNodes: readonly StepNode[];
  readonly visibleEdges: readonly StepEdge[];
  readonly details: ReadonlyMap<string, StepDetail>;
  readonly sizes: ReadonlyMap<string, StepSize>;
  readonly layout: PlanLayout;
  readonly colors: ReadonlyMap<string, string>;
  readonly roles: ReadonlyMap<string, ModuleRole>;
  readonly modules: readonly PlanModule[];
  readonly counts: PlanCounts;
  readonly totals: PlanCounts;
  /** Steps whose IR ref *is* the selected ref — the ones drawn as selected. */
  readonly selectedSteps: ReadonlySet<string>;
  readonly stale: Staleness;
  readonly spacing: LayoutSpacing;
  readonly fingerprint: string | null;
}

export interface PlanModelInput {
  readonly nodes: readonly StepNode[];
  readonly edges: readonly StepEdge[];
  readonly modules?: readonly PlanModule[];
  readonly fingerprint?: string | null;
  readonly filters?: PlanFilters;
  readonly selectedRef?: string | null;
  readonly document?: ProjectDocument | null;
  readonly spacing?: Partial<LayoutSpacing>;
  readonly generationState?: string | null;
  readonly mock?: boolean;
}

export function buildPlanModel(input: PlanModelInput): PlanModel {
  const filters = input.filters ?? EMPTY_FILTERS;
  const selectedRef = input.selectedRef ?? null;
  const document = input.document ?? null;
  const spacing: LayoutSpacing = { ...DEFAULT_SPACING, ...(input.spacing ?? {}) };
  const modules = input.modules ?? [];

  const details = new Map<string, StepDetail>();
  for (const node of input.nodes) details.set(node.id, stepDetail(node, input.edges, document));

  const visible = filterGraph(input.nodes, input.edges, filters, selectedRef);
  const visibleDetails = new Map<string, StepDetail>();
  for (const node of visible.nodes) {
    const detail = details.get(node.id);
    if (detail) visibleDetails.set(node.id, detail);
  }

  const roles = new Map<string, ModuleRole>();
  for (const module of modules) roles.set(module.id, moduleRole(module.id, module.role));
  for (const node of visible.nodes) {
    if (!roles.has(node.module_id)) roles.set(node.module_id, moduleRole(node.module_id));
  }

  const sizes = measureSteps(visible.nodes, visibleDetails);
  const layout = layoutPlan({
    nodes: visible.nodes,
    edges: visible.edges,
    sizes,
    spacing,
  });

  const entity = entityRef(selectedRef);
  const selectedSteps = new Set<string>();
  if (entity) {
    for (const node of visible.nodes) {
      const ref = stepRef(node);
      if (ref && entityRef(ref) === entity) selectedSteps.add(node.id);
    }
  }

  return {
    nodes: input.nodes,
    edges: input.edges,
    visibleNodes: visible.nodes,
    visibleEdges: visible.edges,
    details: visibleDetails,
    sizes: layout.placed.length > 0 ? measureSteps(visible.nodes, visibleDetails) : new Map(),
    layout,
    colors: laneColors(
      modules.length > 0
        ? modules.map((module) => ({ id: module.id, role: module.role }))
        : [...roles].map(([id, role]) => ({ id, role })),
    ),
    roles,
    modules,
    counts: countGraph(visible.nodes, visible.edges),
    totals: countGraph(input.nodes, input.edges),
    selectedSteps,
    stale: staleness(input.generationState, { mock: input.mock, planPresent: input.nodes.length > 0 }),
    spacing,
    fingerprint: input.fingerprint ?? null,
  };
}

/** Problems attached to a step, reached through the step's IR ref. */
export function problemsForStep(
  byRefIndex: Readonly<Record<string, Problem[]>>,
  node: StepNode,
): readonly Problem[] {
  const ref = stepRef(node);
  if (!ref) return [];
  const whole = entityRef(ref);
  return [...(byRefIndex[ref] ?? []), ...(whole && whole !== ref ? (byRefIndex[whole] ?? []) : [])];
}
