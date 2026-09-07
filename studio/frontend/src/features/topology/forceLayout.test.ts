import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import type { Component, Point, ProjectDocument } from "@/lib/ir";
import {
  buildGraph,
  componentRef,
  DEFAULT_FILTERS,
  vertexShape,
  type LinkKind,
  type LinkView,
  type VertexShape,
  type VertexView,
} from "./logic";
import { settleLayout, vertexGeometry } from "./forceLayout";

/**
 * The contract the canvas leans on: one graph, one picture.
 *
 * The module's claim is that the settle is a function of the *sets* of vertices and links —
 * every vertex seeded, so nothing is left for d3 to jitter, and no input order load-bearing.
 * Most of what is pinned below is that claim, plus the physical promises (clearance,
 * pinning) the renderer draws against.
 *
 * Two kinds of fixture on purpose: hand-built graphs shaped to break a rule (a chain, a
 * twelve-strong clique, an island, a self-link), and the demo project off disk, which is the
 * only graph big and cyclic enough to be the one a user actually sees.
 */

const DEMO_DOCUMENT = "/home/paul/Repos/kg-build-system/studio_test_project/.kg-studio/project.ir.json";

/** The demo project as the studio loads it. Absolute path: `import.meta.url` does not
 *  resolve under this vitest config. */
function demoDocument(): ProjectDocument {
  return JSON.parse(readFileSync(DEMO_DOCUMENT, "utf8")) as ProjectDocument;
}

/**
 * How far two cards may come inside their combined clearance.
 *
 * Not zero, and the reason is measurable: the tightest pair in a twelve-strong clique ends
 * up 0.98px short of the room `forceCollide` was asked to keep — collide only relaxes twice
 * per tick against a decaying alpha, and it is the last force to have its say. The returned
 * record rounds every coordinate to a whole pixel as well, worth up to ~0.71px of distance
 * on its own. Two is therefore the tightest bound this implementation holds to; loosen
 * collide or drop it and the shortfall is tens of pixels.
 */
const CLEARANCE_TOLERANCE = 2;

/**
 * How far one vertex may move when the settled picture is settled again.
 *
 * Measured on the demo project at the module's own defaults: 96.8px at worst, 43.9px for the
 * settle after that. `ForceGraph`'s reset gesture persists the settled positions on this
 * basis, so this is what keeps a reload showing the arrangement the user just accepted. It
 * bounds the drift rather than promising a fixed point: every settle restarts at alpha 1
 * from the rounded record, so the relaxation genuinely re-runs.
 */
const RESETTLE_BOUND_PX = 110;

describe("settleLayout — the same graph lays out the same way, however it arrives", () => {
  it("produces byte-identical positions for the same vertices and links in shuffled order", () => {
    // The seed is the whole defence against d3's jitter, and jitter is not the only way
    // order can leak in: `forceLink` adds each link's pull into the two nodes' velocities in
    // array order, so the float total — and therefore the rounded picture — depends on that
    // array until the links are ordered too. Compared as serialised text, so a reordered key
    // is a failure as well as a moved coordinate.
    const graph = buildGraph(demoDocument(), DEFAULT_FILTERS);
    const chainOfNine = chain(9);
    const twelve = clique(12);
    const cases: [string, readonly VertexView[], readonly LinkView[]][] = [
      ["the demo metagraph", graph.vertices, graph.links],
      ["a chain of cards", chainOfNine.vertices, chainOfNine.links],
      ["a twelve-strong clique", twelve.vertices, twelve.links],
    ];
    for (const [name, vertices, links] of cases) {
      const once = settleLayout(vertices, links);
      const picture = JSON.stringify(once);
      for (const permutation of permutations(vertices.length, links.length)) {
        const shuffled = settleLayout(permute(vertices, permutation.vertices), permute(links, permutation.links));
        expect(`${name}: ${JSON.stringify(shuffled) === picture}`).toBe(`${name}: true`);
      }
    }
  });

  it("settles the same graph to the same points every time it is asked, even where d3 jiggles", () => {
    // `forceLink` and `forceCollide` jiggle a coordinate that is exactly zero — five cards
    // stacked on one point, or a link whose two ends are the same card. d3's generator is
    // seeded per simulation rather than from `Math.random`, so those jiggles repeat; this
    // pins that none of them reaches the user as a graph that moves between two renders.
    const five = clique(5);
    const atOnePoint = Object.fromEntries(five.vertices.map((vertex) => [vertex.id, { x: 140, y: -60 }]));
    const withSelfLink: LinkView[] = [...five.links, leg("self", "k00", "k00")];
    const seen = new Set<string>();
    for (let attempt = 0; attempt < 40; attempt += 1) {
      seen.add(JSON.stringify(settleLayout(five.vertices, withSelfLink, { seed: atOnePoint })));
    }
    expect(seen.size).toBe(1);
  });

  it("spreads a graph with no links over the fallback spiral instead of stacking it", () => {
    const loners = Array.from({ length: 20 }, (_unused, index) => card(`lone${String(index).padStart(2, "0")}`));
    const placed = settleLayout(loners, []);
    expectPlaced(placed, loners);
    const points = new Set(Object.values(placed).map((point) => `${point.x},${point.y}`));
    expect(points.size).toBe(loners.length);
    // The spiral is centred on the origin and the centring forces pull toward the middle of
    // the panel, so a graph nobody placed ends up near the middle — 55px from it, measured —
    // rather than at the origin it started from (713px away) or on top of itself.
    expect(centroidOffset(placed, 1200 / 2, 760 / 2)).toBeLessThan(150);
    expect(Object.values(placed).some((point) => point.x === 0 && point.y === 0)).toBe(false);
  });
});

