/**
 * Automatic left-to-right layered layout for a compiled plan.
 *
 * Written here rather than pulled in as a dependency: the graph is small and the
 * rules are plan-specific.
 *
 * 1. **Layering** — longest path from the sources: `layer(n) = 1 + max(layer of
 *    predecessors)`, `0` when there are none. A compiled contract cannot contain a
 *    cycle, but a plan arrives over HTTP, so a cycle is broken by dropping edges
 *    rather than by looping forever (`buildAdjacency`, then a defensive guard in
 *    `longestPathLayers`).
 * 2. **Ordering** — alternating down/up median (barycentre) sweeps over the layer
 *    sequence. A node with no neighbour in the fixed layer keeps its slot; ties
 *    break on the previous index and then the id, both total orders, so two runs on
 *    the same plan produce the same picture. The best sweep seen (fewest crossings)
 *    is the one returned.
 * 3. **Lanes** — one lane per module; columns are numbered *inside* the lane
 *    (`layer - lane.minLayer`), so every module reads left-to-right on its own and
 *    lanes are placed in `core → operator → target` order.
 * 4. **Component alignment** — nodes carrying the same IR ref are pulled halfway
 *    toward their group's median slot before packing, so one component can be
 *    followed with the eye from aggregate through operator to export.
 */

import type {
  Lane,
  LayoutSpacing,
  ModuleRole,
  PlacedStep,
  PlanLayout,
  StepEdge,
  StepNode,
} from "./types";

export const DEFAULT_SPACING: LayoutSpacing = {
  columnGap: 96,
  laneGap: 64,
  rowGap: 24,
};

/** Room for the lane label plus a visual margin around the column contents. */
export const LANE_PADDING_X = 20;
export const LANE_PADDING_TOP = 44;
export const LANE_PADDING_BOTTOM = 20;
export const CANVAS_PADDING = 32;

export interface StepSize {
  readonly width: number;
  readonly height: number;
}

export interface LayoutInput {
  readonly nodes: readonly StepNode[];
  readonly edges: readonly StepEdge[];
  readonly moduleRoles: ReadonlyMap<string, ModuleRole>;
  readonly moduleLabels?: ReadonlyMap<string, string>;
  readonly sizes?: ReadonlyMap<string, StepSize>;
  readonly spacing?: Partial<LayoutSpacing>;
  readonly passes?: number;
}

const FALLBACK_SIZE: StepSize = { width: 232, height: 112 };

const ROLE_RANK: Record<ModuleRole, number> = { core: 0, operator: 1, target: 2 };

