import { describe, expect, it } from "vitest";

import type { StepDetail, StepEdge, StepNode } from "./types";
import { groupSockets, slotName } from "./sockets";
import { roleColor, roleComponent, roleFamily, roleLabel } from "./roles";
import {
  bindingProperties,
  buildKeys,
  isMaterialised,
  KIND_LABEL,
  selectedColumns,
  shorten,
  stepDetail,
  stepRef,
} from "./detail";
import { laneColors, moduleRole } from "./lanes";
import { SAMPLE_PLAN } from "./samplePlan";
import { TOKEN } from "./tokens";

const detailOf = (node: StepNode): StepDetail => stepDetail(node, [], null);

describe("socket grouping", () => {
  it("lists inputs above outputs and keeps slot ids as handle ids", () => {
    const node: StepNode = {
      id: "core::binding.0",
      module_id: "core",
      label: "bind",
      kind: "binding",
      inputs: [
        { slot_id: "core::binding.0.inputs", role: "inputs" },
        { slot_id: "core::binding.0.other", role: "other" },
      ],
      outputs: [{ slot_id: "core::binding.0.output", role: "core.binding.binding:edge:has_defect:4a77" }],
    };
    const group = groupSockets(node);
    expect(group.inputs.map((socket) => socket.id)).toEqual([
      "core::binding.0.inputs",
      "core::binding.0.other",
    ]);
    expect(group.outputs.map((socket) => socket.label)).toEqual(["bind has_defect"]);
    expect(group.inputs[0]?.role).toBeNull();
  });

  it("de-duplicates a slot repeated in the payload", () => {
    const node: StepNode = {
      id: "core::table.sites",
      module_id: "core",
      label: "sites",
      kind: "table",
      inputs: [{ slot_id: "a" }, { slot_id: "a" }],
      outputs: [{ slot_id: "b", role: "core.data.table.sites" }],
    };
    expect(groupSockets(node).inputs).toHaveLength(1);
  });

  it("names a socket by the last dotted part of its slot id", () => {
    expect(slotName("core::table.sites.output")).toBe("output");
    expect(slotName("records")).toBe("records");
  });
});

describe("artifact-role colour mapping", () => {
  it("colours each role family with its own token", () => {
    expect(roleColor("core.data.table.sites")).toBe(TOKEN.template);
    expect(roleColor("core.data.projection.defect")).toBe(TOKEN.edgekind);
    expect(roleColor("core.binding.binding:node:site:e17a")).toBe(TOKEN.category);
    expect(roleColor("core.graph.node.site")).toBe(TOKEN.node);
    expect(roleColor("core.graph.edge.has_unit")).toBe(TOKEN.relation);
    expect(roleColor("workflow.publication.file.write_result")).toBe(TOKEN.warn);
    expect(roleColor(null)).toBe(TOKEN.faint);
  });

  it("labels a role the way the socket shows it", () => {
    expect(roleLabel("core.graph.edge.has_unit")).toBe("edge.has_unit");
    expect(roleLabel("core.data.table.sites")).toBe("table.sites");
    expect(roleLabel("core.binding.binding:edge:has_defect:4a77")).toBe("bind has_defect");
    expect(roleLabel(null)).toBe("");
  });

  it("recovers the component a role names", () => {
    expect(roleComponent("core.binding.binding:edge:has_defect:4a77")).toBe("has_defect");
    expect(roleComponent("core.graph.node.survey_visit")).toBe("survey_visit");
    expect(roleComponent("core.data.table.sites")).toBeNull();
    expect(roleFamily("anything.else")).toBe("other");
  });

  it("colours every edge of the real plan with a known token", () => {
    const colors = new Set((SAMPLE_PLAN.edges ?? []).map((edge) => roleColor(edge.role ?? null)));
    for (const color of colors) expect(Object.values(TOKEN)).toContain(color);
  });
});