describe("settleLayout — a seed the document cannot express", () => {
  it("re-seeds a vertex stored as NaN and still places every vertex at a whole point", () => {
    // A NaN in a stored position is a corrupt payload, not a hand placement. d3 ignores a
    // non-finite point in its quadtrees and gives that node its own starting point, so the
    // bad seed costs one vertex its placement and nothing else: every entry comes back,
    // whole and finite, and the settle is repeatable.
    const graph = buildGraph(demoDocument(), DEFAULT_FILTERS);
    const stored = seedFrom(graph.vertices, 240, 180);
    const settleWith = (broken: Point): Record<string, Point> =>
      settleLayout(graph.vertices, graph.links, { seed: { ...stored, documented: broken } });
    const brokenX = settleWith({ x: Number.NaN, y: 180 });
    const brokenY = settleWith({ x: 240, y: Number.NaN });
    const brokenBoth = settleWith({ x: Number.NaN, y: Number.NaN });
    for (const placed of [brokenX, brokenY, brokenBoth]) {
      expectPlaced(placed, graph.vertices);
    }
    // One broken coordinate throws away both of them — d3 replaces the whole starting point,
    // not the bad axis of it — so no flavour can land the vertex somewhere of its own. Were
    // the sound coordinate kept, `brokenX` and `brokenY` would disagree.
    expect(brokenY).toEqual(brokenX);
    expect(brokenBoth).toEqual(brokenX);
  });

  it("keeps a pinned vertex whose seed is broken, placed at the spiral fallback", () => {
    // A pinned vertex keeps `fx`/`fy` for the whole settle, so a non-finite seed has to be
    // corrected before it is pinned — rescuing it afterwards is impossible. Falling back to
    // the spiral keeps the card on the canvas; dropping the entry would make a hand
    // placement silently disappear, which is the worst failure for the thing the user did
    // most deliberately.
    const graph = buildGraph(demoDocument(), DEFAULT_FILTERS);
    const placed = settleLayout(graph.vertices, graph.links, {
      seed: { documented: { x: Number.NaN, y: 20 } },
      pinned: new Set(["documented"]),
    });
    expectPlaced(placed, graph.vertices);
  });

  it("refuses to hand an infinite seed to the simulation", () => {
    // `JSON.parse` yields `Infinity` for `1e999`, and `views.topology` flows straight into
    // the seed. `Number.isNaN` does not catch it, and d3's quadtree then subdivides for
    // ever trying to separate two infinite coordinates — it exhausts the heap and the tab
    // dies. This is the guard against that, so it is asserted for every broken axis.
    const graph = buildGraph(demoDocument(), DEFAULT_FILTERS);
    for (const bad of [
      { x: Number.POSITIVE_INFINITY, y: 300 },
      { x: 300, y: Number.POSITIVE_INFINITY },
      { x: Number.NEGATIVE_INFINITY, y: Number.NEGATIVE_INFINITY },
    ]) {
      const placed = settleLayout(graph.vertices, graph.links, { seed: { documented: bad } });
      expectPlaced(placed, graph.vertices);
    }
  });
});

