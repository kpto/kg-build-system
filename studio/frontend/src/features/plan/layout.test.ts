import { describe, expect, it } from "vitest";

import type { StepEdge, StepNode } from "./types";
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
    // core, then the operator, then the three targets — targets ordered by the
    // leftmost layer they occupy (neo4j starts one column before the file writer).
    expect(first.lanes.map((lane) => lane.moduleId)).toEqual([
      "core",
      "collapse_exact_duplicates",
      "neo4j",
      "file",
      "meta_graph",
    ]);
  });

  it("stacks lanes left to right in role order and grows them with the spacing control", () => {
    const model = buildPlanModel({
      nodes: SAMPLE_PLAN.nodes ?? [],
      edges: SAMPLE_PLAN.edges ?? [],
      modules: SAMPLE_PLAN.modules ?? [],
      spacing: { columnGap: DEFAULT_SPACING.columnGap * 2, laneGap: 400 },
    });
    const xs = model.layout.lanes.map((lane) => lane.x);
    expect([...xs].sort((a, b) => a - b)).toEqual(xs);
    expect(model.layout.width).toBeGreaterThan(
      buildPlanModel({
        nodes: SAMPLE_PLAN.nodes ?? [],
        edges: SAMPLE_PLAN.edges ?? [],
        modules: SAMPLE_PLAN.modules ?? [],
      }).layout.width,
    );
  });

  it("sizes a node from its sockets, facts and badges", () => {
    const plain = stepContent(node("a"), detail());
    const withSql = stepContent(node("a"), detail({ facts: [{ text: "kg_table_0" }], badges: [{ text: "UNION ALL" }] }));
    expect(estimateStepHeight(withSql)).toBeGreaterThan(estimateStepHeight(plain));
    const sizes = measureSteps([node("a")], new Map([["a", detail()]]));
    expect(sizes.get("a")?.height).toBe(estimateStepHeight(plain));
  });
});
