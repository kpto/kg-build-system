import { describe, expect, it } from "vitest";

import type { PlacedStep, StepEdge, StepNode } from "./types";
import {
  buildAdjacency,
  componentAlignmentKeys,
  countCrossings,
  cyclicNodes,
  layoutPlan,
  longestPathLayers,
  moduleAlignmentKeys,
  orderWithinLayers,
  overlapping,
  DEFAULT_SPACING,
  CANVAS_PADDING,
  type StepSize,
} from "./layout";
import { estimateStepHeight, measureSteps, stepContent } from "./sizing";
import { buildPlanModel, type PlanModel } from "./model";
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

const byIdOf = (placed: readonly PlacedStep[]) => new Map(placed.map((step) => [step.id, step]));

/** One column of the field: its steps top first, plus the things a test asks about. */
interface Column {
  readonly column: number;
  readonly x: number;
  readonly top: number;
  readonly ids: readonly string[];
  readonly lanes: readonly string[];
  /** What the column alone is as tall as, padding excluded. */
  readonly stack: number;
}

const columnsOf = (placed: readonly PlacedStep[]): Column[] => {
  const byColumn = new Map<number, PlacedStep[]>();
  for (const step of [...placed].sort((a, b) => a.y - b.y || (a.id < b.id ? -1 : 1))) {
    const bucket = byColumn.get(step.column);
    if (bucket) bucket.push(step);
    else byColumn.set(step.column, [step]);
  }
  return [...byColumn.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([column, steps]) => ({
      column,
      x: (steps[0] as PlacedStep).x,
      top: Math.min(...steps.map((step) => step.y)),
      ids: steps.map((step) => step.id),
      lanes: steps.map((step) => step.lane),
      stack:
        steps.reduce((sum, step) => sum + step.height, 0) +
        Math.max(0, steps.length - 1) * DEFAULT_SPACING.rowGap,
    }));
};

/** How many runs of one module a column's stacking is made of. */
const runsOf = (lanes: readonly string[]) =>
  lanes.reduce((count, lane, index) => (index === 0 || lanes[index - 1] !== lane ? count + 1 : count), 0);

