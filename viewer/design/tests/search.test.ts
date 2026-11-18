import { describe, expect, it } from "vitest";
import { searchIndex } from "../lib/search";
import { index } from "./fixtures";

describe("search", () => {
  it("finds properties and opens the property route data", () => {
    const result = searchIndex(index.searchRecords, "defect.title", { limit: 10 });
    const property = result.find((record) => record.kind === "property");
    expect(property).toBeDefined();
    expect(property).toMatchObject({
      component: "defect",
      property: "title",
      entityKind: "node",
    });
  });

  it("finds assets by name and semantics", () => {
    const byName = searchIndex(index.searchRecords, "estate");
    expect(byName.some((record) => record.kind === "asset" && record.name === "estate")).toBe(
      true,
    );
    const bySemantics = searchIndex(index.searchRecords, "monitored estate", {
      limit: 100,
    });
    expect(bySemantics.some((record) => record.kind === "asset")).toBe(true);
  });

  it("finds instruction kinds and their steps", () => {
    const results = searchIndex(index.searchRecords, "sql:duckdb", { limit: 100 });
    expect(results.some((record) => record.kind === "instruction")).toBe(true);
    expect(results.some((record) => record.kind === "step")).toBe(true);
    const instruction = results.find((record) => record.kind === "instruction");
    expect(instruction?.instructionKind).toEqual(["sql", "duckdb"]);
  });

  it("finds workflow steps by component and name", () => {
    const results = searchIndex(index.searchRecords, "binding.0", { limit: 20 });
    expect(
      results.some(
        (record) =>
          record.kind === "step" &&
          record.stepId?.[0] === "core" &&
          record.stepId?.[1] === "binding.0",
      ),
    ).toBe(true);
  });

  it("filters by kind and handles empty queries", () => {
    expect(searchIndex(index.searchRecords, "")).toEqual([]);
    const properties = searchIndex(index.searchRecords, "defect", {
      kinds: ["property"],
    });
    expect(properties.length).toBeGreaterThan(0);
    expect(properties.every((record) => record.kind === "property")).toBe(true);
  });

  it("requires every query token to match", () => {
    const results = searchIndex(index.searchRecords, "defect temperature", { limit: 10 });
    expect(results.some((record) => record.name.includes("defect"))).toBe(false);
  });
});