describe("settleLayout — cards keep the room they are drawn in", () => {
  it("never lets two cards of a chain come inside their combined clearance", () => {
    const { vertices, links } = chain(9);
    const placed = settleLayout(vertices, links);
    expectPlaced(placed, vertices);
    expect(tightestClearance(vertices, placed).shortfall).toBeGreaterThanOrEqual(-CLEARANCE_TOLERANCE);
  });

  it("never lets twelve mutually connected cards pile onto one another", () => {
    // The worst case the collide force has: every card is a neighbour of every other, so no
    // amount of link shortening can buy anybody room.
    const { vertices, links } = clique(12);
    const placed = settleLayout(vertices, links);
    expectPlaced(placed, vertices);
    expect(tightestClearance(vertices, placed).shortfall).toBeGreaterThanOrEqual(-CLEARANCE_TOLERANCE);
  });

  it("keeps the demo metagraph's cards clear of each other", () => {
    const graph = buildGraph(demoDocument(), DEFAULT_FILTERS);
    const placed = settleLayout(graph.vertices, graph.links);
    expectPlaced(placed, graph.vertices);
    expect(tightestClearance(graph.vertices, placed).shortfall).toBeGreaterThanOrEqual(-CLEARANCE_TOLERANCE);
  });

  it("places a vertex no link reaches, and clear of the cluster it is drawn beside", () => {
    const main = clique(6);
    const island = card("island");
    const vertices = [...main.vertices, island];
    const placed = settleLayout(vertices, main.links);
    expectPlaced(placed, vertices);
    const at = settledPoint(placed, "island");
    for (const other of main.vertices) {
      const neighbour = settledPoint(placed, other.id);
      const owed = vertexGeometry(island).clearance + vertexGeometry(other).clearance;
      expect(Math.hypot(at.x - neighbour.x, at.y - neighbour.y)).toBeGreaterThanOrEqual(owed - CLEARANCE_TOLERANCE);
    }
  });
});

describe("settleLayout — hand placements", () => {
  it("holds a pinned vertex at exactly its seed position while the rest settles around it", () => {
    const { vertices, links } = clique(12);
    const seed = { k03: { x: 777, y: -42 } };
    const pinned = settleLayout(vertices, links, { pinned: new Set(["k03"]), seed });
    expect(pinned["k03"]).toEqual({ x: 777, y: -42 });
    // Not a vacuous pass: the pin has to have cost somebody else their place.
    const unpinned = settleLayout(vertices, links, { seed });
    const moved = vertices
      .filter((vertex) => vertex.id !== "k03")
      .map((vertex) => distance(settledPoint(pinned, vertex.id), settledPoint(unpinned, vertex.id)));
    expect(Math.min(...moved)).toBeGreaterThan(0);
    expect(Math.max(...moved)).toBeGreaterThan(50);
  });

  it("freezes the whole picture when every vertex is pinned, whatever that costs in overlap", () => {
    // Pinned means the user placed it, so the physics may not answer back. These cards are
    // parked 40px apart against a clearance of 50, and every one of them stays put.
    const { vertices, links } = clique(12);
    const byHand = Object.fromEntries(vertices.map((vertex, index) => [vertex.id, { x: index * 40, y: 0 }]));
    const placed = settleLayout(vertices, links, { pinned: new Set(vertices.map((vertex) => vertex.id)), seed: byHand });
    expect(placed).toEqual(byHand);
  });

  it("still returns a whole point for a pinned vertex the seed says nothing about", () => {
    // `ForceGraph` pins ids as they are dragged; a pin with nothing behind it has to land on
    // the fallback spiral and still be reported, since a missing entry is a card the
    // renderer cannot show at all.
    const { vertices, links } = clique(6);
    const placed = settleLayout(vertices, links, { pinned: new Set(["k05"]) });
    expectPlaced(placed, vertices);
  });

  it("rounds a hand placement onto the same whole-pixel grid as every other position", () => {
    // The reset gesture persists what the settle returns, so this rounding is what reaches
    // the document — a pinned half-pixel has to come back whole.
    const graph = buildGraph(demoDocument(), DEFAULT_FILTERS);
    const placed = settleLayout(graph.vertices, graph.links, {
      pinned: new Set(["documented"]),
      seed: { documented: { x: -1234.5, y: 987.25 } },
    });
    expect(placed["documented"]).toEqual({ x: -1234, y: 987 });
    expectPlaced(placed, graph.vertices);
  });
});

