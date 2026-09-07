/**
 * The force layout behind the topology graph.
 *
 * `d3-force` computes the positions; React owns the DOM. The force model follows the
 * metagraph the framework itself renders (`kg_build_system/modules/targets/meta_graph/render.py`):
 * links pull with a per-kind distance and strength, repulsion scales with the vertex so
 * large nodes claim room for their labels, centring is weak so the graph may spread but
 * stays near the middle, and collide keeps labels readable.
 *
 * Two decisions differ from a stock d3 force graph, both because this is an editor:
 *
 * 1. **It settles to a result rather than animating forever.** `settleLayout` runs the
 *    simulation to rest synchronously and returns points. Typing a slot name changes no
 *    vertex, so nothing recomputes, and the graph cannot shuffle out from under the
 *    pointer mid-edit. The renderer animates the transition when positions do change.
 * 2. **It is deterministic.** d3 jitters a node only when its seed is `NaN`, so every
 *    vertex is seeded — from a stored position, the layered layout, or a fixed
 *    phyllotaxis spiral — and the same document lays out identically every time. A test
 *    pins this, because a graph that moves on reload is indistinguishable from a bug.
 */

import {
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from "d3-force";

import type { Point } from "@/lib/ir";
import type { LinkView, VertexView } from "./logic";

/** How big a vertex is drawn, which is what the forces have to make room for. */
export interface VertexGeometry {
  readonly radius: number;
  /** The label needs more clearance than the shape itself. */
  readonly clearance: number;
}

export interface ForceOptions {
  /** Where the graph is drawn, so the centring forces pull toward its middle. */
  readonly width?: number;
  readonly height?: number;
  /** Positions to start from — a stored drag or the layered layout. */
  readonly seed?: Readonly<Record<string, Point>>;
  /** Ids the user placed by hand; pinned for the whole settle, exactly like d3 dragging. */
  readonly pinned?: ReadonlySet<string>;
  /** Default 320, which is past the point the reference's own decay reaches rest. */
  readonly ticks?: number;
  readonly geometry?: (vertex: VertexView) => VertexGeometry;
}

/**
 * A node's drawn radius. A component with many slots gets a bigger circle so its label
 * and its links do not collide, in the same spirit as the framework sizing by record
 * count; an edge component stays small, since it stands for a link.
 */
export function vertexGeometry(vertex: VertexView): VertexGeometry {
  // The label is drawn under the shape and must not collide with a neighbour's, so the
  // clearance a node claims is the wider of its ring and half its caption.
  const caption = Math.max(vertex.title.length, vertex.component.label?.length ?? 0);
  const labelHalf = caption * 3.6 + 14;
  if (vertex.shape === "edge") {
    return { radius: 15, clearance: Math.max(44, labelHalf) };
  }
  const slots = vertex.component.properties?.length ?? 0;
  const tierBoost = vertex.component.tier === "category" ? 3 : 0;
  const radius = 20 + Math.min(13, slots * 1.6) + tierBoost;
  return { radius, clearance: Math.max(radius + 30, labelHalf) };
}

/**
 * The link's pull. A hierarchy arrow is metadata about the graph rather than a fact in
 * it, so it holds loosely and far apart; a relationship leg is the structure the user is
 * drawing and is held nearest, so a card sits close to the nodes it joins.
 */
const LINK_FORCE: Record<
  LinkView["kind"],
  { readonly distance: number; readonly strength: number }
> = {
  relation: { distance: 132, strength: 0.5 },
  category: { distance: 150, strength: 0.28 },
  hierarchy: { distance: 210, strength: 0.1 },
};

interface FlowNode extends SimulationNodeDatum {
  readonly id: string;
  readonly radius: number;
  readonly clearance: number;
  readonly pinned: boolean;
}

interface FlowLink extends SimulationLinkDatum<FlowNode> {
  readonly link: LinkView;
}

/**
 * A total order over links that never depends on insertion order or on the runtime's
 * collation — the same reason `logic.ts` refuses to use `localeCompare` in its layout.
 */
const byString = (left: string, right: string): number => (left < right ? -1 : left > right ? 1 : 0);

const byLink = (left: LinkView, right: LinkView): number =>
  byString(left.source, right.source) || byString(left.target, right.target) || byString(left.id, right.id);

/**
 * A deterministic spread for a vertex with no seed. The golden-angle spiral places a
 * first graph without overlap, and depends only on the vertex's position in id order.
 */
function phyllotaxis(index: number): Point {
  const angle = index * 2.399963229728653;
  const distance = 26 * Math.sqrt(index + 0.6);
  return { x: distance * Math.cos(angle), y: distance * Math.sin(angle) };
}

/** Positions the graph should be drawn at, keyed by vertex id. */
export function settleLayout(
  vertices: readonly VertexView[],
  links: readonly LinkView[],
  options: ForceOptions = {},
): Record<string, Point> {
  const {
    width = 1200,
    height = 760,
    seed = {},
    pinned,
    ticks = 320,
    geometry = vertexGeometry,
  } = options;

  if (vertices.length === 0) return {};

  // id order drives both the seed and the spiral, so input order cannot change output.
  // The comparator is deliberately locale-free: `localeCompare` reorders ids such as
  // `Alpha` against `beta` differently on different ICU builds, which would reassign the
  // spiral indices and lay the same document out differently on another machine.
  const ordered = [...vertices].sort((left, right) => byString(left.id, right.id));

  const nodes: FlowNode[] = ordered.map((vertex, index) => {
    const shape = geometry(vertex);
    const spiral = phyllotaxis(index);
    // A non-finite seed must never reach d3: its quadtree subdivides forever trying to
    // separate two infinite coordinates and exhausts the heap, and a pinned non-finite
    // coordinate would drop the vertex from the result entirely — a card that silently
    // vanishes. `JSON.parse` turns `1e999` into `Infinity`, so this is document input,
    // not a theoretical one.
    const requested = seed[vertex.id];
    const from =
      requested && Number.isFinite(requested.x) && Number.isFinite(requested.y)
        ? requested
        : spiral;
    const isPinned = pinned?.has(vertex.id) ?? false;
    return {
      id: vertex.id,
      radius: shape.radius,
      clearance: shape.clearance,
      pinned: isPinned,
      x: from.x,
      y: from.y,
      // d3 honours fx/fy absolutely, which is how a hand-placed card survives a settle.
      ...(isPinned ? { fx: from.x, fy: from.y } : {}),
    };
  });

  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  // `buildGraph` only emits a leg when both endpoints are drawn, so for a graph straight
  // from it this filter is a no-op. It earns its keep for a graph built elsewhere or
  // stale: d3 throws on a link naming an id the simulation does not have.
  //
  // The order is part of the result: `forceLink` adds each link's pull into the two nodes'
  // velocities in array order, so a shuffled `links` sums the same terms in a different
  // order and lands on a slightly different float — visible as several pixels after the
  // rounding below. Sorting on the link's own content keeps the settle a function of the
  // graph rather than of the order `buildGraph` emitted it in.
  const flowLinks: FlowLink[] = links
    .filter((link) => nodeById.has(link.source) && nodeById.has(link.target))
    .sort(byLink)
    .map((link) => ({ source: link.source, target: link.target, link }));

  const simulation = forceSimulation<FlowNode>(nodes)
    .force(
      "link",
      forceLink<FlowNode, FlowLink>(flowLinks)
        .id((node) => node.id)
        .distance((entry) => LINK_FORCE[entry.link.kind].distance)
        .strength((entry) => LINK_FORCE[entry.link.kind].strength),
    )
    .force(
      "charge",
      forceManyBody<FlowNode>()
        .strength((node) => -300 - 16 * node.radius)
        .distanceMax(1800),
    )
    .force("collide", forceCollide<FlowNode>((node) => node.clearance).iterations(2))
    // Weak centring rather than forceCenter: the graph may spread, but it stays near the
    // middle of the panel instead of drifting away as it settles.
    .force("x", forceX<FlowNode>(width / 2).strength(0.035))
    .force("y", forceY<FlowNode>(height / 2).strength(0.05))
    .stop();

  for (let tick = 0; tick < ticks; tick += 1) simulation.tick();

  const positions: Record<string, Point> = {};
  for (const node of nodes) {
    const x = node.x ?? 0;
    const y = node.y ?? 0;
    // Non-finite positions would poison the document, so they are dropped rather than
    // rounded; the renderer falls back to the seed for that vertex.
    if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
    positions[node.id] = { x: Math.round(x), y: Math.round(y) };
  }
  return positions;
}
