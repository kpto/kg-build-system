import { describe, expect, it } from "vitest";

import type { ModuleRole, PlacedStep, StepEdge, StepNode } from "./types";
import {
  buildAdjacency,
  componentAlignmentKeys,
  countCrossings,
  cyclicNodes,
  groupLanes,
  layoutPlan,
  longestPathLayers,
  orderWithinLayers,
  overlapping,
  DEFAULT_SPACING,
  LANE_PADDING_TOP,
  LANE_PADDING_X,
  type StepSize,
} from "./layout";
import { estimateStepHeight, measureSteps, stepContent } from "./sizing";
import { buildPlanModel } from "./model";
import { EMPTY_FILTERS } from "./filters";
import type { StepDetail } from "./types";
import { SAMPLE_PLAN } from "./samplePlan";

const node = (
  id: string,
  module = "core",
  component: string | null = null,
  order = 0,
): StepNode => ({
  id,
  module_id: module,
  label: id,
  kind: "step",
  component,
  inputs: [{ slot_id: `${id}.in` }],
  outputs: [{ slot_id: `${id}.out`, role: "core.graph.node.x" }],
  order,
});

const edge = (from: string, to: string): StepEdge => ({
  id: `${from}->${to}`,
  from_step: from,
  from_slot: `${from}.out`,
  to_step: to,
  to_slot: `${to}.in`,
  role: "core.graph.node.x",
});

describe("longest-path layering", () => {
  it("puts sources at 0 and every consumer one layer right of its deepest producer", () => {
    const nodes = [node("a"), node("b"), node("c"), node("d")];
    const edges = [edge("a", "b"), edge("b", "d"), edge("a", "c"), edge("c", "d")];
    const { incoming } = buildAdjacency(nodes, edges);
    const layers = longestPathLayers(nodes, incoming);
    expect([...layers.entries()]).toEqual([
      ["a", 0],
      ["b", 1],
      ["c", 1],
      ["d", 2],
    ]);
  });

  it("layers the real reference plan into a strictly increasing DAG", () => {
    const nodes = SAMPLE_PLAN.nodes ?? [];
    const edges = SAMPLE_PLAN.edges ?? [];
    const { incoming, cycleBroken } = buildAdjacency(nodes, edges);
    expect(cycleBroken).toEqual([]);
    const layers = longestPathLayers(nodes, incoming);
    expect(layers.get("core::table.sites")).toBe(0);
    expect(layers.get("core::projection.defect")).toBe(1);
    expect(layers.get("file::write")).toBeGreaterThan(layers.get("core::aggregate.site") ?? 0);
    for (const link of edges) {
      expect((layers.get(link.to_step) ?? 0) - (layers.get(link.from_step) ?? 0)).toBeGreaterThanOrEqual(1);
    }
  });
});

describe("cycle safety", () => {
  it("drops the fewest edges it can and still terminates on a cyclic plan", () => {
    const nodes = [node("a"), node("b"), node("c")];
    const edges = [edge("a", "b"), edge("b", "c"), edge("c", "a")];
    const adjacency = buildAdjacency(nodes, edges);
    expect(adjacency.cycleBroken).toHaveLength(1);

    const inner = cyclicNodes(
      nodes.map((entry) => entry.id),
      adjacency.incoming,
      adjacency.outgoing,
    );
    expect(inner.size).toBe(0);

    const layers = longestPathLayers(nodes, adjacency.incoming);
    expect([...layers.values()].sort()).toEqual([0, 1, 2]);
  });

  it("ignores self-loops without reporting a cycle", () => {
    const nodes = [node("a"), node("b")];
    const edges = [edge("a", "a"), edge("a", "b")];
    const adjacency = buildAdjacency(nodes, edges);
    expect(adjacency.cycleBroken).toEqual([]);
    expect(adjacency.incoming.get("b")).toEqual(["a"]);
  });
});

