import { describe, expect, it } from "vitest";

import { buildAudit } from "../lib/audit";
import { buildViewerIndex } from "../lib/indexes";
import { loadSnapshotFromObject } from "../lib/load";
import type { Expression, LogicalType } from "../lib/types";

const SEMANTICS = { claims: [{ text: "Fixture semantic unit." }] };

function unit(name: string): LogicalType {
  return { kind: "unit", name };
}

function nullable(value: LogicalType): LogicalType {
  return { kind: "nullable", value };
}

function array(item: LogicalType): LogicalType {
  return { kind: "array", item };
}

function field(
  owner: string,
  name: string,
  type: LogicalType,
  semantics = true,
): Record<string, unknown> {
  return {
    name,
    logical_type: type,
    ref: ["data", "field", `${owner}.${name}`],
    ...(semantics ? { semantics: SEMANTICS } : {}),
  };
}

function fieldRef(owner: string, name: string): string[] {
  return ["data", "field", `${owner}.${name}`];
}

function fieldExpr(owner: string, name: string, type: LogicalType): Expression {
  return { kind: "field", field: fieldRef(owner, name), path: [], logical_type: type };
}

function literalExpr(value: unknown, type: LogicalType): Expression {
  return { kind: "literal", value, logical_type: type };
}

function op(name: string, args: Expression[], type: LogicalType): Expression {
  return {
    kind: "operation",
    operator: ["expressions", "operation", name],
    arguments: args,
    logical_type: type,
  };
}

function property(name: string, type: LogicalType): Record<string, unknown> {
  return {
    name,
    logical_type: type,
    ref: ["topology", "property", name],
    annotations: [],
    semantics: SEMANTICS,
  };
}

function node(
  name: string,
  properties: Array<Record<string, unknown>>,
  extra: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    name,
    abstract: false,
    properties: properties.map((entry) => ({
      ...entry,
      ref: ["topology", "property", `${name}.${String(entry.name)}`],
    })),
    annotations: [],
    description: `${name} fixture node`,
    semantics: SEMANTICS,
    ...extra,
  };
}

function edge(
  name: string,
  properties: Array<Record<string, unknown>>,
  extra: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    name,
    abstract: false,
    source: ["topology", "node", "child"],
    target: ["topology", "node", "fallback_node"],
    properties: properties.map((entry) => ({
      ...entry,
      ref: ["topology", "property", `${name}.${String(entry.name)}`],
    })),
    annotations: [],
    description: `${name} fixture edge`,
    semantics: SEMANTICS,
    ...extra,
  };
}

function binding(
  kind: "node" | "edge",
  component: string,
  input: {
    identity?: Expression;
    source_identity?: Expression;
    target_identity?: Expression;
    properties?: Record<string, Expression>;
    rows?: Record<string, unknown>;
  },
): Record<string, unknown> {
  return {
    kind,
    [kind]: ["topology", kind, component],
    ...input,
    annotations: [],
    semantics: SEMANTICS,
  };
}

