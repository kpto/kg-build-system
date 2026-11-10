import { describe, expect, it } from "vitest";

import { contractIndex } from "./fixtures";
import {
  buildWorkflowComponentMap,
  buildWorkflowModel,
  DEFAULT_WORKFLOW_FILTERS,
  filterWorkflowRows,
  formatArtifactType,
  formatStepId,
  groupWorkflowRows,
} from "../workflow/model/WorkflowViewModel";

const model = buildWorkflowModel(contractIndex);

describe("workflow view model", () => {
  it("indexes every step, component and instruction kind", () => {
    expect(model.steps).toBe(2);
    expect(model.connections).toBe(1);
    expect(model.components).toEqual(["core", "duckdb"]);
    expect(model.kinds).toEqual([{ key: "sql:duckdb", label: "sql:duckdb", count: 2 }]);
    expect(model.rows.map((row) => row.name)).toEqual([
      "binding.0",
      "source.surveys",
    ]);
  });

  it("filters by component, instruction kind and query", () => {
    expect(
      filterWorkflowRows(model.rows, {
        ...DEFAULT_WORKFLOW_FILTERS,
        component: "core",
      }).map((row) => row.key),
    ).toEqual(["core\u0000binding.0"]);

    expect(
      filterWorkflowRows(model.rows, {
        ...DEFAULT_WORKFLOW_FILTERS,
        kind: "sql:duckdb",
      }),
    ).toHaveLength(2);

    expect(
      filterWorkflowRows(model.rows, {
        ...DEFAULT_WORKFLOW_FILTERS,
        query: "surveys",
      }).map((row) => row.name),
    ).toEqual(["source.surveys"]);
  });

  it("groups visible rows in snapshot order", () => {
    expect(groupWorkflowRows(model.rows)).toEqual([
      { component: "core", rows: [expect.objectContaining({ name: "binding.0" })] },
      {
        component: "duckdb",
        rows: [expect.objectContaining({ name: "source.surveys" })],
      },
    ]);
  });

  it("aggregates the plan into a component map", () => {
    const map = buildWorkflowComponentMap(contractIndex, model);
    expect(map.nodes).toEqual([
      expect.objectContaining({ id: "core", steps: 1, outgoing: 0, incoming: 1 }),
      expect.objectContaining({ id: "duckdb", steps: 1, outgoing: 1, incoming: 0 }),
    ]);
    expect(map.edges).toEqual([
      {
        id: "component-edge:duckdb:core",
        source: "duckdb",
        target: "core",
        count: 1,
      },
    ]);
  });

  it("formats identities and artifact types", () => {
    expect(formatStepId(["core", "binding.0"])).toBe("core / binding.0");
    expect(formatArtifactType(["core", "binding", "defect"])).toBe(
      "core:binding:defect",
    );
  });
});