describe("crossing reduction", () => {
  it("untangles a graph whose seed order crosses", () => {
    //  a1 a2      c1 c2   — with the seed order a1,a2 / c1,c2 the edge a2→c1 crosses a1→c2.
    const nodes = [node("a1"), node("a2"), node("c1"), node("c2")];
    const edges = [edge("a1", "c2"), edge("a2", "c1")];
    const { incoming, outgoing } = buildAdjacency(nodes, edges);
    const layers = longestPathLayers(nodes, incoming);
    const seed = ["a1", "a2", "c1", "c2"];

    const naive = new Map(seed.map((id, index) => [id, index]));
    const crossed = countCrossings(layers, incoming, naive);
    const ordered = orderWithinLayers(layers, incoming, outgoing, seed);
    const settled = countCrossings(layers, incoming, ordered);

    expect(crossed).toBeGreaterThan(0);
    expect(settled).toBe(0);
  });

  it("is deterministic: the same plan in a different input order yields the same order", () => {
    // The layout's seed is the contract's declaration order, so a shuffled payload
    // must still produce byte-identical boxes.
    const all = SAMPLE_PLAN.nodes ?? [];
    const edges = SAMPLE_PLAN.edges ?? [];
    const forward = buildPlanModel({ nodes: all, edges, modules: SAMPLE_PLAN.modules ?? [] });
    const backward = buildPlanModel({
      nodes: [...all].reverse(),
      edges: [...edges].reverse(),
      modules: [...(SAMPLE_PLAN.modules ?? [])].reverse(),
    });
    expect(backward.layout.placed).toEqual(forward.layout.placed);
    expect(backward.layout.lanes).toEqual(forward.layout.lanes);
  });

  it("reduces crossings on the real 60-step plan and never re-introduces them", () => {
    const nodes = SAMPLE_PLAN.nodes ?? [];
    const edges = SAMPLE_PLAN.edges ?? [];
    const adjacency = buildAdjacency(nodes, edges);
    const layers = longestPathLayers(nodes, adjacency.incoming);
    const seed = [...nodes].map((entry) => entry.id);
    const naive = new Map(seed.map((id, index) => [id, index]));
    const before = countCrossings(layers, adjacency.incoming, naive);
    const order = orderWithinLayers(layers, adjacency.incoming, adjacency.outgoing, seed);
    const after = countCrossings(layers, adjacency.incoming, order);
    expect(after).toBeLessThanOrEqual(before);
  });
});

describe("lanes", () => {
  it("groups by module and orders core before operator before target", () => {
    const nodes = [
      node("t1", "file", null, 0),
      node("c1", "core", null, 1),
      node("o1", "collapse_exact_duplicates", null, 2),
    ];
    const layers = new Map([
      ["t1", 5],
      ["c1", 0],
      ["o1", 3],
    ]);
    const roles = new Map([
      ["file", "target"],
      ["core", "core"],
      ["collapse_exact_duplicates", "operator"],
    ]) as ReadonlyMap<string, "core" | "operator" | "target">;
    const lanes = groupLanes(nodes, layers, roles);
    expect(lanes.map((lane) => lane.moduleId)).toEqual([
      "core",
      "collapse_exact_duplicates",
      "file",
    ]);
    expect(lanes[0]?.ids).toEqual(["c1"]);
  });
});

describe("component alignment", () => {
  it("pulls the same component's steps toward one slot", () => {
    const nodes = [
      node("agg", "core", "component:site", 0),
      node("other", "core", "component:unit", 1),
      node("op", "collapse_exact_duplicates", "component:site", 2),
    ];
    const order = new Map([
      ["agg", 0],
      ["other", 1],
      ["op", 9],
    ]);
    const keys = componentAlignmentKeys(nodes, order);
    expect((keys.get("op") as number) - (keys.get("agg") as number)).toBeLessThan(
      (order.get("op") as number) - (order.get("agg") as number),
    );
    expect(keys.get("other")).toBe(1);
  });
});