describe("settleLayout — a graph that is barely a graph", () => {
  it("returns an empty record for a graph with no vertices, links or not", () => {
    expect(settleLayout([], [])).toEqual({});
    expect(settleLayout([], [leg("a", "ghost", "phantom")])).toEqual({});
  });

  it("places a lone vertex at one whole point near the middle of the panel", () => {
    // Its fallback seed is `(20, 0)`, some 694px from the middle of a 1200x760 panel; the
    // weak centring forces are the only thing that moves it, and a lone card parked in the
    // corner would read as a rendering bug.
    const alone = [card("alone")];
    const placed = settleLayout(alone, []);
    expectPlaced(placed, alone);
    expect(centroidOffset(placed, 1200 / 2, 760 / 2)).toBeLessThan(100);
  });

  it("ignores a link that names a vertex the graph does not draw", () => {
    // A filtered tier or a dangling endpoint. Pulling on an id with no node behind it is how
    // d3's `forceLink` throws, so such a leg is dropped before it gets there — dropped
    // completely, which is pinned here by comparing against the same graph with no leg at all.
    const vertices = [card("site"), card("unit")];
    expect(settleLayout(vertices, [leg("a", "site", "gone")])).toEqual(settleLayout(vertices, []));
    expect(settleLayout(vertices, [leg("a", "gone", "also-gone")])).toEqual(settleLayout(vertices, []));

    // The demo metagraph with the category that several legs lean on taken out from under
    // them: every vertex still drawn still gets a place.
    const graph = buildGraph(demoDocument(), DEFAULT_FILTERS);
    const withoutCategory = graph.vertices.filter((vertex) => vertex.id !== "documented");
    expect(withoutCategory.length).toBeLessThan(graph.vertices.length);
    expectPlaced(settleLayout(withoutCategory, graph.links), withoutCategory);
  });

  it("settles a link that names the same vertex at both ends", () => {
    // `buildGraph` never emits one, so this is the guard for a stale or hand-made graph: a
    // zero-length link has no direction, and d3's jiggle must not become a NaN.
    const vertices = [card("loop"), card("site"), card("unit")];
    const links = [leg("self", "loop", "loop"), leg("in", "site", "loop"), leg("out", "loop", "unit")];
    const placed = settleLayout(vertices, links);
    expectPlaced(placed, vertices);
    expect(tightestClearance(vertices, placed).shortfall).toBeGreaterThanOrEqual(-CLEARANCE_TOLERANCE);
  });
});

describe("settleLayout — the loop is at rest", () => {
  it("settles from its own output without moving any vertex by more than 110px", () => {
    const graph = buildGraph(demoDocument(), DEFAULT_FILTERS);
    const settled = settleLayout(graph.vertices, graph.links);
    const again = settleLayout(graph.vertices, graph.links, { seed: settled });
    expectPlaced(again, graph.vertices);
    for (const vertex of graph.vertices) {
      expect(distance(settledPoint(again, vertex.id), settledPoint(settled, vertex.id))).toBeLessThanOrEqual(
        RESETTLE_BOUND_PX,
      );
    }
    // Drift is allowed; crowding is not. The re-settled picture is the one a reload shows, so
    // it has to be as readable as the first.
    expect(tightestClearance(graph.vertices, again).shortfall).toBeGreaterThanOrEqual(-CLEARANCE_TOLERANCE);
  });
});