describe("kind labelling and node bodies", () => {
  const table = (SAMPLE_PLAN.nodes ?? []).find((entry) => entry.kind === "table") as StepNode;
  const projection = (SAMPLE_PLAN.nodes ?? []).find((entry) => entry.kind === "projection") as StepNode;
  const binding = (SAMPLE_PLAN.nodes ?? []).find((entry) => entry.kind === "binding") as StepNode;
  const aggregate = (SAMPLE_PLAN.nodes ?? []).find((entry) => entry.kind === "aggregate") as StepNode;
  const operator = (SAMPLE_PLAN.nodes ?? []).find((entry) => entry.kind === "operator") as StepNode;
  const publish = (SAMPLE_PLAN.nodes ?? []).find((entry) => entry.kind === "publish") as StepNode;

  it("labels a table with its columns, format and location", () => {
    const detail = detailOf(table);
    expect(detail.kindLabel).toBe(KIND_LABEL.table);
    expect(detail.facts.some((fact) => /columns/.test(fact.text))).toBe(true);
    expect(detail.facts.some((fact) => fact.text === "json")).toBe(true);
    expect(detail.location).toMatch(/\.json$/);
  });

  it("takes a table's column count from the document when the plan omits it", () => {
    const withDocument = stepDetail(table, [], {
      schema_version: 1,
      revision: 1,
      project: { name: "p", package: "p", data_directory: "data" },
      tables: [{ id: table.component?.split(":")[1] ?? "", declaration_name: "X", name: "x", fields: [{ name: "a", logical_type: { kind: "unit", name: "str" } }] }],
    });
    expect(withDocument.facts.some((fact) => fact.text === "1 declared columns")).toBe(true);
  });

  it("reads a projection's output fields from its lowered SQL", () => {
    const fields = selectedColumns(projection.sql);
    expect(fields.length).toBeGreaterThan(1);
    expect(detailOf(projection).facts[0]?.text).toMatch(/output fields/);
  });

  it("splits a binding's build keys from its properties", () => {
    expect(buildKeys(binding.sql)).toContain("build_key");
    expect(buildKeys(binding.sql)).toContain("source_build_key");
    expect(bindingProperties(binding.sql)).not.toContain("build_key");
    expect(bindingProperties(binding.sql)).not.toContain("_kg_binding_symbol");
    expect(detailOf(binding).summary).toMatch(/build key/);
  });

  it("badges an aggregate with UNION ALL and its fan-in", () => {
    const edges = (SAMPLE_PLAN.edges ?? []).filter((edge: StepEdge) => edge.to_step === aggregate.id);
    const detail = stepDetail(aggregate, edges, null);
    expect(detail.badges.map((badge) => badge.text)).toContain("UNION ALL");
    expect(detail.summary).toMatch(/binding view/);
  });

  it("says what an operator does, and what an export writes", () => {
    expect(detailOf(operator).summary).toMatch(/identical|already seen/);
    expect(detailOf(publish).summary).toMatch(/^→ graph\.jsonl$/);
  });

  it("recognises materialised steps only when the payload says so", () => {
    expect(isMaterialised(table)).toBe(false);
    expect(isMaterialised({ ...table, notes: ["materialized"] })).toBe(true);
    expect(isMaterialised({ ...table, payload: { materialize: true } })).toBe(true);
  });

  it("recovers a binding step's IR ref from its published role", () => {
    expect(binding.component ?? null).toBeNull();
    expect(stepRef(binding)).toBe("component:has_defect");
    expect(stepRef(table)).toBe(table.component);
  });

  it("shortens absolute paths for a 232 px card", () => {
    expect(shorten("/home/paul/Repos/data/sites.json", 12)).toBe("…/sites.json");
  });
});

describe("lane identity", () => {
  it("falls back to the module id when the plan declares no role", () => {
    expect(moduleRole("core")).toBe("core");
    expect(moduleRole("collapse_exact_duplicates")).toBe("operator");
    expect(moduleRole("neo4j")).toBe("target");
    expect(moduleRole("whatever", "operator")).toBe("operator");
  });

  it("gives two target modules different colours", () => {
    const colors = laneColors([
      { id: "file", role: "target" },
      { id: "neo4j", role: "target" },
      { id: "core", role: "core" },
    ]);
    expect(colors.get("file")).not.toBe(colors.get("neo4j"));
    expect(colors.get("core")).toBe(TOKEN.node);
  });
});
