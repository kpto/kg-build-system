import { describe, expect, it } from "vitest";

import { operationDetailFor } from "../lib/expressions";
import { buildViewerIndex } from "../lib/indexes";
import { loadSnapshotFromObject } from "../lib/load";
import type {
  Expression,
  ExpressionsPartDTO,
  OperationDTO,
} from "../lib/types";

const declaration = {
  name: "severity_rank",
  arity: 1,
  arguments: [
    {
      expected: { kind: "unit", name: "str" },
      description: "severity label",
    },
  ],
  parameters: [{ name: "fallback", required: false, default: 0 }],
  result_type: { kind: "unit", name: "int" },
  row_effect: "preserve",
} satisfies OperationDTO;

function snapshot(operations?: ExpressionsPartDTO) {
  return loadSnapshotFromObject({
    format: "kg-viewer-snapshot",
    version: 1,
    name: "operation-fixture",
    title: "Operation fixture",
    blueprint: {
      graph: { nodes: [], edges: [] },
      data: { structs: [], source_relations: [], derived_relations: [] },
      assets: [],
      bindings: [],
      ...(operations ? { operations } : {}),
    },
    workflow: { components: [], steps: [], connections: [], provenance: null },
  });
}

const expression: Expression = {
  kind: "operation",
  operator: ["expressions", "operation", "severity_rank"],
  arguments: [],
  logical_type: { kind: "unit", name: "int" },
};

describe("operation declarations", () => {
  it("indexes a custom operation by its reference name", () => {
    const index = buildViewerIndex(
      snapshot({ operations: [declaration] }),
    );

    expect(index.operationsByName.get("severity_rank")).toEqual(declaration);
  });

  it("resolves an operation node to its declared signature and description", () => {
    const index = buildViewerIndex(
      snapshot({ operations: [declaration] }),
    );

    expect(operationDetailFor(index.operationsByName, expression)).toBe(
      "severity_rank(str, fallback?) → int · severity label",
    );
  });

  it("keeps the actual result type when no declaration is published", () => {
    const index = buildViewerIndex(snapshot());
    const unknown: Expression = {
      ...expression,
      operator: ["expressions", "operation", "local_only"],
      logical_type: { kind: "nullable", value: { kind: "unit", name: "int" } },
    };

    expect(index.operationsByName).toHaveLength(0);
    expect(operationDetailFor(index.operationsByName, unknown)).toBe(
      "Nullable[int]",
    );
  });
});
