import { describe, expect, it } from "vitest";

import { collectionModel } from "../detail/model/collection";
import { contractIndex } from "./fixtures";

const index = contractIndex;

function layerTitles(model: ReturnType<typeof collectionModel>): string[] {
  return model.dependency.axes.flatMap((axis) =>
    axis.layers.map((layer) => layer.title),
  );
}

function dependantTitles(model: ReturnType<typeof collectionModel>): string[] {
  return model.dependants.axes.flatMap((axis) =>
    axis.layers.map((layer) => layer.title),
  );
}

describe("virtual collection model", () => {
  it("gives assets a dependency empty state and source relations as dependants", () => {
    const model = collectionModel(index, "assets");
    expect(model.dependency.axes).toEqual([]);
    expect(model.dependency.empty).toContain("origin");
    expect(dependantTitles(model)).toEqual(["Source relations"]);
    expect(model.items.rows.map((row) => row.name)).toEqual(["estate"]);
  });

  it("reads the full layer DAG below a derived relation collection", () => {
    const model = collectionModel(index, "derivedRelations");
    expect(layerTitles(model)).toEqual([
      "Assets",
      "Source relations",
      "Derived relations",
    ]);
    const current = model.dependency.axes
      .flatMap((axis) => axis.layers)
      .find((layer) => layer.current);
    expect(current?.title).toBe("Derived relations");
  });

  it("keeps dependants to one layer above the source relation collection", () => {
    const model = collectionModel(index, "sourceRelations");
    expect(dependantTitles(model)).toEqual(["Derived relations", "Bindings"]);
    expect(model.dependants.axes[0].layers.map((layer) => layer.count)).toEqual([
      1, 1,
    ]);
  });

  it("does not treat an indirect binding as a derived relation dependant", () => {
    const model = collectionModel(index, "derivedRelations");
    // The fixture binding reads the source relation, not the derived relation.
    expect(dependantTitles(model)).toEqual(["Derived relations", "Bindings"]);
    expect(
      model.dependants.axes[0].layers.map((layer) => layer.count),
    ).toEqual([0, 0]);
  });

  it("puts node and edge records above a binding collection", () => {
    const model = collectionModel(index, "bindings");
    expect(dependantTitles(model)).toEqual(["Nodes", "Edges"]);
    expect(model.dependants.axes[0].layers.map((layer) => layer.count)).toEqual([
      1, 0,
    ]);
    expect(model.items.rows).toHaveLength(1);
  });

  it("includes abstract nodes and abstract edges as abstract items", () => {
    const model = collectionModel(index, "abstract");
    expect(model.items.rows.map((row) => row.name)).toEqual(["documented"]);
    expect(model.items.rows[0].concept).toBe("abstract");
    // The abstract's dependency is its own binding layer, not its descendants.
    expect(layerTitles(model)).toContain("Bindings");
    expect(model.dependency.axes[0].layers.at(-2)?.count).toBe(0);
  });

  it("gives a workflow component its downstream component as dependant", () => {
    const model = collectionModel(index, "workflow", "duckdb");
    expect(model.items.rows.map((row) => row.name)).toEqual(["source.surveys"]);
    expect(
      model.dependants.axes.flatMap((axis) => axis.layers).map((layer) => layer.title),
    ).toEqual(["core"]);
  });

  it("lists workflow components as a collection of component groups", () => {
    const model = collectionModel(index, "workflow");
    expect(model.items.rows.map((row) => row.name).sort()).toEqual([
      "core",
      "duckdb",
    ]);
    expect(model.items.rows.every((row) => row.collection?.id === "workflow")).toBe(
      true,
    );
  });
});
