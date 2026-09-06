import { describe, expect, it } from "vitest";

import type { StepEdge, StepNode } from "./types";
import {
  countGraph,
  EMPTY_FILTERS,
  filterGraph,
  matchesQuery,
  shortFingerprint,
  staleness,
  stepMatches,
  touchesRef,
  filtersActive,
} from "./filters";
import { traceSubDag } from "./subdag";
import { SAMPLE_PLAN } from "./samplePlan";

const node = (
  id: string,
  overrides: Partial<StepNode> = {},
): StepNode => ({
  id,
  module_id: "core",
  label: id,
  kind: "table",
  component: `table:${id}`,
  inputs: [],
  outputs: [{ slot_id: `${id}.out`, role: `core.data.table.${id}` }],
  ...overrides,
});

const link = (from: string, to: string, id = `${from}->${to}`): StepEdge => ({
  id,
  from_step: from,
  from_slot: `${from}.out`,
  to_step: to,
  to_slot: `${to}.in`,
  role: "core.data.table.sites",
});

const nodes = [
  node("sites"),
  node("defect", { kind: "projection", component: "projection:defect", module_id: "core" }),
  node("bind", {
    kind: "binding",
    component: null,
    outputs: [{ slot_id: "bind.out", role: "core.binding.binding:edge:has_defect:4a77" }],
    sql: 'SELECT * FROM (SELECT "d"."defect_id" AS "_kg_raw_build_key", "d"."as_at" AS "_kg_raw_as_at")',
  }),
  node("site", { kind: "aggregate", component: "component:site", module_id: "core", notes: ["materialized"] }),
  node("write", { kind: "publish", component: null, module_id: "file" }),
];
const edges = [link("sites", "defect"), link("defect", "bind"), link("bind", "site"), link("site", "write")];

describe("filter predicates", () => {
  it("keeps everything when no filter is set", () => {
    const visible = filterGraph(nodes, edges, EMPTY_FILTERS, null);
    expect(visible.nodes).toHaveLength(nodes.length);
    expect(visible.edges).toHaveLength(edges.length);
  });

  it("drops a module's steps and the connections that touched them", () => {
    const visible = filterGraph(nodes, edges, { ...EMPTY_FILTERS, modules: ["core"] }, null);
    expect(visible.nodes.map((entry) => entry.id)).toEqual(["sites", "defect", "bind", "site"]);
    expect(visible.edges.map((entry) => entry.id)).toEqual(["sites->defect", "defect->bind", "bind->site"]);
  });

  it("filters by kind", () => {
    const visible = filterGraph(nodes, edges, { ...EMPTY_FILTERS, kinds: ["binding"] }, null);
    expect(visible.nodes.map((entry) => entry.id)).toEqual(["bind"]);
    expect(visible.edges).toHaveLength(0);
  });

  it("searches label, component, relation and notes", () => {
    expect(matchesQuery(nodes[3] as StepNode, "material")).toBe(true);
    expect(matchesQuery(nodes[1] as StepNode, "projection:defect")).toBe(true);
    expect(matchesQuery(nodes[0] as StepNode, "nope")).toBe(false);
  });

  it("matches a step to a selected ref including refs to a part of it", () => {
    const binding = nodes[2] as StepNode;
    expect(touchesRef(binding, "component:has_defect")).toBe(true);
    expect(touchesRef(nodes[3] as StepNode, "component:site.property.city")).toBe(true);
    expect(touchesRef(nodes[3] as StepNode, "component:unit")).toBe(false);
    expect(stepMatches(nodes[3] as StepNode, { ...EMPTY_FILTERS, onlySelected: true }, "component:site")).toBe(true);
    expect(stepMatches(nodes[0] as StepNode, { ...EMPTY_FILTERS, onlySelected: true }, "component:site")).toBe(false);
  });

  it("reports whether any filter is in force", () => {
    expect(filtersActive(EMPTY_FILTERS)).toBe(false);
    expect(filtersActive({ ...EMPTY_FILTERS, query: " " })).toBe(false);
    expect(filtersActive({ ...EMPTY_FILTERS, query: "x" })).toBe(true);
  });
});

describe("counts", () => {
  it("summarises steps, connections, materialised steps and steps with SQL", () => {
    const counts = countGraph(nodes, edges);
    expect(counts).toEqual({
      steps: 5,
      connections: 4,
      materialised: 1,
      withSql: 1,
      components: 4,
    });
  });

  it("counts the real plan: 60 steps, 90 connections, 16 with SQL", () => {
    const counts = countGraph(SAMPLE_PLAN.nodes ?? [], SAMPLE_PLAN.edges ?? []);
    expect(counts.steps).toBe(60);
    expect(counts.connections).toBe(90);
    expect(counts.withSql).toBe(16);
    expect(counts.materialised).toBe(0);
  });
});

describe("sub-DAG tracing", () => {
  it("lights the ancestors and descendants of the hovered step only", () => {
    const trace = traceSubDag("bind", nodes, edges);
    expect([...trace.ancestors].sort()).toEqual(["defect", "sites"]);
    expect([...trace.descendants].sort()).toEqual(["site", "write"]);
    expect(trace.related.has("bind")).toBe(true);
    expect(trace.relatedEdges.has("defect->bind")).toBe(true);
    expect(trace.relatedEdges.has("site->write")).toBe(true);
  });

  it("terminates and stays finite on a cyclic plan", () => {
    const cyclic = [node("a"), node("b"), node("c")];
    const cyclicEdges = [link("a", "b"), link("b", "c"), link("c", "a")];
    const trace = traceSubDag("a", cyclic, cyclicEdges);
    expect(trace.related.size).toBe(3);
    expect(trace.relatedEdges.size).toBe(3);
  });

  it("returns nothing when no node is hovered", () => {
    expect(traceSubDag(null, nodes, edges).related.size).toBe(0);
  });
});

describe("staleness rule", () => {
  it("treats only a clean generation as a current plan", () => {
    expect(staleness("clean").level).toBe("fresh");
    expect(staleness("dirty").level).toBe("stale");
    expect(staleness("running").level).toBe("stale");
    expect(staleness("failed").level).toBe("stale");
    expect(staleness("never").level).toBe("stale");
    expect(staleness(null).level).toBe("stale");
  });

  it("explains the state in the banner copy", () => {
    expect(staleness("dirty", { planPresent: true }).message).toMatch(/may be stale/);
    expect(staleness("running", { planPresent: true }).message).toMatch(/regeneration is running/);
  });

  it("does not claim freshness without a status model or a plan", () => {
    expect(staleness("clean", { mock: true }).level).toBe("unknown");
    expect(staleness("clean", { planPresent: false }).level).toBe("unknown");
  });

  it("shortens the fingerprint for the header chip", () => {
    expect(shortFingerprint("0c6b5dda6a216cb5c5397f72")).toBe("0c6b5dda6a21");
    expect(shortFingerprint(null)).toBe("no fingerprint");
  });
});