describe("placement", () => {
  const detail = (overrides: Partial<StepDetail> = {}): StepDetail => ({
    kindLabel: "step",
    summary: null,
    facts: [],
    badges: [],
    hasSql: false,
    relation: null,
    location: null,
    target: null,
    ...overrides,
  });

  it("places the whole real plan without overlapping boxes", () => {
    const model = buildPlanModel({
      nodes: SAMPLE_PLAN.nodes ?? [],
      edges: SAMPLE_PLAN.edges ?? [],
      modules: SAMPLE_PLAN.modules ?? [],
      filters: EMPTY_FILTERS,
    });
    expect(model.layout.placed).toHaveLength((SAMPLE_PLAN.nodes ?? []).length);
    expect(overlapping(model.layout.placed)).toEqual([]);
  });

  it("is deterministic: laying out the same plan twice produces identical boxes", () => {
    const input = {
      nodes: SAMPLE_PLAN.nodes ?? [],
      edges: SAMPLE_PLAN.edges ?? [],
      moduleRoles: new Map([["core", "core" as const]]),
      sizes: new Map(
        (SAMPLE_PLAN.nodes ?? []).map((entry) => [
          entry.id,
          measureSteps([entry], new Map([[entry.id, detail()]])).get(entry.id) as { width: number; height: number },
        ]),
      ),
    };
    const first = layoutPlan(input);
    const second = layoutPlan(input);
    expect(first.placed).toEqual(second.placed);
    expect(first.lanes).toEqual(second.lanes);
    expect([first.width, first.height]).toEqual([second.width, second.height]);
    // core, then the operator, then the three targets — targets ordered by the
    // leftmost *global* layer they occupy (neo4j starts two layers before the
    // file writer).
    expect(first.lanes.map((lane) => lane.moduleId)).toEqual([
      "core",
      "collapse_exact_duplicates",
      "neo4j",
      "file",
      "meta_graph",
    ]);
  });

  it("stacks lane bands top to bottom in role order and grows with the spacing control", () => {
    const wide = buildPlanModel({
      nodes: SAMPLE_PLAN.nodes ?? [],
      edges: SAMPLE_PLAN.edges ?? [],
      modules: SAMPLE_PLAN.modules ?? [],
      spacing: { columnGap: DEFAULT_SPACING.columnGap * 2, laneGap: 400 },
    });
    const tight = buildPlanModel({
      nodes: SAMPLE_PLAN.nodes ?? [],
      edges: SAMPLE_PLAN.edges ?? [],
      modules: SAMPLE_PLAN.modules ?? [],
    });

    // Lanes are horizontal bands now, so their order is a `y` order, not an `x` one.
    const ys = wide.layout.lanes.map((lane) => lane.y);
    expect([...ys].sort((a, b) => a - b)).toEqual(ys);
    expect(new Set(ys).size).toBe(ys.length);
    // A wider column grid is wider; a taller lane stack is taller.
    expect(wide.layout.width).toBeGreaterThan(tight.layout.width);
    expect(wide.layout.height).toBeGreaterThan(tight.layout.height);
    for (const [key, lane] of wide.layout.lanes.entries()) {
      const next = wide.layout.lanes[key + 1];
      if (!next) continue;
      expect(next.y).toBeGreaterThanOrEqual(lane.y + lane.height);
    }
  });

  it("sizes a node from its sockets, facts and badges", () => {
    const plain = stepContent(node("a"), detail());
    const withSql = stepContent(node("a"), detail({ facts: [{ text: "kg_table_0" }], badges: [{ text: "UNION ALL" }] }));
    expect(estimateStepHeight(withSql)).toBeGreaterThan(estimateStepHeight(plain));
    const sizes = measureSteps([node("a")], new Map([["a", detail()]]));
    expect(sizes.get("a")?.height).toBe(estimateStepHeight(plain));
  });
});

/**
 * The demo-shaped graph: a target and a meta-graph writer with identical parent
 * sets, i.e. two sinks where neither consumes the other.
 */
const DEMO_NODES: StepNode[] = [
  node("core::source", "core", null, 0),
  node("core::project", "core", null, 1),
  node("collapse_exact_duplicates::dedup", "collapse_exact_duplicates", null, 2),
  node("file::write", "file", null, 3),
  node("meta_graph::document", "meta_graph", null, 4),
];

const DEMO_EDGES: StepEdge[] = [
  edge("core::source", "core::project"),
  edge("core::project", "collapse_exact_duplicates::dedup"),
  edge("collapse_exact_duplicates::dedup", "file::write"),
  edge("collapse_exact_duplicates::dedup", "meta_graph::document"),
];

const DEMO_ROLES = new Map<string, ModuleRole>([
  ["core", "core"],
  ["collapse_exact_duplicates", "operator"],
  ["file", "target"],
  ["meta_graph", "target"],
]);

const byIdOf = (placed: readonly PlacedStep[]) => new Map(placed.map((step) => [step.id, step]));

