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
 * 3. **Columns** — `x` is evaluation depth and comes from one column grid shared by
 *    the whole canvas, so two steps in the same layer get the same `x` even when
 *    neither depends on the other. Numbering columns *inside* a module instead would
 *    advance every module's depth on its own, so two modules at equal depth could
 *    never line up and an independent sibling would sit to the right of a step it
 *    does not consume — reading as a sequence that is not there.
 * 4. **One vertical field** — every step of every module lives in the same field: a
 *    column starts at the canvas' top padding and its steps stack downwards from
 *    there. Offsetting a module downwards in its own band pushed that module's steps
 *    below steps that consume them, so a pipeline that flows rightward read as a fold
 *    downward. Which module a step belongs to is carried by its card colour, not by
 *    geometry.
 * 5. **Alignment** — nodes carrying the same IR ref are pulled halfway toward their
 *    group's median slot before packing, so one component can be followed with the
 *    eye from aggregate through operator to export; the same half-pull then runs over
 *    each module's steps inside their own column, so a module stays one continuous run
 *    of its own colour rather than interleaving with its neighbours.
 */

import type {
  LayoutSpacing,
  PlacedStep,
  PlanLayout,
  StepEdge,
  StepNode,
} from "./types";

export const DEFAULT_SPACING: LayoutSpacing = {
  columnGap: 96,
  rowGap: 24,
};

/** Margin around the field. Every column starts at this `y`, so nothing in the
 * picture sits lower than it has to because of which module it belongs to. */
export const CANVAS_PADDING = 32;

export interface StepSize {
  readonly width: number;
  readonly height: number;
}

export interface LayoutInput {
  readonly nodes: readonly StepNode[];
  readonly edges: readonly StepEdge[];
  readonly sizes?: ReadonlyMap<string, StepSize>;
  readonly spacing?: Partial<LayoutSpacing>;
  readonly passes?: number;
}

const FALLBACK_SIZE: StepSize = { width: 232, height: 112 };

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

/* --------------------------------------------------------------- alignment */

/**
 * `group → member ids` for every group with more than one member.
 *
 * Members keep the order the node list hands over (the contract's declaration order),
 * so a group's median never depends on a map's insertion order.
 */
function alignmentGroups(
  nodes: readonly StepNode[],
  groupOf: (node: StepNode) => string | null | undefined,
): Map<string, string[]> {
  const groups = new Map<string, string[]>();
  for (const node of nodes) {
    const group = groupOf(node);
    if (!group) continue;
    const bucket = groups.get(group);
    if (bucket) bucket.push(node.id);
    else groups.set(group, [node.id]);
  }
  return new Map([...groups].filter(([, ids]) => ids.length > 1));
}

/**
 * Half-pull every member of a group toward the median key of that group.
 *
 * The keys returned order nodes *within* a column. One pass is mild by design — it
 * leans a group toward its median without overriding the crossing reduction — and it is
 * monotone inside a group, so it gathers a group's steps without reordering them among
 * themselves.
 */
function pullToMedianKeys(
  keys: ReadonlyMap<string, number>,
  groups: Iterable<readonly string[]>,
): Map<string, number> {
  const out = new Map(keys);
  for (const ids of groups) {
    const anchor = median(ids.map((id) => keys.get(id) ?? 0)) ?? 0;
    for (const id of ids) out.set(id, (keys.get(id) ?? 0) * 0.5 + anchor * 0.5);
  }
  return out;
}

/** Same-component affinity: the steps of one IR ref reach for one slot. */
export function componentAlignmentKeys(
  nodes: readonly StepNode[],
  order: ReadonlyMap<string, number>,
): Map<string, number> {
  return pullToMedianKeys(order, alignmentGroups(nodes, (node) => node.component).values());
}

/** Passes of the module pull. Each halves a block's spread, so eight leave it a 256th
 * of its original size — small enough that two modules cannot still interleave. */
const MODULE_PULL_PASSES = 8;

/**
 * Same-module affinity: the identical half-pull, run over each module's steps within
 * one column, on top of the component pull.
 *
 * Repeated, because one pass cannot group anything: it halves a block's spread, which
 * is wider than the gap between two blocks' medians, so the two still interleave.
 * Column-local, because an anchor taken from a module's steps in *every* column says
 * nothing about where that module belongs in *this* one — measured on the 60-step plan
 * a whole-canvas anchor grouped the columns just as well but paid for it with 60 drawn
 * crossings instead of 19, dragging blocks past the neighbours the barycentre had put
 * beside them.
 *
 * The pull is monotone inside a group, so the component pull and the crossing reduction
 * still order the steps *within* a block, and a module can only ever move its own
 * steps. Applied last, it decides which module's block a column shows first, which is
 * what keeps each module one continuous run of its own colour down the canvas.
 */