/** A fixture with one deliberate instance of every audit rule. */
function fixture() {
  return {
    format: "kg-viewer-snapshot",
    version: 1,
    name: "audit-fixture",
    title: "Audit fixture",
    blueprint: {
      graph_declaration: {
        name: "audit_graph",
        description: "Graph used by the audit engine tests.",
        semantics: {
          claims: [{ text: "The fixture graph states its purpose." }],
          purpose: { text: "Exercise every deterministic audit rule." },
        },
      },
      graph: {
        nodes: [
          node(
            "category",
            [property("inherited", unit("str"))],
            {
              abstract: true,
              description: "An abstract category with one inherited property.",
            },
          ),
          node(
            "child",
            [
              property("id", unit("str")),
              property("unbound", unit("str")),
              property("literal_only", unit("str")),
              property("type_shape", unit("str")),
              property("required", unit("str")),
            ],
            { parent: ["topology", "node", "category"] },
          ),
          node("fallback_node", [property("id", unit("str"))]),
          node("nullable_node", [property("id", unit("str"))]),
          node("unbound_node", [property("id", unit("str"))]),
          node("duplicate_node", [property("id", unit("str"))]),
          node("multi_node", [property("id", unit("str"))]),
          node("nosource_node", [property("id", unit("str"))]),
          node("empty_category", [], {
            abstract: true,
            description: "An abstract category with no producer.",
          }),
        ],
        edges: [
          edge("child_edge", [property("weight", unit("str"))]),
          edge("nullable_edge", [property("weight", unit("str"))]),
        ],
      },
      data: {
        relations: [
          {
            name: "source_a",
            asset: ["asset", "asset", "asset_a"],
            columns: [
              field("source_a", "id", unit("str")),
              field("source_a", "value", unit("str")),
              field("source_a", "optional", nullable(unit("str"))),
              field("source_a", "list", array(unit("str"))),
            ],
            annotations: [],
            description: "The primary fixture source.",
            semantics: SEMANTICS,
          },
          {
            name: "source_b",
            asset: ["asset", "asset", "asset_a"],
            columns: [field("source_b", "id", unit("str")), field("source_b", "value", unit("str"))],
            annotations: [],
            description: "The alternate fixture source.",
            semantics: SEMANTICS,
          },
          {
            name: "plain_relation",
            asset: ["asset", "asset", "asset_a"],
            columns: [
              {
                name: "id",
                logical_type: unit("str"),
                ref: ["data", "field", "plain_relation.id"],
                annotations: [],
              },
            ],
            annotations: [],
            description: "A relation with no attached semantics.",
          },
        ],
        projections: [
          {
            name: "projection_a",
            columns: [
              {
                name: "id",
                logical_type: unit("str"),
                ref: ["data", "field", "projection_a.id"],
                annotations: [],
                semantics: SEMANTICS,
              },
            ],
            annotations: [],
            description: "A projection of source_a.",
            row_source: { kind: "scan", relation: ["data", "relation", "source_a"] },
            semantics: SEMANTICS,
          },
        ],
        structs: [
          {
            name: "struct_a",
            columns: [
              {
                name: "id",
                logical_type: unit("str"),
                ref: ["data", "field", "struct_a.id"],
                annotations: [],
                semantics: SEMANTICS,
              },
            ],
            annotations: [],
            description: "A fixture struct.",
            semantics: SEMANTICS,
          },
        ],
      },
      assets: [
        {
          name: "asset_a",
          layout: { kind: "json", locator: "fixture://audit" },
          profile: {
            subject: "the audit fixture",
            coverage: "synthetic rows",
            authority: "primary",
            basis: "fixture",
          },
          annotations: [],
          semantics: SEMANTICS,
        },
      ],
      bindings: [
        binding("node", "child", {
          identity: fieldExpr("source_a", "id", unit("str")),
          properties: {
            id: fieldExpr("source_a", "id", unit("str")),
            literal_only: literalExpr("constant", unit("str")),
            type_shape: fieldExpr("source_a", "list", array(unit("str"))),
            required: fieldExpr("source_a", "optional", nullable(unit("str"))),
          },
          rows: { kind: "scan", relation: ["data", "relation", "source_a"] },
        }),
        binding("node", "fallback_node", {
          identity: op(
            "coalesce",
            [fieldExpr("source_a", "optional", nullable(unit("str"))), literalExpr("fallback", unit("str"))],
            unit("str"),
          ),
          properties: { id: fieldExpr("source_a", "value", unit("str")) },
          rows: { kind: "scan", relation: ["data", "relation", "source_a"] },
        }),
        binding("node", "nullable_node", {
          identity: fieldExpr("source_a", "optional", nullable(unit("str"))),
          properties: { id: fieldExpr("source_a", "value", unit("str")) },
          rows: { kind: "scan", relation: ["data", "relation", "source_a"] },
        }),
        binding("node", "duplicate_node", {
          identity: fieldExpr("source_a", "id", unit("str")),
          properties: { id: fieldExpr("source_a", "value", unit("str")) },
          rows: { kind: "scan", relation: ["data", "relation", "source_a"] },
        }),
        binding("node", "duplicate_node", {
          identity: fieldExpr("source_a", "id", unit("str")),
          properties: { id: fieldExpr("source_a", "value", unit("str")) },
          rows: { kind: "scan", relation: ["data", "relation", "source_a"] },
        }),
        binding("node", "multi_node", {
          identity: fieldExpr("source_a", "id", unit("str")),
          properties: { id: fieldExpr("source_a", "value", unit("str")) },
          rows: { kind: "scan", relation: ["data", "relation", "source_a"] },
        }),
        binding("node", "multi_node", {
          identity: fieldExpr("source_b", "id", unit("str")),
          properties: { id: fieldExpr("source_b", "value", unit("str")) },
          rows: { kind: "scan", relation: ["data", "relation", "source_b"] },
        }),
        binding("node", "nosource_node", {
          identity: fieldExpr("source_a", "id", unit("str")),
          properties: { id: fieldExpr("source_a", "value", unit("str")) },
        }),
        binding("edge", "child_edge", {
          identity: fieldExpr("source_a", "id", unit("str")),
          target_identity: fieldExpr("source_a", "id", unit("str")),
          properties: { weight: fieldExpr("source_a", "value", unit("str")) },
          rows: { kind: "scan", relation: ["data", "relation", "source_a"] },
        }),
        binding("edge", "nullable_edge", {
          identity: fieldExpr("source_a", "id", unit("str")),
          source_identity: fieldExpr("source_a", "optional", nullable(unit("str"))),
          target_identity: fieldExpr("source_a", "id", unit("str")),
          properties: { weight: fieldExpr("source_a", "value", unit("str")) },
          rows: { kind: "scan", relation: ["data", "relation", "source_a"] },
        }),
      ],
    },
    workflow: {
      components: [{ id: "fixture", version: "1" }],
      steps: [],
      connections: [],
    },
    report: {
      published_artifacts: [],
      recovered_failures: [],
      unresolved_failures: [],
    },
  };
}