describe("global columns", () => {
  const layout = () => layoutPlan({ nodes: DEMO_NODES, edges: DEMO_EDGES, moduleRoles: DEMO_ROLES });

  it("stacks sibling steps in different lanes in one column instead of one after the other", () => {
    // `file::write` and `meta_graph::document` share every parent and no edge, so
    // they are at the same depth: side by side would read as a sequence that does
    // not exist.
    const placed = byIdOf(layout().placed);
    const file = placed.get("file::write");
    const meta = placed.get("meta_graph::document");
    expect(file).toBeDefined();
    expect(meta).toBeDefined();
    expect(file?.layer).toBe(meta?.layer);
    expect(file?.x).toBe(meta?.x);
    expect(file?.y).not.toBe(meta?.y);
  });

  it("places a consumer to the right of its producer across the whole canvas, not just inside a lane", () => {
    const result = layout();
    const placed = byIdOf(result.placed);
    // The two-module chain has to advance one column per hop even though each hop
    // lands in a different lane — the property the lane-relative grid broke.
    expect(placed.get("core::source")?.x).toBeLessThan((placed.get("collapse_exact_duplicates::dedup")?.x ?? 0));
    expect(placed.get("collapse_exact_duplicates::dedup")?.x).toBeLessThan((placed.get("file::write")?.x ?? 0));
    for (const link of DEMO_EDGES) {
      expect(placed.get(link.to_step)?.x).toBeGreaterThan((placed.get(link.from_step)?.x ?? Number.POSITIVE_INFINITY));
    }
  });

  it("monotonises x with dependency depth across lanes on the real plan", () => {
    const model = buildPlanModel({
      nodes: SAMPLE_PLAN.nodes ?? [],
      edges: SAMPLE_PLAN.edges ?? [],
      modules: SAMPLE_PLAN.modules ?? [],
    });
    const placed = byIdOf(model.layout.placed);
    for (const link of SAMPLE_PLAN.edges ?? []) {
      expect(placed.get(link.to_step)?.x).toBeGreaterThan(
        (placed.get(link.from_step)?.x ?? Number.POSITIVE_INFINITY),
      );
    }
    // The two sinks the bug was about: same column, different rows.
    const file = placed.get("file::write");
    const meta = placed.get("meta_graph::document");
    expect(file?.x).toBe(meta?.x);
    expect(file?.y).not.toBe(meta?.y);
  });

  it("stacks non-overlapping lane bands, each containing all of its own steps", () => {
    const result = layout();
    const lanes = [...result.lanes];
    expect(lanes).toHaveLength(4);
    for (const [index, lane] of lanes.entries()) {
      for (const other of lanes.slice(index + 1)) {
        expect(lane.y + lane.height).toBeLessThanOrEqual(other.y);
      }
    }
    for (const step of result.placed) {
      const lane = lanes.find((entry) => entry.moduleId === step.lane);
      expect(lane).toBeDefined();
      expect(step.x).toBeGreaterThanOrEqual((lane?.x ?? 0) + LANE_PADDING_X);
      expect(step.x + step.width).toBeLessThanOrEqual((lane?.x ?? 0) + (lane?.width ?? 0) - LANE_PADDING_X);
      expect(step.y).toBeGreaterThanOrEqual((lane?.y ?? 0) + LANE_PADDING_TOP);
      expect(step.y + step.height).toBeLessThanOrEqual((lane?.y ?? 0) + (lane?.height ?? 0));
    }
  });

  it("numbers columns globally, so a lane's band spans only the layers it occupies", () => {
    const result = layout();
    const lanes = new Map(result.lanes.map((lane) => [lane.moduleId, lane]));
    // Both sinks sit in the same band column, and the core band stops where core stops.
    expect(lanes.get("file")?.x).toBe(lanes.get("meta_graph")?.x);
    const core = lanes.get("core");
    const file = lanes.get("file");
    expect(core).toBeDefined();
    expect(file).toBeDefined();
    const coreRight = (core?.x ?? 0) + (core?.width ?? 0);
    const lastCore = result.placed
      .filter((step) => step.lane === "core")
      .reduce((right, step) => Math.max(right, step.x + step.width), 0);
    expect(coreRight).toBeGreaterThanOrEqual(lastCore);
    // Core owns layers 0–1 and the sinks layer 3, so its band must not run under them.
    expect(coreRight).toBeLessThan(file?.x ?? 0);
    // Every column the plan occupies fits inside the reported canvas.
    const right = result.placed.reduce((max, step) => Math.max(max, step.x + step.width), 0);
    expect(right).toBeLessThanOrEqual(result.width);
    const bottom = result.placed.reduce((max, step) => Math.max(max, step.y + step.height), 0);
    expect(bottom).toBeLessThanOrEqual(result.height);
  });

  it("places the demo-scale plan without overlapping boxes", () => {
    expect(overlapping(layout().placed)).toEqual([]);
  });

  it("sizes a global column by the widest node in that layer, whichever lane holds it", () => {
    // The wide step is the second lane's, but it still has to widen the column the
    // first lane's narrow step sits in — that is what makes the two columns line up
    // across lanes instead of per lane.
    const nodes = [node("core::a", "core", null, 0), node("file::b", "file", null, 1)];
    const sizes = new Map<string, StepSize>([
      ["core::a", { width: 100, height: 60 }],
      ["file::b", { width: 300, height: 60 }],
    ]);
    const result = layoutPlan({
      nodes,
      edges: [],
      moduleRoles: new Map([["file", "target" as const]]),
      sizes,
    });
    const [narrow, wide] = [byIdOf(result.placed).get("core::a"), byIdOf(result.placed).get("file::b")];
    expect(narrow?.column).toBe(wide?.column);
    // Centred in one 300 px column: same centre, the narrow card inset by half the
    // difference on each side. Every real plan card is `STEP_WIDTH` wide, so equal
    // `x` — what the canvas actually draws — is this rule with a zero inset.
    const centre = (step: PlacedStep | undefined) => (step ? step.x + step.width / 2 : 0);
    expect(centre(narrow)).toBe(centre(wide));
    expect(wide?.x).toBeLessThan(narrow?.x ?? 0);
    expect(narrow?.x).toBe((wide?.x ?? 0) + (300 - 100) / 2);
    // The narrow card's own lane band is as wide as the shared column, not as wide
    // as the card.
    const core = result.lanes.find((lane) => lane.moduleId === "core");
    expect(core?.width).toBe(300 + LANE_PADDING_X * 2);
  });
});
