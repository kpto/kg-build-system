import { describe, expect, it } from "vitest";

import {
  collectionDagModel,
  collectionModel,
} from "../detail/model/collection";
import { constitutionModel } from "../detail/model/constitution";
import { buildConstitutionScene } from "../detail/view/constitutionScene";
import { buildViewerIndex } from "../lib/indexes";
import { loadSnapshotFromObject } from "../lib/load";
import { contractIndex, contractSnapshot } from "./fixtures";

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
    expect(model.items.rows[0].concept).toBe("abstractNode");
    // The abstract's dependency is its own binding layer, not its descendants.
    expect(layerTitles(model)).toContain("Bindings");
    expect(model.dependency.axes[0].layers.at(-2)?.count).toBe(0);
  });

  it("reads abstract edges alongside abstract nodes", () => {
    const index = buildViewerIndex(
      loadSnapshotFromObject({
        ...contractSnapshot,
        blueprint: {
          ...contractSnapshot.blueprint,
          graph: {
            ...contractSnapshot.blueprint.graph,
            edges: [
              ...contractSnapshot.blueprint.graph.edges,
              {
                name: "related_to",
                labels: ["RELATED_TO"],
                abstract: true,
                properties: [],
                source: ["topology", "node", "documented"],
                target: ["topology", "node", "documented"],
                meaning: { claims: [{ text: "An abstract edge." }] },
              },
            ],
          },
        },
      }),
    );
    const model = collectionModel(index, "abstract");
    expect(model.items.rows.map((row) => row.name)).toEqual([
      "documented",
      "related_to",
    ]);
    expect(model.items.rows.map((row) => row.concept)).toEqual([
      "abstractNode",
      "abstractEdge",
    ]);

    const dag = collectionDagModel(index, model, "dependency");
    expect(dag.layers?.map((layer) => layer.name)).toEqual(
      expect.arrayContaining(["documented", "related_to"]),
    );
  });

  it("does not add an empty-binding note to a constitution", () => {
    const model = constitutionModel(contractIndex, {
      level: "abstract",
      component: "documented",
      abstract: true,
    });
    const scene = buildConstitutionScene(model);
    expect(scene.notes.map((note) => note.text)).not.toContain(
      "No binding meets these two axes.",
    );
  });

  it("gives a workflow component its downstream component as dependant", () => {
    const model = collectionModel(index, "workflow", "duckdb");
    expect(model.items.rows.map((row) => row.name)).toEqual(["source.surveys"]);
    expect(
      model.dependants.axes.flatMap((axis) => axis.layers).map((layer) => layer.title),
    ).toEqual(["core"]);
  });

  it("reads a collection's actual subjects as a constitution DAG", () => {
    const collection = collectionModel(index, "derivedRelations");
    const dag = collectionDagModel(index, collection, "dependency");
    expect(dag.direction).toBe("dependency");
    expect(dag.layers?.map((layer) => layer.name)).toEqual([
      "defect",
      "surveys",
      "estate",
    ]);
    expect(dag.layerEdges).toEqual([
      { source: "asset:estate", target: "relation:surveys" },
      { source: "relation:surveys", target: "projection:defect" },
    ]);
    const scene = buildConstitutionScene(dag);
    expect(scene.frames.map((frame) => frame.id)).toEqual(["relation"]);
    for (const node of scene.nodes) {
      expect(
        scene.frames.some(
          (frame) =>
            node.x >= frame.x &&
            node.y >= frame.y &&
            node.x + node.width <= frame.x + frame.width &&
            node.y + node.height <= frame.y + frame.height,
        ),
      ).toBe(true);
    }
  });

  it("reads one layer above a collection as its contribution DAG", () => {
    const collection = collectionModel(index, "sourceRelations");
    const dag = collectionDagModel(index, collection, "contribution");
    expect(dag.direction).toBe("contribution");
    expect(dag.layers?.map((layer) => layer.name)).toEqual([
      "surveys",
      "defect",
      "defect.title",
    ]);
    expect(dag.layers?.map((layer) => layer.kind)).toEqual([
      "relation",
      "projection",
      "binding",
    ]);
    expect(dag.layerEdges).toEqual([
      { source: "relation:surveys", target: "projection:defect" },
      { source: "relation:surveys", target: "binding:0" },
    ]);
    expect(dag.layers?.every((layer) => layer.collection === undefined)).toBe(
      true,
    );
  });

  it("states that assets are the origin in the collection constitution", () => {
    const dag = collectionDagModel(
      index,
      collectionModel(index, "assets"),
      "dependency",
    );
    expect(dag.layers?.map((layer) => layer.name)).toEqual(["estate"]);
    expect(dag.note).toContain("origin");
    const scene = buildConstitutionScene(dag);
    expect(scene.notes.map((note) => note.text)).toContain(
      "Assets are the origin. No layer is below an asset.",
    );
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