/** A total order that never depends on insertion order or locale. */
function byId(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

/* ------------------------------------------------------------------ adjacency */

export interface Adjacency {
  readonly outgoing: ReadonlyMap<string, readonly string[]>;
  readonly incoming: ReadonlyMap<string, readonly string[]>;
  /** Connections that had to be dropped to make the graph acyclic. */
  readonly cycleBroken: readonly string[];
}

/**
 * Connections between known steps, with self-loops removed and — only if the plan
 * really is cyclic — the back edges that close the cycles dropped.
 */
export function buildAdjacency(
  nodes: readonly { readonly id: string }[],
  edges: readonly StepEdge[],
): Adjacency {
  const ids = [...new Set(nodes.map((node) => node.id))];
  const known = new Set(ids);

  const usable = edges.filter(
    (edge) => edge.from_step !== edge.to_step && known.has(edge.from_step) && known.has(edge.to_step),
  );

  const cycleBroken: string[] = [];
  const kept = [...usable];
  for (;;) {
    const buckets = link(ids, kept);
    const onCycle = cyclicNodes(ids, buckets.incoming, buckets.outgoing);
    if (onCycle.size === 0) {
      return { outgoing: buckets.outgoing, incoming: buckets.incoming, cycleBroken };
    }
    // Deterministic: the greatest connection id inside the cyclic part is the one
    // that goes, so the same cyclic plan always lays out the same way.
    const candidate = kept
      .filter((edge) => onCycle.has(edge.from_step) && onCycle.has(edge.to_step))
      .map((edge) => edge.id)
      .sort((a, b) => byId(b, a))[0];
    if (candidate === undefined) break;
    const index = kept.findIndex((edge) => edge.id === candidate);
    if (index >= 0) kept.splice(index, 1);
    cycleBroken.push(candidate);
  }

  const final = link(ids, kept);
  return { outgoing: final.outgoing, incoming: final.incoming, cycleBroken };
}

function link(
  ids: readonly string[],
  edges: readonly StepEdge[],
): { outgoing: Map<string, string[]>; incoming: Map<string, string[]> } {
  const outgoing = new Map<string, string[]>();
  const incoming = new Map<string, string[]>();
  for (const id of ids) {
    outgoing.set(id, []);
    incoming.set(id, []);
  }
  for (const edge of edges) {
    (outgoing.get(edge.from_step) as string[]).push(edge.to_step);
    (incoming.get(edge.to_step) as string[]).push(edge.from_step);
  }
  return { outgoing, incoming };
}

/** Nodes Kahn never reaches — the ones sitting on a cycle. Empty when acyclic. */
export function cyclicNodes(
  ids: readonly string[],
  incoming: ReadonlyMap<string, readonly string[]>,
  outgoing: ReadonlyMap<string, readonly string[]>,
): Set<string> {
  const degree = new Map<string, number>();
  for (const id of ids) degree.set(id, new Set(incoming.get(id) ?? []).size);
  const queue = ids.filter((id) => (degree.get(id) ?? 0) === 0);
  const seen = new Set<string>();
  while (queue.length > 0) {
    const id = queue.shift() as string;
    if (seen.has(id)) continue;
    seen.add(id);
    for (const next of outgoing.get(id) ?? []) {
      const left = (degree.get(next) ?? 0) - 1;
      degree.set(next, left);
      if (left === 0) queue.push(next);
    }
  }
  return new Set(ids.filter((id) => !seen.has(id)));
}

/* ------------------------------------------------------------------ layering */

/** Longest-path layering: sources at 0, every consumer one layer right of its
 * deepest producer. Cycle-safe by construction (a node already on the stack is
 * treated as a source). */
export function longestPathLayers(
  nodes: readonly { readonly id: string }[],
  incoming: ReadonlyMap<string, readonly string[]>,
): Map<string, number> {
  const layer = new Map<string, number>();
  const visiting = new Set<string>();

  const resolve = (id: string): number => {
    const settled = layer.get(id);
    if (settled !== undefined) return settled;
    if (visiting.has(id)) return 0;
    visiting.add(id);
    let depth = 0;
    for (const parent of incoming.get(id) ?? []) {
      depth = Math.max(depth, resolve(parent) + 1);
    }
    visiting.delete(id);
    layer.set(id, depth);
    return depth;
  };

  for (const node of nodes) resolve(node.id);
  return layer;
}

/* ----------------------------------------------------------------- ordering */

function median(values: readonly number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1
    ? (sorted[middle] as number)
    : ((sorted[middle - 1] as number) + (sorted[middle] as number)) / 2;
}

/**
 * Edge crossings between every pair of adjacent layers.
 *
 * Two connections cross when their producers and consumers are ordered the other
 * way round, which is exactly the inversion count of the consumer sequence read in
 * producer order.
 */
export function countCrossings(
  layerOf: ReadonlyMap<string, number>,
  incoming: ReadonlyMap<string, readonly string[]>,
  order: ReadonlyMap<string, number>,
): number {
  let total = 0;
  // Collect the connections that join layer L to layer L+1 and count inversions
  // per pair of layers.
  const between = new Map<number, { from: number; to: number }[]>();
  for (const [child, parents] of incoming) {
    const childLayer = layerOf.get(child);
    if (childLayer === undefined) continue;
    const childOrder = order.get(child) ?? 0;
    for (const parent of parents) {
      const parentLayer = layerOf.get(parent);
      if (parentLayer === undefined) continue;
      // Only immediate neighbours take part in the classic inversion count; longer
      // spans are straight lines through empty space and cannot hide a crossing.
      if (parentLayer !== childLayer - 1) continue;
      const bucket = between.get(childLayer) ?? [];
      bucket.push({ from: order.get(parent) ?? 0, to: childOrder });
      between.set(childLayer, bucket);
    }
  }

  for (const pairs of between.values()) {
    const sorted = [...pairs].sort((a, b) => a.from - b.from || a.to - b.to);
    for (let i = 0; i < sorted.length; i += 1) {
      for (let j = i + 1; j < sorted.length; j += 1) {
        const first = sorted[i];
        const second = sorted[j];
        if (!first || !second) continue;
        if (first.to > second.to) total += 1;
      }
    }
  }
  return total;
}

/**
 * Median/barycentre crossing reduction.
 *
 * @returns `id → index within its layer`, deterministic for a given graph.
 */
export function orderWithinLayers(
  layerOf: ReadonlyMap<string, number>,
  incoming: ReadonlyMap<string, readonly string[]>,
  outgoing: ReadonlyMap<string, readonly string[]>,
  seedOrder: readonly string[],
  passes = 8,
): Map<string, number> {
  const columns = new Map<number, string[]>();
  for (const id of seedOrder) {
    const layer = layerOf.get(id) ?? 0;
    const bucket = columns.get(layer);
    if (bucket) bucket.push(id);
    else columns.set(layer, [id]);
  }
  const layers = [...columns.keys()].sort((a, b) => a - b);

  const order = new Map<string, number>();
  for (const layer of layers) {
    (columns.get(layer) as string[]).forEach((id, index) => order.set(id, index));
  }

  const positionsOf = (id: string, useIncoming: boolean): number[] => {
    const links = useIncoming ? incoming.get(id) ?? [] : outgoing.get(id) ?? [];
    const positions: number[] = [];
    for (const other of links) {
      const position = order.get(other);
      if (position !== undefined) positions.push(position);
    }
    return positions;
  };

  let best = new Map(order);
  let bestCrossings = countCrossings(layerOf, incoming, best);

  for (let pass = 0; pass < passes && bestCrossings > 0; pass += 1) {
    const downwards = pass % 2 === 0;
    const sweep = downwards ? layers : [...layers].reverse();
    for (const layer of sweep) {
      const ids = columns.get(layer) as string[];
      const keyed = ids.map((id) => ({
        id,
        key: median(positionsOf(id, downwards)),
        before: order.get(id) ?? 0,
      }));
      keyed.sort(
        (a, b) =>
          (a.key ?? a.before) - (b.key ?? b.before) || a.before - b.before || byId(a.id, b.id),
      );
      keyed.forEach((entry, index) => {
        order.set(entry.id, index);
        ids[index] = entry.id;
      });
    }
    const crossings = countCrossings(layerOf, incoming, order);
    if (crossings < bestCrossings) {
      bestCrossings = crossings;
      best = new Map(order);
    }
  }

  return best;
}

/* -------------------------------------------------------------------- lanes */

export interface LaneGroup {
  readonly moduleId: string;
  readonly ids: readonly string[];
  readonly minLayer: number;
  readonly maxLayer: number;
}

/** Steps grouped per module, lanes ordered `core → operator → target`, then by
 * their leftmost layer, then by id. */
export function groupLanes(
  nodes: readonly StepNode[],
  layerOf: ReadonlyMap<string, number>,
  moduleRoles: ReadonlyMap<string, ModuleRole>,
): LaneGroup[] {
  const buckets = new Map<string, string[]>();
  for (const node of nodes) {
    const bucket = buckets.get(node.module_id);
    if (bucket) bucket.push(node.id);
    else buckets.set(node.module_id, [node.id]);
  }

  const lanes: LaneGroup[] = [];
  for (const [moduleId, ids] of buckets) {
    let minLayer = Number.POSITIVE_INFINITY;
    let maxLayer = Number.NEGATIVE_INFINITY;
    for (const id of ids) {
      const layer = layerOf.get(id) ?? 0;
      minLayer = Math.min(minLayer, layer);
      maxLayer = Math.max(maxLayer, layer);
    }
    lanes.push({
      moduleId,
      ids,
      minLayer: Number.isFinite(minLayer) ? minLayer : 0,
      maxLayer: Number.isFinite(maxLayer) ? maxLayer : 0,
    });
  }

  return lanes.sort((a, b) => {
    const roleA = ROLE_RANK[moduleRoles.get(a.moduleId) ?? "core"];
    const roleB = ROLE_RANK[moduleRoles.get(b.moduleId) ?? "core"];
    return roleA - roleB || a.minLayer - b.minLayer || byId(a.moduleId, b.moduleId);
  });
}

/**
 * Half-pull same-component nodes toward their group's median slot.
 *
 * The key it returns orders nodes *within* a column; the weight is deliberately
 * below 1 so the crossing reduction still dominates when the two disagree.
 */
export function componentAlignmentKeys(
  nodes: readonly StepNode[],
  order: ReadonlyMap<string, number>,
): Map<string, number> {
  const byComponent = new Map<string, string[]>();
  for (const node of nodes) {
    if (!node.component) continue;
    const bucket = byComponent.get(node.component);
    if (bucket) bucket.push(node.id);
    else byComponent.set(node.component, [node.id]);
  }

  const keys = new Map<string, number>();
  for (const node of nodes) keys.set(node.id, order.get(node.id) ?? 0);
  for (const ids of byComponent.values()) {
    if (ids.length < 2) continue;
    const anchor = median(ids.map((id) => order.get(id) ?? 0)) ?? 0;
    for (const id of ids) keys.set(id, (order.get(id) ?? 0) * 0.5 + anchor * 0.5);
  }
  return keys;
}

/* ---------------------------------------------------------------- placement */

/** Place every step and compute the lane band behind it. */
export function layoutPlan(input: LayoutInput): PlanLayout {
  const spacing: LayoutSpacing = { ...DEFAULT_SPACING, ...(input.spacing ?? {}) };
  if (input.nodes.length === 0) {
    return {
      placed: [],
      lanes: [],
      width: 0,
      height: 0,
      layers: new Map(),
      crossings: 0,
      cycleBroken: [],
    };
  }

  const adjacency = buildAdjacency(input.nodes, input.edges);
  const layerOf = longestPathLayers(input.nodes, adjacency.incoming);
  const seed = [...input.nodes]
    .sort((a, b) => (a.order ?? 0) - (b.order ?? 0) || byId(a.id, b.id))
    .map((node) => node.id);
  const order = orderWithinLayers(
    layerOf,
    adjacency.incoming,
    adjacency.outgoing,
    seed,
    input.passes,
  );
  const alignment = componentAlignmentKeys(input.nodes, order);
  const laneGroups = groupLanes(input.nodes, layerOf, input.moduleRoles);
  const nodeById = new Map(input.nodes.map((node) => [node.id, node]));
  const size = (id: string): StepSize => input.sizes?.get(id) ?? FALLBACK_SIZE;

  const placed: PlacedStep[] = [];
  const lanes: Lane[] = [];
  let laneX = CANVAS_PADDING;
  let tallest = 0;

  for (const group of laneGroups) {
    const columns = new Map<number, StepNode[]>();
    for (const id of group.ids) {
      const node = nodeById.get(id);
      if (!node) continue;
      const column = (layerOf.get(id) ?? 0) - group.minLayer;
      const bucket = columns.get(column);
      if (bucket) bucket.push(node);
      else columns.set(column, [node]);
    }

    const columnNumbers = [...columns.keys()].sort((a, b) => a - b);
    const widthOf = (column: number): number =>
      (columns.get(column) ?? []).reduce((widest, node) => Math.max(widest, size(node.id).width), 0);

    const offsets = new Map<number, number>();
    let cursor = 0;
    for (const column of columnNumbers) {
      offsets.set(column, cursor);
      cursor += widthOf(column) + spacing.columnGap;
    }
    const contentWidth = Math.max(0, cursor - spacing.columnGap);
    const laneWidth = contentWidth + LANE_PADDING_X * 2;

    let laneBottom = 0;
    for (const column of columnNumbers) {
      const nodes = [...(columns.get(column) ?? [])].sort((a, b) => {
        const keyA = alignment.get(a.id) ?? 0;
        const keyB = alignment.get(b.id) ?? 0;
        return keyA - keyB || byId(a.id, b.id);
      });
      const columnWidth = widthOf(column);
      let y = LANE_PADDING_TOP;
      for (const node of nodes) {
        const stepSize = size(node.id);
        placed.push({
          id: node.id,
          x: laneX + LANE_PADDING_X + (columnWidth - stepSize.width) / 2 + (offsets.get(column) ?? 0),
          y,
          width: stepSize.width,
          height: stepSize.height,
          lane: group.moduleId,
          layer: layerOf.get(node.id) ?? 0,
          column,
        });
        y += stepSize.height + spacing.rowGap;
      }
      laneBottom = Math.max(laneBottom, y - spacing.rowGap);
    }

    lanes.push({
      moduleId: group.moduleId,
      label: input.moduleLabels?.get(group.moduleId) ?? group.moduleId,
      role: input.moduleRoles.get(group.moduleId) ?? "core",
      x: laneX,
      width: laneWidth,
      height: laneBottom + LANE_PADDING_TOP + LANE_PADDING_BOTTOM,
      stepCount: group.ids.length,
    });
    tallest = Math.max(tallest, laneBottom + LANE_PADDING_TOP + LANE_PADDING_BOTTOM);
    laneX += laneWidth + spacing.laneGap;
  }

  return {
    placed,
    lanes,
    width: Math.max(0, laneX - spacing.laneGap + CANVAS_PADDING),
    height: tallest + CANVAS_PADDING,
    layers: layerOf,
    crossings: countCrossings(layerOf, adjacency.incoming, order),
    cycleBroken: adjacency.cycleBroken,
  };
}

/** Nodes that overlap because their measured boxes grew past the layout estimate. */
export function overlapping(placed: readonly PlacedStep[]): string[] {
  const hit: string[] = [];
  for (let i = 0; i < placed.length; i += 1) {
    const a = placed[i];
    if (!a) continue;
    for (let j = i + 1; j < placed.length; j += 1) {
      const b = placed[j];
      if (!b) continue;
      const overlaps =
        a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y;
      if (overlaps) {
        hit.push(a.id, b.id);
      }
    }
  }
  return [...new Set(hit)];
}