describe("vertexGeometry — the room a card claims", () => {
  it("draws a node card with a bigger ring than the edge card standing in for a link", () => {
    const node = vertexGeometry(card("site", "node", 4));
    const edge = vertexGeometry(card("has_unit", "edge", 4));
    expect(node.radius).toBeGreaterThan(edge.radius);
    expect(edge.radius).toBe(15);
    expect(node.clearance).toBeGreaterThan(edge.clearance);
  });

  it("grows a node card with its slots and stops growing at the cap", () => {
    // The growth is the point — a card with thirty slots has a label and a crowd of links to
    // make room for — and so is the cap, since one huge circle would shove the graph aside.
    let previous = Number.NEGATIVE_INFINITY;
    for (const slots of [0, 1, 3, 5, 8]) {
      const radius = vertexGeometry(card(`n${slots}`, "node", slots)).radius;
      expect(radius).toBeGreaterThan(previous);
      previous = radius;
    }
    expect(vertexGeometry(card("bare", "node", 0)).radius).toBe(20);
    const capped = [9, 12, 40].map((slots) => vertexGeometry(card(`c${slots}`, "node", slots)).radius);
    expect(capped).toEqual([33, 33, 33]);
    expect(vertexGeometry(card("crowded", "node", 40)).clearance).toBeGreaterThan(
      vertexGeometry(card("bare", "node", 0)).clearance,
    );
  });

  it("gives a category node more room and leaves an edge card the size it is drawn at", () => {
    const concrete = vertexGeometry(card("site", "node", 4));
    const category = vertexGeometry(card("documented", "node", 4, "category"));
    expect(category.radius).toBe(concrete.radius + 3);
    expect(category.clearance).toBeGreaterThan(concrete.clearance);
    // An edge category is drawn as the same small diamond as a concrete one, so it claims the
    // same small ring whatever its tier.
    expect(vertexGeometry(card("related", "edge", 0, "category")).radius).toBe(15);
  });

  it("claims room for whichever caption is longer, the card's name or its relation label", () => {
    const title = "a".repeat(40);
    const titled = vertexGeometry(captioned(card("site", "node", 0), title));
    expect(titled.clearance).toBe(title.length * 3.6 + 14);
    expect(titled.clearance).toBeGreaterThan(titled.radius + 30);

    const label = "L".repeat(30);
    expect(vertexGeometry(edgeCard("reported_for", label, "short")).clearance).toBe(label.length * 3.6 + 14);
    // The wider of the two wins, whichever side it is on.
    expect(vertexGeometry(edgeCard("reported_for", "S", "t".repeat(20))).clearance).toBe(20 * 3.6 + 14);
  });

  it("never claims less than the ring plus a gutter, whatever the caption says", () => {
    const bare = vertexGeometry(captioned(card("site", "node", 0), ""));
    expect(bare.clearance).toBe(bare.radius + 30);
    expect(vertexGeometry(edgeCard("related", null, "")).clearance).toBe(44);
    expect(vertexGeometry(edgeCard("has_unit", "HAS", "has_unit")).clearance).toBe(44);
  });
});

/* ------------------------------------------------------------------------- fixtures */

function component(id: string, kind: "node" | "edge", tier: "template" | "category" | "concrete"): Component {
  return {
    id,
    kind,
    tier,
    declaration_name: id,
    name: id,
    description: null,
    label: null,
    parent: null,
    mixins: [],
    source: null,
    target: null,
    properties: [],
    annotations: [],
  };
}

/** A vertex the settle can be pointed at on its own, with a chosen number of slots. */
function card(
  id: string,
  shape: VertexShape = "node",
  slots = 0,
  tier: "category" | "concrete" = "concrete",
): VertexView {
  const item = {
    ...component(id, shape, tier),
    properties: Array.from({ length: slots }, (_unused, index) => ({
      name: `slot_${index}`,
      logical_type: { kind: "unit", name: "str" } as const,
      description: null,
      optional: false,
    })),
  };
  return {
    id,
    ref: componentRef(id),
    component: item,
    title: id,
    subtitle: id,
    position: { x: 0, y: 0 },
    shape: vertexShape(item),
    endpoints: { source: item.source ?? null, target: item.target ?? null },
  };
}

/** The same card under a different caption — that is what the clearance has to make room for. */
const captioned = (vertex: VertexView, title: string): VertexView => ({ ...vertex, title });

/** An edge card with both captions under the caller's control: the shape only reads `label`. */
function edgeCard(id: string, label: string | null, title: string): VertexView {
  return { ...card(id, "edge", 0), title, component: { ...component(id, "edge", "concrete"), label } };
}

function leg(id: string, source: string, target: string, kind: LinkKind = "relation"): LinkView {
  return {
    id,
    source,
    target,
    kind,
    role: kind === "hierarchy" ? "parent" : "out",
    label: "",
    ref: componentRef(source),
  };
}

/** `node card → edge card → node card …`, `count` cards long. */
function chain(count: number): { vertices: VertexView[]; links: LinkView[] } {
  const name = (index: number): string => `v${String(index).padStart(2, "0")}`;
  const vertices = Array.from({ length: count }, (_unused, index) =>
    card(name(index), index % 2 === 1 ? "edge" : "node"),
  );
  const links: LinkView[] = [];
  for (let index = 2; index < count; index += 1) links.push(leg(`l${index}`, name(index - 2), name(index)));
  return { vertices, links };
}