export function moduleAlignmentKeys(
  nodes: readonly StepNode[],
  layerOf: ReadonlyMap<string, number>,
  keys: ReadonlyMap<string, number>,
): Map<string, number> {
  // One group per (column, module); the separator cannot occur in a layer number or
  // a module id, so no two pairs can collide. Materialised, because the passes below
  // walk it more than once.
  const groups = [...alignmentGroups(nodes, (node) => `${layerOf.get(node.id) ?? 0}\u0000${node.module_id}`).values()];
  let settled = new Map(keys);
  for (let pass = 0; pass < MODULE_PULL_PASSES; pass += 1) {
    settled = pullToMedianKeys(settled, groups);
  }
  return settled;
}

/* ------------------------------------------------------------------ columns */

export interface ColumnGrid {
  /** `layer → left edge of its column`, relative to the grid origin. */
  readonly offsets: ReadonlyMap<number, number>;
  /** `layer → width of its column`, the widest node anywhere in that layer. */
  readonly widths: ReadonlyMap<number, number>;
  /** `layer → ordinal of its column`, so `column` counts occupied layers from 0. */
  readonly columns: ReadonlyMap<number, number>;
  /** Width of the whole grid: the last column's right edge, padding excluded. */
  readonly width: number;
}

/**
 * One column grid for the entire canvas: a layer's column is as wide as the widest
 * node in that layer *wherever it lives*, and the offsets accumulate once. That is
 * what makes `x` comparable across modules.
 */
export function columnGrid(
  nodes: readonly StepNode[],
  layerOf: ReadonlyMap<string, number>,
  size: (id: string) => StepSize,
  spacing: LayoutSpacing,
): ColumnGrid {
  const widths = new Map<number, number>();
  for (const node of nodes) {
    const layer = layerOf.get(node.id) ?? 0;
    widths.set(layer, Math.max(widths.get(layer) ?? 0, size(node.id).width));
  }

  const offsets = new Map<number, number>();
  const columns = new Map<number, number>();
  let cursor = 0;
  let ordinal = 0;
  for (const layer of [...widths.keys()].sort((a, b) => a - b)) {
    offsets.set(layer, cursor);
    columns.set(layer, ordinal);
    cursor += (widths.get(layer) ?? 0) + spacing.columnGap;
    ordinal += 1;
  }

  return {
    offsets,
    widths,
    columns,
    width: Math.max(0, cursor - spacing.columnGap),
  };
}

/* ---------------------------------------------------------------- placement */

/** Place every step of every module in one vertical field on the global column grid. */
export function layoutPlan(input: LayoutInput): PlanLayout {
  const spacing: LayoutSpacing = { ...DEFAULT_SPACING, ...(input.spacing ?? {}) };
  if (input.nodes.length === 0) {
    return {
      placed: [],
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
  const alignment = moduleAlignmentKeys(
    input.nodes,
    layerOf,
    componentAlignmentKeys(input.nodes, order),
  );
  const size = (id: string): StepSize => input.sizes?.get(id) ?? FALLBACK_SIZE;

  const grid = columnGrid(input.nodes, layerOf, size, spacing);

  const byLayer = new Map<number, StepNode[]>();
  for (const node of input.nodes) {
    const layer = layerOf.get(node.id) ?? 0;
    const bucket = byLayer.get(layer);
    if (bucket) bucket.push(node);
    else byLayer.set(layer, [node]);
  }

  const placed: PlacedStep[] = [];
  let fieldBottom = 0;
  for (const layer of [...byLayer.keys()].sort((a, b) => a - b)) {
    // The affinity keys order the column and `byId` closes the comparator, so the
    // packing cannot depend on the payload's arrival order.
    const nodes = [...(byLayer.get(layer) ?? [])].sort((a, b) => {
      const keyA = alignment.get(a.id) ?? 0;
      const keyB = alignment.get(b.id) ?? 0;
      return keyA - keyB || byId(a.id, b.id);
    });
    const columnWidth = grid.widths.get(layer) ?? 0;
    // Every column starts at the same top edge: one field, no module offsets.
    let y = CANVAS_PADDING;
    for (const node of nodes) {
      const stepSize = size(node.id);
      placed.push({
        id: node.id,
        x: CANVAS_PADDING + (grid.offsets.get(layer) ?? 0) + (columnWidth - stepSize.width) / 2,
        y,
        width: stepSize.width,
        height: stepSize.height,
        lane: node.module_id,
        layer,
        column: grid.columns.get(layer) ?? layer,
      });
      y += stepSize.height + spacing.rowGap;
    }
    fieldBottom = Math.max(fieldBottom, y - spacing.rowGap);
  }

  return {
    placed,
    width: CANVAS_PADDING + grid.width + CANVAS_PADDING,
    height: fieldBottom + CANVAS_PADDING,
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