const sampleModel = (spacing?: Partial<typeof DEFAULT_SPACING>): PlanModel =>
  buildPlanModel({
    nodes: SAMPLE_PLAN.nodes ?? [],
    edges: SAMPLE_PLAN.edges ?? [],
    modules: SAMPLE_PLAN.modules ?? [],
    spacing,
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
    expect(backward.layout.layers).toEqual(forward.layout.layers);
    expect([backward.layout.width, backward.layout.height]).toEqual([
      forward.layout.width,
      forward.layout.height,
    ]);
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

describe("vertical affinity", () => {
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

  it("gathers a module's steps into one run instead of interleaving them", () => {
    // Two modules meeting in the middle column. The crossing reduction's own order
    // alternates operator, core, operator, core; the module pull has to settle that
    // into two adjacent blocks, or neither module reads as one continuous colour.
    const nodes = [
      node("core::s1", "core", null, 0),
      node("core::s2", "core", null, 1),
      node("dedup::o1", "collapse_exact_duplicates", null, 2),
      node("dedup::o2", "collapse_exact_duplicates", null, 3),
      node("core::c1", "core", null, 4),
      node("dedup::c2", "collapse_exact_duplicates", null, 5),
      node("core::c3", "core", null, 6),
      node("dedup::c4", "collapse_exact_duplicates", null, 7),
    ];
    const edges = [
      edge("core::s1", "dedup::o1"),
      edge("core::s2", "dedup::o2"),
      edge("core::s1", "core::c1"),
      edge("dedup::o1", "dedup::c2"),
      edge("core::s2", "core::c3"),
      edge("dedup::o2", "dedup::c4"),
    ];
    const shared = columnsOf(layoutPlan({ nodes, edges }).placed)[1] as Column;
    expect(shared.lanes).toEqual([
      "collapse_exact_duplicates",
      "collapse_exact_duplicates",
      "core",
      "core",
    ]);
    expect(shared.ids).toEqual(["dedup::o1", "dedup::o2", "core::c1", "core::c3"]);
  });

  it("leaves the order inside a module's run to the pull beneath it", () => {
    // The component pull moves `dedup::c` (component:site) up beside `core::a`; the
    // module pull tightens the operator's run without undoing that.
    const nodes = [
      node("core::a", "core", "component:site", 0),
      node("core::b", "core", "component:unit", 1),
      node("dedup::c", "collapse_exact_duplicates", "component:site", 2),
      node("dedup::d", "collapse_exact_duplicates", "component:other", 3),
    ];
    const layerOf = new Map(nodes.map((entry) => [entry.id, 0]));
    const order = new Map([
      ["core::a", 0],
      ["core::b", 1],
      ["dedup::c", 2],
      ["dedup::d", 3],
    ]);
    const component = componentAlignmentKeys(nodes, order);
    expect(component.get("dedup::c")).toBeLessThan(component.get("dedup::d") as number);

    const keys = moduleAlignmentKeys(nodes, layerOf, component);
    expect(keys.get("dedup::c")).toBeLessThan(keys.get("dedup::d") as number);
    expect(keys.get("core::a")).toBeLessThan(keys.get("core::b") as number);
    // The run's own steps end up nearer one another than the pull beneath it left them.
    expect(Math.abs((keys.get("dedup::d") as number) - (keys.get("dedup::c") as number))).toBeLessThan(
      Math.abs((component.get("dedup::d") as number) - (component.get("dedup::c") as number)),
    );
  });

  it("anchors a module per column, so one column never drags another along", () => {
    const nodes = [
      node("dedup::a", "collapse_exact_duplicates", null, 0),
      node("core::b", "core", null, 1),
      node("dedup::c", "collapse_exact_duplicates", null, 2),
      node("core::d", "core", null, 3),
    ];
    const layerOf = new Map([
      ["dedup::a", 0],
      ["core::b", 0],
      ["dedup::c", 1],
      ["core::d", 1],
    ]);
    const keys = moduleAlignmentKeys(
      nodes,
      layerOf,
      new Map([
        ["dedup::a", 3],
        ["core::b", 0],
        ["dedup::c", 0],
        ["core::d", 1],
      ]),
    );
    // Column 1 keeps the order it was handed (c above d) whatever column 0 decided,
    // and column 0 keeps its own (b above a).
    expect(keys.get("dedup::c")).toBeLessThan(keys.get("core::d") as number);
    expect(keys.get("core::b")).toBeLessThan(keys.get("dedup::a") as number);
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
    const model = sampleModel();
    expect(model.layout.placed).toHaveLength((SAMPLE_PLAN.nodes ?? []).length);
    expect(overlapping(model.layout.placed)).toEqual([]);
  });

  it("is deterministic: laying out the same plan twice produces identical boxes", () => {
    const input = {
      nodes: SAMPLE_PLAN.nodes ?? [],
      edges: SAMPLE_PLAN.edges ?? [],
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
    expect([first.width, first.height]).toEqual([second.width, second.height]);
    // Every step still carries its module: the card colour is what replaced the bands,
    // so it has to survive them.
    const moduleOf = new Map((SAMPLE_PLAN.nodes ?? []).map((entry) => [entry.id, entry.module_id]));
    expect(first.placed.every((step) => step.lane === moduleOf.get(step.id))).toBe(true);
    expect(new Set(first.placed.map((step) => step.lane)).size).toBe(5);
    // One column grid for the whole canvas, numbered left to right from 0.
    expect(columnsOf(first.placed).map((column) => column.column)).toEqual([0, 1, 2, 3, 4, 5, 6, 7]);
  });

  it("grows sideways with the spacing control while its top edge stays put", () => {
    const wide = sampleModel({
      columnGap: DEFAULT_SPACING.columnGap * 2,
      rowGap: DEFAULT_SPACING.rowGap * 3,
    });
    const tight = sampleModel();

    expect(wide.layout.width).toBeGreaterThan(tight.layout.width);
    expect(wide.layout.height).toBeGreaterThan(tight.layout.height);
    // There is no band gap left to grow, so spacing can only move the columns apart
    // and the rows within them: the top of every column is the canvas padding either
    // way, in both settings.
    for (const model of [wide, tight]) {
      expect(new Set(columnsOf(model.layout.placed).map((column) => column.top))).toEqual(
        new Set([CANVAS_PADDING]),
      );
    }
  });

  it("sizes a node from its sockets, facts and badges", () => {
    const plain = stepContent(node("a"), detail());
    const withSql = stepContent(node("a"), detail({ facts: [{ text: "kg_table_0" }], badges: [{ text: "UNION ALL" }] }));
    expect(estimateStepHeight(withSql)).toBeGreaterThan(estimateStepHeight(plain));
    const sizes = measureSteps([node("a")], new Map([["a", detail()]]));
    expect(sizes.get("a")?.height).toBe(estimateStepHeight(plain));
  });

  it("places nothing for an empty plan", () => {
    expect(layoutPlan({ nodes: [], edges: [] })).toMatchObject({
      placed: [],
      width: 0,
      height: 0,
      crossings: 0,
      cycleBroken: [],
    });
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

describe("one field on global columns", () => {
  const layout = () => layoutPlan({ nodes: DEMO_NODES, edges: DEMO_EDGES });

  it("stacks sibling steps of two modules in one column instead of one after the other", () => {
    // `file::write` and `meta_graph::document` share every parent and no edge, so
    // they are at the same depth: side by side would read as a sequence that does
    // not exist.
    const placed = byIdOf(layout().placed);
    const file = placed.get("file::write");
    const meta = placed.get("meta_graph::document");
    expect(file).toBeDefined();
    expect(meta).toBeDefined();
    expect(file?.layer).toBe(meta?.layer);
    expect(file?.column).toBe(meta?.column);
    expect(file?.x).toBe(meta?.x);
    expect(file?.y).not.toBe(meta?.y);
    // And they stack down from the top of the field, not from under every other module.
    expect(Math.min(file?.y ?? 0, meta?.y ?? 0)).toBe(CANVAS_PADDING);
  });

  it("places a consumer to the right of its producer across the whole canvas", () => {
    const result = layout();
    const placed = byIdOf(result.placed);
    // Every hop of the chain lands in a different module, so the column grid has to be
    // shared for the depth to advance at all — the property a per-module grid broke.
    expect(placed.get("core::source")?.x).toBeLessThan((placed.get("collapse_exact_duplicates::dedup")?.x ?? 0));
    expect(placed.get("collapse_exact_duplicates::dedup")?.x).toBeLessThan((placed.get("file::write")?.x ?? 0));
    for (const link of DEMO_EDGES) {
      expect(placed.get(link.to_step)?.x).toBeGreaterThan((placed.get(link.from_step)?.x ?? Number.POSITIVE_INFINITY));
    }
  });

  it("starts every column at the same top edge, whichever module owns its steps", () => {
    const result = layout();
    const columns = columnsOf(result.placed);
    expect(columns).toHaveLength(4);
    for (const column of columns) {
      expect(column.top).toBe(CANVAS_PADDING);
    }
    // So the field is as tall as its tallest column, not as tall as all of them.
    const tallest = Math.max(...columns.map((column) => column.stack));
    expect(result.height).toBe(tallest + CANVAS_PADDING * 2);
    // And as wide as the shared grid plus one padding on each side — no lane padding.
    const right = result.placed.reduce((max, step) => Math.max(max, step.x + step.width), 0);
    expect(result.width).toBe(right + CANVAS_PADDING);
  });

  it("draws a later module beside the steps it consumes, not under them", () => {
    const placed = byIdOf(layout().placed);
    const source = placed.get("core::source") as PlacedStep;
    const project = placed.get("core::project") as PlacedStep;
    const dedup = placed.get("collapse_exact_duplicates::dedup") as PlacedStep;
    const file = placed.get("file::write") as PlacedStep;
    const meta = placed.get("meta_graph::document") as PlacedStep;
    // One module band per module used to start every operator card under the whole
    // core block; each step now starts where its own column starts, so the folding
    // reads as the next stage to the right, at the same height.
    expect(dedup.y).toBe(CANVAS_PADDING);
    expect(dedup.y).toBe(source.y);
    expect(dedup.y).toBe(project.y);
    // The two sinks are the only cards in their column and sit directly under one
    // another, one row gap apart, with nothing above the first.
    expect(file.y).toBe(CANVAS_PADDING);
    expect(meta.y).toBe(file.y + file.height + DEFAULT_SPACING.rowGap);
  });

  it("monotonises x with dependency depth across modules on the real plan", () => {
    const model = sampleModel();
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

  it("top-aligns every column of the real plan and stops at its tallest one", () => {
    const model = sampleModel();
    const columns = columnsOf(model.layout.placed);
    expect(columns.map((column) => column.top)).toEqual(columns.map(() => CANVAS_PADDING));
    const tallest = Math.max(...columns.map((column) => column.stack));
    expect(model.layout.height).toBe(tallest + CANVAS_PADDING * 2);
    // Which is what keeps the picture short and narrow: 60 cards, each about 90 px
    // tall and 232 wide, laid end to end would fill many times the field's height, and
    // one padded column grid per module many times its width.
    expect(model.layout.height).toBeLessThan(60 * 90);
    expect(model.layout.width).toBeLessThan(8 * (232 + DEFAULT_SPACING.columnGap) + CANVAS_PADDING * 2);

    // No module is drawn below the steps it consumes: core, operator and the biggest
    // target all start at the field's top edge.
    const top = (lane: string) =>
      Math.min(...model.layout.placed.filter((step) => step.lane === lane).map((step) => step.y));
    expect(top("core")).toBe(CANVAS_PADDING);
    expect(top("collapse_exact_duplicates")).toBe(CANVAS_PADDING);
    expect(top("neo4j")).toBe(CANVAS_PADDING);
    // The two sinks still share the last-but-one column.
    const sinks = columns[6] as Column;
    expect(sinks.ids).toContain("file::write");
    expect(sinks.ids).toContain("meta_graph::document");
    expect(byIdOf(model.layout.placed).get("file::write")?.x).toBe(sinks.x);
  });

  it("keeps each module's steps in one contiguous run per column", () => {
    const columns = columnsOf(sampleModel().layout.placed);
    for (const column of columns) {
      expect(runsOf(column.lanes)).toBe(new Set(column.lanes).size);
    }
    // The concrete case: the column where the operator meets core holds five core
    // steps and then seven operator steps, one run each.
    expect(columns[3]?.lanes).toEqual([
      "core",
      "core",
      "core",
      "core",
      "core",
      "collapse_exact_duplicates",
      "collapse_exact_duplicates",
      "collapse_exact_duplicates",
      "collapse_exact_duplicates",
      "collapse_exact_duplicates",
      "collapse_exact_duplicates",
      "collapse_exact_duplicates",
    ]);
  });

  it("sizes a global column by the widest node in that layer, whichever module holds it", () => {
    // The wide card belongs to the second module, but it still widens the column the
    // first module's narrow card sits in — that is what makes the two line up across
    // modules instead of per module.
    const nodes = [node("core::a", "core", null, 0), node("file::b", "file", null, 1)];
    const sizes = new Map<string, StepSize>([
      ["core::a", { width: 100, height: 60 }],
      ["file::b", { width: 300, height: 60 }],
    ]);
    const result = layoutPlan({ nodes, edges: [], sizes });
    const placed = byIdOf(result.placed);
    const narrow = placed.get("core::a");
    const wide = placed.get("file::b");
    expect(narrow?.column).toBe(wide?.column);
    // Centred in one 300 px column: same centre, the narrow card inset by half the
    // difference on each side. Every real plan card is `STEP_WIDTH` wide, so equal
    // `x` — what the canvas actually draws — is this rule with a zero inset.
    const centre = (step: PlacedStep | undefined) => (step ? step.x + step.width / 2 : 0);
    expect(centre(narrow)).toBe(centre(wide));
    expect(wide?.x).toBe(CANVAS_PADDING);
    expect(narrow?.x).toBe(CANVAS_PADDING + (300 - 100) / 2);
    // Both stack in that one shared column with no lane padding anywhere: the field is
    // as wide as the widest card plus the canvas padding, and as tall as the two of them.
    expect(result.width).toBe(300 + CANVAS_PADDING * 2);
    expect(result.height).toBe(60 + DEFAULT_SPACING.rowGap + 60 + CANVAS_PADDING * 2);
  });

  it("places the demo-scale plan without overlapping boxes", () => {
    expect(overlapping(layout().placed)).toEqual([]);
  });
});