const index = buildViewerIndex(loadSnapshotFromObject(fixture()));
const audit = buildAudit(index);

function findingsFor(rule: string) {
  return audit.findings.filter((finding) => finding.rule === rule);
}

function one(rule: string, predicate: (finding: (typeof audit.findings)[number]) => boolean) {
  const finding = findingsFor(rule).find(predicate);
  if (!finding) {
    throw new Error(
      `missing ${rule}; saw ${findingsFor(rule)
        .map((entry) => `${entry.subject?.name}/${entry.subject?.property ?? ""}`)
        .join(", ")}`,
    );
  }
  return finding;
}

describe("audit engine", () => {
  it("is deterministic, uses stable ids and computes no rubric", () => {
    expect(buildAudit(index)).toEqual(audit);
    expect(audit.score).toEqual({ value: 0, components: [] });
    expect(new Set(audit.findings.map((finding) => finding.id)).size).toBe(
      audit.findings.length,
    );
    for (const finding of audit.findings) {
      expect(finding.id).toMatch(/^finding:[a-z.-]+:[0-9a-f]{8}$/);
      expect(finding.evidence.length).toBeGreaterThan(0);
    }
    const counted = Object.values(audit.counts).reduce(
      (total, value) => total + value,
      0,
    );
    expect(counted).toBe(audit.findings.length);
    expect(audit.questions).toEqual(
      audit.findings.filter((finding) => Boolean(finding.question)),
    );
  });

  it("reports a fallback key as high", () => {
    const finding = one(
      "identity.key-fallback",
      (entry) => entry.subject?.component === "fallback_node",
    );
    expect(finding.severity).toBe("high");
    expect(finding.subject?.kind).toBe("node");
    expect(finding.subject?.bindingIndex).toBe(1);
    expect(finding.evidence[0].jsonPointer).toBe("/bindings/1/identity");
  });

  it("reports a nullable key without drop_null as high", () => {
    const finding = one(
      "identity.nullable-key",
      (entry) => entry.subject?.component === "nullable_node",
    );
    expect(finding.severity).toBe("high");
    expect(finding.subject?.entityKind).toBe("node");
    expect(finding.subject?.bindingIndex).toBe(2);
  });

  it("reports nullable and missing edge endpoints as high", () => {
    const nullable = one(
      "identity.edge-endpoint-nullable",
      (entry) => entry.subject?.component === "nullable_edge",
    );
    expect(nullable.severity).toBe("high");
    expect(nullable.detail).toContain("source");
    expect(nullable.evidence[0].jsonPointer).toBe("/bindings/9/source_identity");

    const missing = one(
      "identity.missing-endpoint",
      (entry) => entry.subject?.component === "child_edge",
    );
    expect(missing.severity).toBe("high");
    expect(missing.detail).toContain("source");
    expect(missing.evidence.map((entry) => entry.jsonPointer)).toEqual(
      expect.arrayContaining(["/bindings/8/source_identity", "/bindings/8/target_identity"]),
    );
  });

  it("reports duplicate producers and multi-source components", () => {
    const duplicate = one(
      "identity.duplicate-producer",
      (entry) => entry.subject?.component === "duplicate_node",
    );
    expect(duplicate.severity).toBe("high");
    expect(duplicate.evidence.map((entry) => entry.jsonPointer)).toEqual([
      "/bindings/3",
      "/bindings/4",
    ]);

    const multi = one(
      "identity.multi-source-component",
      (entry) => entry.subject?.component === "multi_node",
    );
    expect(multi.severity).toBe("high");
    expect(multi.evidence.map((entry) => entry.jsonPointer)).toEqual([
      "/bindings/5",
      "/bindings/6",
    ]);
  });

  it("reports unbound components and abstract categories", () => {
    const unbound = one(
      "identity.unbound-component",
      (entry) => entry.subject?.name === "unbound_node",
    );
    expect(unbound.severity).toBe("high");
    expect(unbound.subject?.kind).toBe("node");

    const abstract = one(
      "identity.abstract-no-producer",
      (entry) => entry.subject?.name === "empty_category",
    );
    expect(abstract.severity).toBe("medium");
    expect(abstract.subject?.kind).toBe("node");
  });

  it("reports a concrete component that does not bind an inherited property", () => {
    const finding = one(
      "identity.inherited-property-missing",
      (entry) =>
        entry.subject?.component === "child" && entry.subject?.property === "inherited",
    );
    expect(finding.severity).toBe("high");
    expect(finding.subject?.entityKind).toBe("node");
    expect(finding.evidence.map((entry) => entry.jsonPointer)).toEqual(
      expect.arrayContaining([
        "/graph/nodes/0/properties/0",
        "/graph/nodes/1",
      ]),
    );
  });

  it("reports unbound and literal-only properties", () => {
    const unbound = one(
      "coverage.unbound-property",
      (entry) =>
        entry.subject?.component === "child" && entry.subject?.property === "unbound",
    );
    expect(unbound.severity).toBe("high");
    expect(unbound.subject?.kind).toBe("property");

    const literal = one(
      "coverage.literal-only",
      (entry) =>
        entry.subject?.component === "child" && entry.subject?.property === "literal_only",
    );
    expect(literal.severity).toBe("medium");
    expect(literal.detail).toContain("constant");
  });

  it("reports a binding with fields but no source relation or step", () => {
    const finding = one(
      "coverage.no-source",
      (entry) => entry.subject?.component === "nosource_node",
    );
    expect(finding.severity).toBe("medium");
    expect(finding.subject?.kind).toBe("binding");
    expect(finding.subject?.bindingIndex).toBe(7);
  });

  it("reports semantics presence at the right severity", () => {
    const relation = one(
      "semantics.missing",
      (entry) => entry.subject?.kind === "relation" && entry.subject?.name === "plain_relation",
    );
    expect(relation.severity).toBe("medium");
    expect(
      findingsFor("semantics.missing").some(
        (entry) => entry.subject?.name === "source_a",
      ),
    ).toBe(false);

    const field = one(
      "semantics.missing",
      (entry) =>
        entry.subject?.kind === "field" &&
        entry.subject?.name === "id" &&
        entry.subject?.component === "plain_relation",
    );
    expect(field.severity).toBe("low");
  });

  it("reports nullable expressions into required properties and shape mismatches", () => {
    const presence = one(
      "type.presence-mismatch",
      (entry) =>
        entry.subject?.component === "child" && entry.subject?.property === "required",
    );
    expect(presence.severity).toBe("high");
    expect(presence.detail).toContain("nullable");

    const shape = one(
      "type.shape-mismatch",
      (entry) =>
        entry.subject?.component === "child" && entry.subject?.property === "type_shape",
    );
    expect(shape.severity).toBe("high");
    expect(shape.detail).toContain("array");
    expect(shape.detail).toContain("unit");
  });

  it("keeps graph purpose present when the declaration states one", () => {
    expect(findingsFor("graph.purpose-missing")).toHaveLength(0);
  });

  it("reports a missing graph purpose as critical", () => {
    const missing = buildViewerIndex(
      loadSnapshotFromObject({
        format: "kg-viewer-snapshot",
        version: 1,
        name: "no-graph",
        title: "No graph",
        blueprint: {
          graph: { nodes: [], edges: [] },
          data: { relations: [], projections: [], structs: [] },
          assets: [],
          bindings: [],
        },
        workflow: { components: [], steps: [], connections: [] },
        report: {
          published_artifacts: [],
          recovered_failures: [],
          unresolved_failures: [],
        },
      }),
    );
    const finding = buildAudit(missing).findings.find(
      (entry) => entry.rule === "graph.purpose-missing",
    );
    expect(finding).toBeDefined();
    expect(finding?.severity).toBe("critical");
    expect(finding?.subject?.kind).toBe("graph");
    expect(finding?.evidence[0].jsonPointer).toBe("/graph_declaration");
  });
});
