import { describe, expect, it } from "vitest";

import { involvedWorkflowRows } from "../detail/model/involvedSteps";
import { contractIndex as index } from "./fixtures";

describe("involved steps", () => {
  it("resolves a binding step and the plan neighbour it reads", () => {
    const rows = involvedWorkflowRows(index, {
      kind: "binding",
      component: "defect",
      bindingIndex: 0,
    });
    expect(rows.map((row) => row.id)).toEqual([
      ["core", "binding.0"],
      ["duckdb", "source.surveys"],
    ]);
  });

  it("resolves a record through its bindings", () => {
    const rows = involvedWorkflowRows(index, {
      kind: "node",
      component: "defect",
    });
    expect(rows.map((row) => row.id)).toEqual([
      ["core", "binding.0"],
      ["duckdb", "source.surveys"],
    ]);
  });

  it("resolves a step and its immediate plan neighbours", () => {
    const rows = involvedWorkflowRows(index, {
      kind: "step",
      component: "core",
      name: "binding.0",
      stepId: ["core", "binding.0"],
    });
    expect(rows.map((row) => row.id)).toEqual([
      ["core", "binding.0"],
      ["duckdb", "source.surveys"],
    ]);
  });

  it("resolves a binding collection to the same steps", () => {
    const rows = involvedWorkflowRows(index, {
      kind: "collection",
      collection: "bindings",
    });
    expect(rows).toHaveLength(2);
  });
});