/** Every vertex joined to every other — the densest thing collide has to untangle. */
function clique(count: number): { vertices: VertexView[]; links: LinkView[] } {
  const name = (index: number): string => `k${String(index).padStart(2, "0")}`;
  const vertices = Array.from({ length: count }, (_unused, index) => card(name(index)));
  const links: LinkView[] = [];
  for (let a = 0; a < count; a += 1) {
    for (let b = a + 1; b < count; b += 1) links.push(leg(`kl:${a}:${b}`, name(a), name(b)));
  }
  return { vertices, links };
}

/* ------------------------------------------------------------------------- assertions */

/** The settled point of one vertex — returning one at all is part of every assertion. */
function settledPoint(placed: Record<string, Point>, id: string): Point {
  const point = placed[id];
  if (!point) throw new Error(`settleLayout returned no position for ${id}`);
  return point;
}

/** Every vertex got an entry, and every entry is a whole, finite point. */
function expectPlaced(placed: Record<string, Point>, vertices: readonly VertexView[]): void {
  expect(Object.keys(placed).sort()).toEqual(vertices.map((vertex) => vertex.id).sort());
  for (const point of Object.values(placed)) {
    expect(Number.isInteger(point.x) && Number.isInteger(point.y)).toBe(true);
  }
}

const distance = (a: Point, b: Point): number => Math.hypot(a.x - b.x, a.y - b.y);

/** How far the settled centroid sits from a point in the panel. */
function centroidOffset(placed: Record<string, Point>, x: number, y: number): number {
  const points = Object.values(placed);
  const mean = (pick: (point: Point) => number): number =>
    points.reduce((total, point) => total + pick(point), 0) / points.length;
  return Math.hypot(mean((point) => point.x) - x, mean((point) => point.y) - y);
}

/** The worst pair, as how far short of their combined clearance they ended up. */
function tightestClearance(
  vertices: readonly VertexView[],
  placed: Record<string, Point>,
): { shortfall: number; pair: string } {
  let shortfall = Number.POSITIVE_INFINITY;
  let pair = "";
  for (const [index, left] of vertices.entries()) {
    for (const right of vertices.slice(index + 1)) {
      const owed = vertexGeometry(left).clearance + vertexGeometry(right).clearance;
      const gap = distance(settledPoint(placed, left.id), settledPoint(placed, right.id)) - owed;
      if (gap < shortfall) {
        shortfall = gap;
        pair = `${left.id}/${right.id}`;
      }
    }
  }
  return { shortfall, pair };
}

/** A seed putting every vertex somewhere different, for the tests that need a placement. */
function seedFrom(vertices: readonly VertexView[], x: number, y: number): Record<string, Point> {
  return Object.fromEntries(vertices.map((vertex, index) => [vertex.id, { x: x + index * 30, y: y - index * 20 }]));
}

/* --------------------------------------------------------------------------- reorder */

/** A fixed-seed shuffle: a determinism test that itself moved about would be worthless. */
function shuffled(length: number, salt: number): number[] {
  const out = [...Array.from({ length }, (_unused, index) => index)];
  let seed = (0x9e3779b9 ^ salt) >>> 0;
  const next = (): number => {
    seed = (seed * 1_103_515_245 + 12_345) % 2_147_483_648;
    return seed / 2_147_483_648;
  };
  for (let index = out.length - 1; index > 0; index -= 1) {
    const swap = Math.floor(next() * (index + 1));
    const hold = out[index] as number;
    out[index] = out[swap] as number;
    out[swap] = hold;
  }
  return out;
}

function permute<T>(items: readonly T[], order: readonly number[]): T[] {
  return order.map((index) => items[index] as T);
}

const reverse = (length: number): number[] => [...Array.from({ length }, (_unused, index) => length - 1 - index)];

/** Reorderings enough that no code path can lean on the payload's order unnoticed. */
function permutations(vertexCount: number, linkCount: number): { vertices: number[]; links: number[] }[] {
  return [
    { vertices: reverse(vertexCount), links: reverse(linkCount) },
    { vertices: shuffled(vertexCount, 1), links: shuffled(linkCount, 2) },
    { vertices: shuffled(vertexCount, 3), links: shuffled(linkCount, 4) },
    { vertices: shuffled(vertexCount, 7), links: shuffled(linkCount, 8) },
  ];
}
