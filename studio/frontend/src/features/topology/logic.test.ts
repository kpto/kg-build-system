import { describe, expect, it } from "vitest";

import {
  autoLayout,
  createComponent,
  createEdgePair,
  buildGraph,
  categoryEndpoint,
  componentRef,
  deleteImpact,
  deriveIdentity,
  emptySlot,
  findCategoryEdgeForPair,
  freePosition,
  normalizeSlot,
  positionOf,
  prunePositions,
  removeComponentCascade,
  setSlotOptional,
  setSlotType,
  slotAllowsOptional,
  templateCatalogue,
  vertexShape,
  withPosition,
  withPositions,
  canBeMixin,
  canBeParent,
  canBeEndpoint,
  DEFAULT_EDGE_SIZE,
  DEFAULT_FILTERS,
  DEFAULT_NODE_SIZE,
  type LinkKind,
  type LinkView,
  type TopologyGraph,
  type VertexShape,
  type VertexSize,
  type VertexView,
} from "./logic";
import { SAMPLE_DOCUMENT } from "@/lib/sampleDocument";
import type { Component, Point, ProjectDocument } from "@/lib/ir";
import { array, nullable, unit } from "@/lib/ir";

const clone = (): ProjectDocument => JSON.parse(JSON.stringify(SAMPLE_DOCUMENT)) as ProjectDocument;

/** A document extended with extra components (models are frozen, so rebuild). */
function withComponents(document: ProjectDocument, extra: readonly Component[]): ProjectDocument {
  return { ...document, components: [...(document.components ?? []), ...extra] };
}

describe("createComponent — framework-legal defaults", () => {
  it("derives id, logical name and declaration_name from the display name", () => {
    const identity = deriveIdentity(clone(), "Pump Room", "node", "concrete");
    expect(identity.id).toBe("pump_room");
    expect(identity.name).toBe("pump_room");
    expect(identity.declaration_name).toBe("PumpRoomNode");
  });

  it("spells the tier suffix the generator uses for each tier", () => {
    expect(deriveIdentity(clone(), "audited", "node", "template").declaration_name).toBe(
      "AuditedNodeTemplate",
    );
    expect(deriveIdentity(clone(), "audited", "edge", "category").declaration_name).toBe(
      "AuditedAbstractEdge",
    );
  });

  it("gives a concrete node the framework-required category parent, creating one on demand", () => {
    const document = clone();
    const { component, createdCategory } = createComponent(document, {
      displayName: "Pump Room",
      kind: "node",
      tier: "concrete",
    });
    // The sample has a `documented` node category, so it should be offered/used only when
    // chosen; with no parent chosen it mints an `unnamed`-style category.
    expect(component.tier).toBe("concrete");
    expect(component.kind).toBe("node");
    expect(createdCategory).not.toBeNull();
    expect(component.parent).toBe(createdCategory?.id);
    expect(createdCategory?.tier).toBe("category");
    expect(createdCategory?.label).toBe("Unnamed");
    expect(canBeParent("node", "concrete", createdCategory as Component)).toBe(true);
  });

  it("uses a chosen existing category parent instead of minting one", () => {
    const { component, createdCategory } = createComponent(clone(), {
      displayName: "Pump Room",
      kind: "node",
      tier: "concrete",
      parentId: "documented",
    });
    expect(component.parent).toBe("documented");
    expect(createdCategory).toBeNull();
  });

  it("leaves templates without a parent or label (spec §3)", () => {
    const { component } = createComponent(clone(), {
      displayName: "audited",
      kind: "node",
      tier: "template",
    });
    expect(component.parent).toBeNull();
    expect(component.label).toBeNull();
    expect(component.properties).toEqual([]);
  });

  it("never collides on an id already present in the document", () => {
    const document = clone();
    const { component } = createComponent(document, {
      displayName: "site",
      kind: "node",
      tier: "concrete",
      parentId: "documented",
    });
    expect(component.id).not.toBe("site");
    expect(component.id.startsWith("site")).toBe(true);
  });
});

describe("kind / tier legality", () => {
  it("accepts a same-kind category parent and rejects the rest", () => {
    const category = component("documented", "node", "category");
    expect(canBeParent("node", "concrete", category)).toBe(true);
    expect(canBeParent("edge", "concrete", category)).toBe(false);
    expect(canBeParent("node", "template", category)).toBe(false);
  });

  it("only mixes same-kind templates (R3)", () => {
    const nodeTemplate = component("provenanced_node", "node", "template");
    const edgeTemplate = component("audited", "edge", "template");
    const site = component("site", "node", "concrete");
    expect(canBeMixin(site, nodeTemplate)).toBe(true);
    expect(canBeMixin(site, edgeTemplate)).toBe(false);
  });

  it("only node components are valid endpoints (node-side root, spec §6)", () => {
    expect(canBeEndpoint(component("site", "node", "concrete"))).toBe(true);
    expect(canBeEndpoint(component("documented", "node", "category"))).toBe(true);
    expect(canBeEndpoint(component("has_unit", "edge", "concrete"))).toBe(false);
    expect(canBeEndpoint(null)).toBe(false);
  });
});

describe("createEdgePair — category construction and kind pairing", () => {
  it("reuses the existing category edge over an endpoint pair instead of minting one", () => {
    const document = clone();
    // site + unit both descend from `documented`, and the sample already carries the
    // `monitored_relation` category over documented->documented.
    expect(categoryEndpoint(document, "site")).toBe("documented");
    expect(categoryEndpoint(document, "unit")).toBe("documented");
    expect(findCategoryEdgeForPair(document, "documented", "documented")?.id).toBe(
      "monitored_relation",
    );

    const result = createEdgePair(document, {
      predicate: "has part",
      label: "HAS_PART",
      sourceId: "site",
      targetId: "unit",
      createCategoryIfMissing: true,
    });
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.concrete.source).toBe("site");
    expect(result.concrete.target).toBe("unit");
    expect(result.concrete.tier).toBe("concrete");
    expect(result.concrete.parent).toBe("monitored_relation");
    expect(result.createdCategory).toBeNull();
  });

  it("mints a category edge over the endpoints' categories when none exists", () => {
    const document = pairableDocument();
    // `gadget` descends from `locatable`, so documented->locatable has no category edge.
    const result = createEdgePair(document, {
      predicate: "mounts",
      label: "MOUNTS",
      sourceId: "site",
      targetId: "gadget",
      createCategoryIfMissing: true,
    });
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.createdCategory).not.toBeNull();
    expect(result.createdCategory?.tier).toBe("category");
    expect(result.createdCategory?.source).toBe("documented");
    expect(result.createdCategory?.target).toBe("locatable");
    expect(result.concrete.parent).toBe(result.createdCategory?.id);
    expect(result.concrete.source).toBe("site");
    expect(result.concrete.target).toBe("gadget");
  });

  it("refuses a node -> edge pairing (mismatched kinds)", () => {
    const result = createEdgePair(clone(), {
      predicate: "bad",
      label: "BAD",
      sourceId: "site",
      targetId: "has_unit",
      createCategoryIfMissing: true,
    });
    expect(result.ok).toBe(false);
  });

  it("refuses a concrete edge with no category parent and no consent to create one", () => {
    const document = pairableDocument();
    const result = createEdgePair(document, {
      predicate: "mounts",
      label: "MOUNTS",
      sourceId: "site",
      targetId: "gadget",
      createCategoryIfMissing: false,
    });
    expect(result.ok).toBe(false);
  });
});

describe("position persistence shape", () => {
  it("reads the stored position by ref and reports none otherwise", () => {
    const document = clone();
    expect(positionOf(document, "component:site")).toEqual({ x: 120, y: 80 });
    expect(positionOf(document, "component:unit")).toBeNull();
  });

  it("writes a point under views.topology[ref] without mutating the source", () => {
    const document = clone();
    const next = withPosition(document, "component:unit", { x: 33.333, y: 44 });
    expect(next.views?.topology?.["component:unit"]).toEqual({ x: 33.33, y: 44 });
    expect(document.views?.topology?.["component:unit"]).toBeUndefined();
  });

  it("offers a point that no placed component already occupies", () => {
    const document = clone();
    const point = freePosition(document);
    const taken = Object.values(document.views?.topology ?? {});
    for (const existing of taken) {
      expect(Math.abs(point.x - existing.x) >= 200 || Math.abs(point.y - existing.y) >= 130).toBe(
        true,
      );
    }
  });

  it("is deterministic for the same document", () => {
    expect(freePosition(clone())).toEqual(freePosition(clone()));
  });

  it("steps around every drawn vertex, edge cards included", () => {
    // A document in which nothing is left to the fallback grid: every component, node or
    // edge, has a stored position, so the free point has to clear all of them.
    const document = buildGraph(clone(), DEFAULT_FILTERS).vertices.reduce(
      (acc, vertex, index) =>
        withPosition(acc, vertex.ref, { x: 80 + (index % 3) * 240, y: 80 + Math.floor(index / 3) * 200 }),
      clone(),
    );
    const point = freePosition(document);
    for (const vertex of buildGraph(document, DEFAULT_FILTERS).vertices) {
      const taken = positionOf(document, vertex.ref) as Point;
      expect(Math.abs(point.x - taken.x) >= 200 || Math.abs(point.y - taken.y) >= 130).toBe(true);
    }
  });
});

describe("withPositions — writing a layout in one pass", () => {
  it("writes one ref per id, rounded like withPosition and without mutating the source", () => {
    const document = clone();
    const next = withPositions(document, {
      site: { x: 12.345, y: 8 },
      unit: { x: 0, y: -4 },
    });
    expect(next.views?.topology?.["component:site"]).toEqual({ x: 12.35, y: 8 });
    expect(next.views?.topology?.["component:unit"]).toEqual({ x: 0, y: -4 });
    expect(document.views?.topology).toEqual({ "component:site": { x: 120, y: 80 } });
  });

  it("accepts a ref where a caller holds one instead of an id", () => {
    const next = withPositions(clone(), { "component:unit": { x: 8, y: 16 } });
    expect(next.views?.topology?.["component:unit"]).toEqual({ x: 8, y: 16 });
  });

  it("ignores an id that resolves to no vertex rather than writing a junk ref", () => {
    const next = withPositions(clone(), {
      gone: { x: 1, y: 1 },
      site: { x: 2, y: 2 },
      "binding:site_binding": { x: 3, y: 3 },
    });
    expect(next.views?.topology?.["component:gone"]).toBeUndefined();
    expect(next.views?.topology?.["component:site_binding"]).toBeUndefined();
    expect(next.views?.topology?.["component:site"]).toEqual({ x: 2, y: 2 });
  });

  it("writes nothing for a document with no resolvable id", () => {
    const document = clone();
    expect(withPositions(document, { nope: { x: 1, y: 1 } })).toBe(document);
  });

  it("keys a layout reported in vertex ids under each vertex's ref, edge cards included", () => {
    // A layout — `autoLayout`, or the force settle it seeds — answers in vertex ids, while
    // `views.topology` is keyed by ref. Every writer of a whole canvas would have to bridge
    // that itself otherwise, so it is bridged here once.
    const document = metaGraphDocument();
    const graph = buildGraph(document, DEFAULT_FILTERS);
    const placed = autoLayout(graph.vertices, graph.links);
    const next = withPositions(document, placed);
    expect(Object.keys(next.views?.topology ?? {}).sort()).toEqual(
      graph.vertices.map((vertex) => vertex.ref).sort(),
    );
    expect(next.views?.topology?.["component:studied_in"]).toBeDefined();
    expect(next.views?.topology?.["component:studied_in"]).toEqual(placed["studied_in"]);
    // A layout is a view, not a model edit, and the document handed over is untouched.
    expect(next.components).toEqual(document.components);
    expect(document.views?.topology).toEqual({});
  });
});

describe("autoLayout — x carries the metagraph", () => {
  it("places a concrete edge card horizontally between the nodes it joins", () => {
    const vertices = [card("site"), card("has_unit", "edge"), card("unit")];
    const links = [leg("a", "site", "has_unit"), leg("b", "has_unit", "unit")];
    const placed = autoLayout(vertices, links);
    expect(xOf(placed, "site")).toBeLessThan(xOf(placed, "has_unit"));
    expect(xOf(placed, "has_unit")).toBeLessThan(xOf(placed, "unit"));
  });

  it("lays the demo-shaped metagraph out in the columns the metagraph reads as", () => {
    const graph = buildGraph(metaGraphDocument(), DEFAULT_FILTERS);
    const placed = autoLayout(graph.vertices, graph.links);
    // Deriving the table from the rule by hand: `documented` is the root of the is-a tree and
    // of the category's `in` leg, so column 0; `target`/`publication` inherit it and
    // `related` joins it, so column 1; the two concrete cards each sit one right of their
    // source, so column 2; `pathway` is only reachable through `studied_in`, so column 3.
    expect(columns(graph, placed)).toEqual([
      ["documented"],
      ["publication", "related", "target"],
      ["reported_for", "studied_in"],
      ["pathway"],
    ]);
  });

  it("sits an edge category one column right of the nodes it joins", () => {
    const graph = buildGraph(metaGraphDocument(), DEFAULT_FILTERS);
    const placed = autoLayout(graph.vertices, graph.links);
    // Not the trailing column: its `in` leg anchors it.
    expect(xOf(placed, "documented")).toBeLessThan(xOf(placed, "related"));
    expect(xOf(placed, "related")).toBeLessThan(xOf(placed, "studied_in"));
    // Its `out` leg (related → documented) points back at column 0, which is allowed of a
    // declaration and is the whole reason the out leg is not a constraint.
    expect(xOf(placed, "related")).toBeGreaterThan(xOf(placed, "documented"));
  });

  it("never lets a category leg push the endpoint it names", () => {
    // `cat` declares a → b; the concrete `first` runs b → a. The category may place itself
    // (one column right of its deepest endpoint), but it must not move an endpoint: were the
    // out leg a constraint, `b` would be pushed right of `cat` and the flow would fold back
    // on itself. What the contradiction costs instead is one leftward declaration arrow.
    const graph = buildGraph(declaredAgainstFlowDocument(), DEFAULT_FILTERS);
    const placed = autoLayout(graph.vertices, graph.links);
    expect(xOf(placed, "b")).toBeLessThan(xOf(placed, "first"));
    expect(xOf(placed, "first")).toBeLessThan(xOf(placed, "a"));
    expect(xOf(placed, "a")).toBeLessThan(xOf(placed, "cat"));
    expect(xOf(placed, "b")).toBeLessThan(xOf(placed, "cat"));
    expect(leftward(graph, placed, "hierarchy")).toEqual([]);
    expect(leftward(graph, placed, "relation")).toEqual([]);
    expect(leftward(graph, placed, "category")).toEqual(["link:cat:out"]);
  });

  it("walks a chain rightwards, alternating node and edge columns", () => {
    const graph = buildGraph(chainDocument(), DEFAULT_FILTERS);
    const placed = autoLayout(graph.vertices, graph.links);
    for (const [from, to] of [
      ["a", "first"],
      ["first", "b"],
      ["b", "second"],
      ["second", "c"],
    ] as const) {
      expect(xOf(placed, from)).toBeLessThan(xOf(placed, to));
    }
  });

  it("lays the demo-shaped metagraph out with each edge card between its endpoints", () => {
    const graph = buildGraph(metaGraphDocument(), DEFAULT_FILTERS);
    const placed = autoLayout(graph.vertices, graph.links);
    expect(xOf(placed, "target")).toBeLessThan(xOf(placed, "studied_in"));
    expect(xOf(placed, "studied_in")).toBeLessThan(xOf(placed, "pathway"));
    expect(xOf(placed, "publication")).toBeLessThan(xOf(placed, "reported_for"));
    // Two edge cards of one category share a column, so `related` reads as their parent.
    expect(xOf(placed, "studied_in")).toBe(xOf(placed, "reported_for"));
    // `documented` is the category the three node cards descend from, so it opens the
    // graph rather than sitting to the right of the card that points at it.
    expect(xOf(placed, "documented")).toBeLessThan(xOf(placed, "publication"));
    expect(xOf(placed, "related")).toBeLessThan(xOf(placed, "studied_in"));
  });

  it("never lets an is-a arrow point leftwards", () => {
    for (const document of [clone(), metaGraphDocument(), chainDocument(), cyclicCategoryDocument()]) {
      const graph = buildGraph(document, DEFAULT_FILTERS);
      const placed = autoLayout(graph.vertices, graph.links);
      const backwards = graph.links
        .filter((link) => link.kind === "hierarchy" && xOf(placed, link.source) > xOf(placed, link.target))
        .map((link) => link.id);
      expect(backwards).toEqual([]);
    }
  });

  it("keeps the flow reading left to right when the flow and the hierarchy agree", () => {
    for (const document of [clone(), chainDocument()]) {
      const graph = buildGraph(document, DEFAULT_FILTERS);
      const placed = autoLayout(graph.vertices, graph.links);
      expect(leftward(graph, placed, "relation")).toEqual([]);
      expect(leftward(graph, placed, "hierarchy")).toEqual([]);
    }
  });

  it("draws the legs that fight the hierarchy instead of hiding them", () => {
    // The demo declares `publication is-a documented` and `reported_for: publication →
    // documented` together, so no columning can put reported_for right of publication AND
    // documented right of reported_for AND documented left of publication. The is-a wins and
    // that single out-leg doubles back — the same arrow `meta_graph.json` draws, where
    // documented sits at depth 0 and reported_for at depth 1. It must be exactly one link,
    // or the layout has stopped honouring the constraint set rather than meeting a cycle.
    const graph = buildGraph(metaGraphDocument(), DEFAULT_FILTERS);
    const placed = autoLayout(graph.vertices, graph.links);
    expect(leftward(graph, placed, "relation")).toEqual(["link:reported_for:out"]);
    expect(leftward(graph, placed, "hierarchy")).toEqual([]);
    // `related` declares documented → documented, so there is no "between" for it to sit in:
    // its in leg pulls the card one column right of the category, and its out leg — never a
    // constraint, by design — is the arrow that points back at column 0.
    expect(leftward(graph, placed, "category")).toEqual(["link:related:out"]);
  });

  it("gives up the declaration before the flow when a cycle offers both", () => {
    // Same document: the category's `in` leg survives the cycle because dropping the shared
    // `reported_for` leg untangles two loops at once, so one leftward arrow suffices. If the
    // declaration had been the one sacrificed, `related` would be back in column 0 beside the
    // node it joins — the reading this rule exists to prevent.
    const graph = buildGraph(metaGraphDocument(), DEFAULT_FILTERS);
    const placed = autoLayout(graph.vertices, graph.links);
    expect(xOf(placed, "documented")).toBeLessThan(xOf(placed, "related"));
    expect(columns(graph, placed)[0]).toEqual(["documented"]);
  });

  it("lets only a cyclic declaration arrow leftwards", () => {
    // `cat` declares a→b while `uses`, which inherits it, runs b→a. The is-a step and the
    // flow are both satisfiable; what cannot be is the category's own legs, so that is the
    // arrow that points back, and it is a real cycle in what the document declares.
    const graph = buildGraph(cyclicCategoryDocument(), DEFAULT_FILTERS);
    const placed = autoLayout(graph.vertices, graph.links);
    expect(leftward(graph, placed, "hierarchy")).toEqual([]);
    expect(leftward(graph, placed, "relation")).toEqual([]);
    expect(leftward(graph, placed, "category")).toEqual(["link:cat:in"]);
  });

  it("places every card without an overlap and with the gutters it is owed", () => {
    const graph = buildGraph(metaGraphDocument(), DEFAULT_FILTERS);
    // Deliberately not the sizes the cards default to: the layout must honour the
    // measurement it is handed, and an edge card wider than the nodes it joins is the
    // case a hand-written grid gets wrong.
    const sizes = (vertex: VertexView): VertexSize => (vertex.shape === "edge" ? EDGE : NODE);
    const placed = autoLayout(graph.vertices, graph.links, sizes);
    const spread = gaps(graph.vertices, placed, sizes);
    expect(spread.tightestX).toBeGreaterThanOrEqual(40);
    expect(spread.tightestY).toBeGreaterThanOrEqual(32);
  });

  it("separates the boxes it was measured at, not the boxes it guessed", () => {
    const graph = buildGraph(metaGraphDocument(), DEFAULT_FILTERS);
    const placed = autoLayout(graph.vertices, graph.links);
    const boxes = graph.vertices.map((vertex) => {
      const point = placed[vertex.id] as Point;
      const size = vertex.shape === "edge" ? DEFAULT_EDGE_SIZE : DEFAULT_NODE_SIZE;
      return { id: vertex.id, left: point.x, right: point.x + size.width, top: point.y, bottom: point.y + size.height };
    });
    for (const [index, a] of boxes.entries()) {
      for (const b of boxes.slice(index + 1)) {
        const overlaps = a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
        expect(`${a.id}/${b.id} overlapping: ${overlaps}`).toBe(`${a.id}/${b.id} overlapping: false`);
      }
    }
  });

  it("snaps every coordinate onto a non-negative grid", () => {
    const graph = buildGraph(metaGraphDocument(), DEFAULT_FILTERS);
    const placed = autoLayout(graph.vertices, graph.links, () => ({ width: 217, height: 61 }));
    for (const point of Object.values(placed)) {
      expect(Number.isFinite(point.x) && Number.isFinite(point.y)).toBe(true);
      expect(point.x).toBeGreaterThanOrEqual(0);
      expect(point.x % 4).toBe(0);
      expect(point.y).toBeGreaterThanOrEqual(0);
      expect(point.y % 4).toBe(0);
    }
  });

  it("is deterministic: the same graph handed over in any order lays out the same way", () => {
    // Including a graph whose cycle has to be broken by hand — which constraint gets cut is
    // the part of the layout most likely to lean on input order.
    for (const document of [metaGraphDocument(), cyclicCategoryDocument(), clone()]) {
      const graph = buildGraph(document, DEFAULT_FILTERS);
      const once = autoLayout(graph.vertices, graph.links);
      for (const permutation of permutations(graph.vertices.length, graph.links.length)) {
        const shuffled = autoLayout(
          permute(graph.vertices, permutation.vertices),
          permute(graph.links, permutation.links),
        );
        expect(shuffled).toEqual(once);
      }
    }
  });

  it("survives an empty graph, a single card and a nonsense measurement", () => {
    expect(autoLayout([], [])).toEqual({});
    const alone = autoLayout([card("site")], []);
    expect(alone["site"]).toEqual({ x: 0, y: 0 });
    const measured = autoLayout([card("site"), card("has_unit", "edge")], [], () => ({
      width: Number.NaN,
      height: -40,
    }));
    expect(Object.values(measured).every((point) => Number.isFinite(point.x) && Number.isFinite(point.y))).toBe(
      true,
    );
    // Links to a vertex that is not drawn are ignored rather than laid out.
    const ignoring = autoLayout([card("site")], [leg("a", "site", "ghost")]);
    expect(Object.keys(ignoring)).toEqual(["site"]);
  });

  it("stacks a column of cards that no leg reaches", () => {
    const vertices = [card("first"), card("second"), card("third")];
    const placed = autoLayout(vertices, []);
    expect(xOf(placed, "first")).toBe(xOf(placed, "second"));
    expect(xOf(placed, "second")).toBe(xOf(placed, "third"));
    expect(yOf(placed, "first")).toBeLessThan(yOf(placed, "second"));
    expect(yOf(placed, "second")).toBeLessThan(yOf(placed, "third"));
  });

  it("still gives a card with neither endpoints nor parent a place of its own", () => {
    // The residual column is the last resort, and the only thing that reaches it now is a
    // component nothing constrains: `lonely` has no parent, no endpoints and nothing under
    // it, so no rule says where it goes — but it is still drawn, so it still gets a spot.
    const graph = buildGraph(lonelyCategoryDocument(), DEFAULT_FILTERS);
    const placed = autoLayout(graph.vertices, graph.links);
    const laid = columns(graph, placed);
    expect(laid[laid.length - 1]).toEqual(["lonely"]);
    expect(placed["lonely"]).toBeDefined();
    expect(Number.isFinite(xOf(placed, "lonely") as number)).toBe(true);
  });
});

describe("prunePositions — forgetting places nothing can be drawn at", () => {
  it("drops template refs and refs whose component no longer exists", () => {
    const next = prunePositions(stalePositionsDocument());
    const kept = Object.keys(next.views?.topology ?? {}).sort();
    expect(kept).toEqual(["component:target"]);
  });

  it("keeps the position of a component that only the filters hide", () => {
    // The whole point: toggling `showCategories` off and on again must not cost the user the
    // place they dragged a category to, so the decision comes from the document, not from
    // the filtered graph the canvas happens to be drawing.
    const document = withPosition(metaGraphDocument(), "component:related", { x: 640, y: 320 });
    const graph = buildGraph(document, { ...DEFAULT_FILTERS, showCategories: false });
    expect(graph.vertices.some((vertex) => vertex.id === "related")).toBe(false);
    const next = prunePositions(document);
    expect(next.views?.topology?.["component:related"]).toEqual({ x: 640, y: 320 });
  });

  it("keeps every drawn ref and mutates nothing else about the document", () => {
    const document = stalePositionsDocument();
    const next = prunePositions(document);
    expect(next.views?.topology?.["component:target"]).toEqual({ x: 240, y: 40 });
    // The source is untouched, and every section other than the view is identical.
    expect(document.views?.topology?.["component:provenanced_node"]).toEqual({ x: 40, y: 40 });
    expect({ ...next, views: undefined }).toEqual({ ...document, views: undefined });
  });

  it("returns the same document when there is nothing to drop", () => {
    const document = withPosition(metaGraphDocument(), "component:target", { x: 1, y: 2 });
    expect(prunePositions(document)).toBe(document);
  });

  it("leaves exactly the refs the canvas draws, once a whole-canvas layout has been written", () => {
    // The reset gesture, in the two steps the canvas actually performs: write a settled
    // position for every drawn vertex, then forget the positions that can never be drawn
    // again. What survives is precisely the canvas's own view — and the model is untouched,
    // because a layout is a view.
    const document = stalePositionsDocument();
    const graph = buildGraph(document, DEFAULT_FILTERS);
    const placed = Object.fromEntries(graph.vertices.map((vertex) => [vertex.ref, vertex.position]));
    const once = prunePositions(withPositions(document, placed));
    expect(Object.keys(once.views?.topology ?? {}).sort()).toEqual(
      graph.vertices.map((vertex) => vertex.ref).sort(),
    );
    expect(once.components).toEqual(document.components);
    // Nothing is left to drop, so a second pass cannot change the document at all — which is
    // what makes rewriting the whole view safe to do more than once.
    expect(prunePositions(once)).toBe(once);
  });
});

describe("slot optionality rule", () => {
  it("allows optional only for nullable types", () => {
    expect(slotAllowsOptional(nullable(unit("str")))).toBe(true);
    expect(slotAllowsOptional(nullable(array(nullable(unit("int")))))).toBe(true);
    expect(slotAllowsOptional(unit("str"))).toBe(false);
    expect(slotAllowsOptional(null)).toBe(false);
  });

  it("drops the optional flag when the type stops being nullable", () => {
    const optionalSlot = { ...emptySlot("note"), optional: true };
    expect(normalizeSlot(optionalSlot).optional).toBe(true);
    const downgraded = setSlotType(optionalSlot, unit("str"));
    expect(downgraded.optional).toBe(false);
  });

  it("refuses to set optional on a non-nullable slot", () => {
    const required = { ...emptySlot("code"), logical_type: unit("str") };
    expect(setSlotOptional(required, true)).toBe(required);
  });
});

describe("deleteImpact — dangling bindings and cascade repair", () => {
  it("finds the bindings that dangle when a bound node is deleted", () => {
    const impact = deleteImpact(clone(), "site");
    expect(impact.dangling).toBe(true);
    expect(impact.bindings.map((b) => b.id)).toContain("site_binding");
  });

  it("flags a category with children/mixins", () => {
    const impact = deleteImpact(clone(), "documented");
    expect(impact.children.map((c) => c.id)).toContain("site");
    expect(impact.dangling).toBe(true);
  });

  it("reports nothing dangling for an unbound, unreferenced component", () => {
    const document = withComponents(clone(), [component("lonely", "node", "category")]);
    expect(deleteImpact(document, "lonely").dangling).toBe(false);
  });

  it("removes the component, its bindings, and repairs references", () => {
    const next = removeComponentCascade(clone(), "site");
    expect((next.components ?? []).some((c) => c.id === "site")).toBe(false);
    expect((next.bindings ?? []).some((b) => b.component === "site")).toBe(false);
    // Edges that pointed at site now point at site's category parent, never at a hole.
    const hasUnit = (next.components ?? []).find((c) => c.id === "has_unit");
    expect(hasUnit?.source).not.toBe("site");
    expect(next.views?.topology?.["component:site"]).toBeUndefined();
  });
});

describe("buildGraph — the metagraph", () => {
  it("draws every visible component as a vertex, edge components included", () => {
    const graph = buildGraph(clone(), DEFAULT_FILTERS);
    const byId = new Map(graph.vertices.map((v) => [v.id, v]));
    expect(byId.has("site")).toBe(true);
    expect(byId.has("documented")).toBe(true);
    // A concrete edge is a card of its own now, so its own is-a can be drawn.
    expect(byId.get("has_unit")?.shape).toBe("edge");
    expect(byId.get("monitored_relation")?.shape).toBe("edge");
    expect(byId.get("site")?.shape).toBe("node");
    expect(byId.get("has_unit")?.endpoints).toEqual({ source: "site", target: "unit" });
    expect(byId.get("site")?.endpoints).toEqual({ source: null, target: null });
    expect(byId.get("site")?.ref).toBe("component:site");
  });

  it("draws the framework's metagraph, not the whole document", () => {
    // `meta_graph.json` for the demo project is those four nodes and three edges and
    // nothing else: a mix-in template never reaches the blueprint, so it is not a vertex.
    const graph = buildGraph(metaGraphDocument(), DEFAULT_FILTERS);
    expect(graph.vertices.map((vertex) => vertex.id).sort()).toEqual([
      "documented",
      "pathway",
      "publication",
      "related",
      "reported_for",
      "studied_in",
      "target",
    ]);
  });

  it("joins an edge card to its endpoints with two legs, labelled on the out leg only", () => {
    const graph = buildGraph(clone(), DEFAULT_FILTERS);
    const legs = graph.links.filter((link) => link.id.startsWith("link:has_unit"));
    expect(legs.map((link) => link.id)).toEqual(["link:has_unit:in", "link:has_unit:out"]);
    const [inLeg, outLeg] = legs as [LinkView, LinkView];
    expect(inLeg).toMatchObject({
      source: "site",
      target: "has_unit",
      kind: "relation",
      role: "in",
      label: "",
      ref: "component:has_unit",
    });
    expect(outLeg).toMatchObject({
      source: "has_unit",
      target: "unit",
      kind: "relation",
      role: "out",
      label: "HAS_UNIT",
      ref: "component:has_unit",
    });
    // The predicate is written once per relation, not twice along one polyline.
    expect(graph.links.filter((link) => link.label === "HAS_UNIT")).toHaveLength(1);
    // A category edge draws the same two legs in the category colour.
    const categoryLegs = graph.links.filter((link) => link.id.startsWith("link:monitored_relation"));
    expect(categoryLegs.map((link) => link.kind)).toEqual(["category", "category"]);
    expect(categoryLegs.map((link) => link.role)).toEqual(["in", "out"]);
  });

  it("adds an is-a hierarchy link for a parent, and nothing for a mix-in", () => {
    const graph = buildGraph(clone(), DEFAULT_FILTERS);
    expect(graph.links.find((l) => l.id === "hier:site:parent")).toMatchObject({
      source: "documented",
      target: "site",
      kind: "hierarchy",
      role: "parent",
      label: "is-a",
      ref: "component:site",
    });
    // `site` mixes `provenanced_node`; a template is not a vertex, so there is no card for
    // that fact to run between and the library carries it instead.
    expect(graph.links.filter((link) => link.id.includes(":mixin:"))).toEqual([]);
    expect(graph.links.filter((link) => link.label === "mixes")).toEqual([]);
    expect(graph.vertices.some((vertex) => vertex.id === "provenanced_node")).toBe(false);
  });

  it("draws the is-a of an edge component, which a line could not carry", () => {
    const graph = buildGraph(metaGraphDocument(), DEFAULT_FILTERS);
    const parent = graph.links.find((link) => link.id === "hier:studied_in:parent");
    expect(parent).toMatchObject({
      source: "related",
      target: "studied_in",
      kind: "hierarchy",
      role: "parent",
      label: "is-a",
      ref: "component:studied_in",
    });
    expect(graph.links.find((link) => link.id === "hier:reported_for:parent")).toMatchObject({
      source: "related",
      target: "reported_for",
      label: "is-a",
    });
    // The edge template those two mix in is not a vertex, so it links to nothing here;
    // `templateCatalogue` is where that relationship is reported.
    expect(graph.vertices.some((vertex) => vertex.id === "recorded_edge")).toBe(false);
    // A category edge over two endpoints of its own still gets its legs.
    expect(graph.links.filter((link) => link.id.startsWith("link:related:"))).toHaveLength(2);
  });

  it("never draws a link from a vertex to itself", () => {
    for (const document of [clone(), metaGraphDocument(), selfNamingEdgeDocument()]) {
      const graph = buildGraph(document, DEFAULT_FILTERS);
      expect(graph.links.filter((link) => link.source === link.target)).toEqual([]);
    }
    // A category over one category pair is two distinct legs, node→card and card→node.
    const graph = buildGraph(metaGraphDocument(), DEFAULT_FILTERS);
    expect(
      graph.links
        .filter((link) => link.id.startsWith("link:related"))
        .map((link) => `${link.source}>${link.target}`),
    ).toEqual(["documented>related", "related>documented"]);
    // A card naming itself as its own endpoint has nothing to join to and says so quietly.
    const self = buildGraph(selfNamingEdgeDocument(), DEFAULT_FILTERS);
    expect(self.vertices.some((vertex) => vertex.id === "loop")).toBe(true);
    expect(self.links.filter((link) => link.source === "loop" || link.target === "loop")).toEqual([]);
  });

  it("keeps every vertex id and link id unique", () => {
    for (const document of [clone(), metaGraphDocument(), duplicatedComponentDocument()]) {
      const graph = buildGraph(document, DEFAULT_FILTERS);
      const vertexIds = graph.vertices.map((vertex) => vertex.id);
      const linkIds = graph.links.map((link) => link.id);
      expect(new Set(vertexIds).size).toBe(vertexIds.length);
      expect(new Set(linkIds).size).toBe(linkIds.length);
    }
  });

  it("keeps a card whose endpoint dangles, with no legs", () => {
    const document = withComponents(clone(), [
      { ...component("nowhere", "edge", "concrete"), label: "NOWHERE", source: "site", target: "gone" },
    ]);
    const graph = buildGraph(document, DEFAULT_FILTERS);
    const card = graph.vertices.find((vertex) => vertex.id === "nowhere");
    expect(card?.shape).toBe("edge");
    expect(card?.endpoints).toEqual({ source: "site", target: "gone" });
    expect(graph.refsById["nowhere"]).toBe("component:nowhere");
    expect(legsOf(graph, "nowhere")).toEqual([]);
  });

  it("keeps a card whose endpoint the filters hide, with no legs", () => {
    const graph = buildGraph(metaGraphDocument(), { ...DEFAULT_FILTERS, showCategories: false });
    const card = graph.vertices.find((vertex) => vertex.id === "reported_for");
    // `documented` is a category, so it is off-canvas and this card cannot be joined.
    expect(card?.shape).toBe("edge");
    expect(legsOf(graph, "reported_for")).toEqual([]);
    // Its is-a went with the hidden parent; nothing else reached that card either.
    expect(graph.links.some((link) => link.id === "hier:reported_for:parent")).toBe(false);
    expect(graph.links.filter((link) => link.source === "reported_for" || link.target === "reported_for")).toEqual([]);
    // `studied_in` joins two concrete nodes, so both of its legs survive.
    expect(legsOf(graph, "studied_in")).toHaveLength(2);
  });

  it("gates edge cards by the same filters as every other component", () => {
    const all = buildGraph(metaGraphDocument(), DEFAULT_FILTERS);
    expect(all.vertices.some((vertex) => vertex.id === "related")).toBe(true);

    const noCategories = buildGraph(metaGraphDocument(), { ...DEFAULT_FILTERS, showCategories: false });
    expect(noCategories.vertices.some((vertex) => vertex.id === "related")).toBe(false);
    expect(noCategories.vertices.some((vertex) => vertex.id === "documented")).toBe(false);
    expect(noCategories.links.some((link) => link.ref === "component:related")).toBe(false);
    expect(noCategories.links.some((link) => link.kind === "category")).toBe(false);
  });

  it("never draws a template, whatever the filters say", () => {
    // There is deliberately no `showTemplates` filter: hiding a tier you should never have
    // drawn is how a mix-in ended up floating in the middle of the graph.
    expect(Object.keys(DEFAULT_FILTERS).sort()).toEqual(["showCategories", "showHierarchy"]);
    for (const filters of [
      DEFAULT_FILTERS,
      { showCategories: true, showHierarchy: false },
      { showCategories: false, showHierarchy: true },
      { showCategories: false, showHierarchy: false },
    ]) {
      const graph = buildGraph(metaGraphDocument(), filters);
      expect(graph.vertices.some((vertex) => vertex.component.tier === "template")).toBe(false);
    }
  });

  it("keeps a hidden category revealable but never a template", () => {
    const graph = buildGraph(metaGraphDocument(), { ...DEFAULT_FILTERS, showCategories: false });
    // A category that is merely filtered out can still be jumped to; `reveal` finds it a
    // position through the document rather than a vertex that does not exist.
    expect(graph.refsById["related"]).toBe("component:related");
    // A template has no vertex to centre, so the canvas must be able to say "not here".
    expect(graph.refsById["provenanced_node"]).toBeUndefined();
    expect(graph.refsById["recorded_edge"]).toBeUndefined();
    // Drawn vertices are always in the index.
    for (const vertex of graph.vertices) expect(graph.refsById[vertex.id]).toBe(vertex.ref);
  });

  it("drops hierarchy links without touching the legs", () => {
    const graph = buildGraph(metaGraphDocument(), { ...DEFAULT_FILTERS, showHierarchy: false });
    expect(graph.links.some((link) => link.kind === "hierarchy")).toBe(false);
    expect(graph.links.filter((link) => link.id.startsWith("link:studied_in:"))).toHaveLength(2);
  });
});

describe("templateCatalogue — the surface templates get instead of a vertex", () => {
  it("lists every template with the components that mix it in, in document order", () => {
    const catalogue = templateCatalogue(metaGraphDocument());
    expect(catalogue.map((entry) => entry.component.id)).toEqual(["provenanced_node", "recorded_edge"]);
    expect(catalogue[0]?.users.map((user) => user.id)).toEqual(["target", "pathway", "publication"]);
    expect(catalogue[1]?.users.map((user) => user.id)).toEqual(["studied_in", "reported_for"]);
  });

  it("reports the slots a template contributes", () => {
    const document = withComponents(clone(), [
      { ...component("audited", "node", "template"), properties: [emptySlot("reviewed_by"), emptySlot("reviewed_at")] },
    ]);
    const entry = templateCatalogue(document).find((item) => item.component.id === "audited");
    expect(entry?.slotNames).toEqual(["reviewed_by", "reviewed_at"]);
    expect(entry?.users).toEqual([]);
  });

  it("surfaces a template mixed into nothing — that is the point of the list", () => {
    const document = withComponents(clone(), [component("orphan", "edge", "template")]);
    const entry = templateCatalogue(document).find((item) => item.component.id === "orphan");
    expect(entry?.users).toEqual([]);
    expect(entry?.slotNames).toEqual([]);
    // And it is nowhere on the canvas.
    expect(buildGraph(document, DEFAULT_FILTERS).vertices.some((v) => v.id === "orphan")).toBe(false);
  });

  it("orders node templates before edge templates, and each by id", () => {
    const document = withComponents(clone(), [
      component("zeta_node", "node", "template"),
      component("alpha_node", "node", "template"),
      component("zeta_edge", "edge", "template"),
      component("alpha_edge", "edge", "template"),
    ]);
    expect(templateCatalogue(document).map((entry) => entry.component.id)).toEqual([
      "alpha_node",
      "provenanced_node",
      "zeta_node",
      "alpha_edge",
      "zeta_edge",
    ]);
  });

  it("counts a template's users once even when a component lists it twice", () => {
    const document = withComponents(clone(), [
      component("audited", "node", "template"),
      { ...component("dossier", "node", "concrete"), mixins: ["audited", "audited"] },
    ]);
    const entry = templateCatalogue(document).find((item) => item.component.id === "audited");
    expect(entry?.users.map((user) => user.id)).toEqual(["dossier"]);
  });

  it("leaves non-templates out entirely", () => {
    const ids = templateCatalogue(metaGraphDocument()).map((entry) => entry.component.id);
    expect(ids).not.toContain("documented");
    expect(ids).not.toContain("related");
    expect(ids).not.toContain("studied_in");
  });
});

describe("vertexShape — what a component is drawn as", () => {
  it("makes every edge kind an edge card, at every tier", () => {
    expect(vertexShape(component("site", "node", "concrete"))).toBe("node");
    expect(vertexShape(component("documented", "node", "category"))).toBe("node");
    expect(vertexShape(component("audited", "edge", "template"))).toBe("edge");
    expect(vertexShape(component("related", "edge", "category"))).toBe("edge");
    expect(vertexShape(component("has_unit", "edge", "concrete"))).toBe("edge");
  });
});

function component(id: string, kind: "node" | "edge", tier: "template" | "category" | "concrete"): Component {
  return {
    id,
    kind,
    tier,
    declaration_name: id,
    name: id,
    description: null,
    label: null,
    parent: null,
    mixins: [],
    source: null,
    target: null,
    properties: [],
    annotations: [],
  };
}

/** A document shaped like the demo project: a `related` category edge over
 *  documented→documented, with `studied_in` (target→pathway) and `reported_for`
 *  (publication→documented) beneath it and `recorded_edge` mixed into both. Every one of
 *  those is-a / mixes declarations used to be dropped for want of a card to draw it on. */
function metaGraphDocument(): ProjectDocument {
  return {
    ...clone(),
    components: [
      { ...component("documented", "node", "category"), label: "Documented" },
      component("provenanced_node", "node", "template"),
      component("recorded_edge", "edge", "template"),
      {
        ...component("target", "node", "concrete"),
        label: "Target",
        parent: "documented",
        mixins: ["provenanced_node"],
      },
      {
        ...component("pathway", "node", "concrete"),
        label: "Pathway",
        parent: "documented",
        mixins: ["provenanced_node"],
      },
      {
        ...component("publication", "node", "concrete"),
        label: "Publication",
        parent: "documented",
        mixins: ["provenanced_node"],
      },
      {
        ...component("related", "edge", "category"),
        label: "RELATED",
        source: "documented",
        target: "documented",
      },
      {
        ...component("studied_in", "edge", "concrete"),
        label: "STUDIED_IN",
        parent: "related",
        mixins: ["recorded_edge"],
        source: "target",
        target: "pathway",
      },
      {
        ...component("reported_for", "edge", "concrete"),
        label: "REPORTED_FOR",
        parent: "related",
        mixins: ["recorded_edge"],
        source: "publication",
        target: "documented",
      },
    ],
    bindings: [],
    views: { topology: {} },
  };
}

/** Three nodes joined by two edge cards — the chain whose x ordering the layout owes. */
function chainDocument(): ProjectDocument {
  return {
    ...clone(),
    components: [
      component("a", "node", "concrete"),
      component("b", "node", "concrete"),
      component("c", "node", "concrete"),
      { ...component("first", "edge", "concrete"), label: "FIRST", source: "a", target: "b" },
      { ...component("second", "edge", "concrete"), label: "SECOND", source: "b", target: "c" },
    ],
    bindings: [],
    views: { topology: {} },
  };
}

/** A category that declares `a → b` while the concrete edge inheriting it runs `b → a`:
 *  the is-a step and the flow are both satisfiable, the category's own legs are not. */
function cyclicCategoryDocument(): ProjectDocument {
  return {
    ...clone(),
    components: [
      component("a", "node", "concrete"),
      component("b", "node", "concrete"),
      { ...component("cat", "edge", "category"), label: "CAT", source: "a", target: "b" },
      { ...component("uses", "edge", "concrete"), label: "USES", parent: "cat", source: "b", target: "a" },
    ],
    bindings: [],
    views: { topology: {} },
  };
}

/** An edge naming itself as both of its endpoints: a card, but nothing joinable. */
function selfNamingEdgeDocument(): ProjectDocument {
  return withComponents(metaGraphDocument(), [
    { ...component("loop", "edge", "concrete"), label: "LOOP", source: "loop", target: "loop" },
  ]);
}

/** The sample with the same component declared twice — a payload the canvas must not
 *  answer to by drawing one id twice or emitting a link id twice. */
function duplicatedComponentDocument(): ProjectDocument {
  const document = clone();
  const components = [...(document.components ?? [])];
  const first = components[0] as Component;
  return { ...document, components: [...components, first, { ...first }] };
}

/** A category declaring `a → b` against a concrete edge running `b → a`, with nothing in
 *  the way of a hierarchy between them. */
function declaredAgainstFlowDocument(): ProjectDocument {
  return {
    ...clone(),
    components: [
      component("a", "node", "concrete"),
      component("b", "node", "concrete"),
      { ...component("cat", "edge", "category"), label: "CAT", source: "a", target: "b" },
      { ...component("first", "edge", "concrete"), label: "FIRST", source: "b", target: "a" },
    ],
    bindings: [],
    views: { topology: {} },
  };
}

/** A category node with no parent, no endpoints and nothing under it — the one shape the
 *  column constraints have nothing to say about. */
function lonelyCategoryDocument(): ProjectDocument {
  return withComponents(metaGraphDocument(), [component("lonely", "node", "category")]);
}

/** The metagraph with positions this file cannot account for: a template that left the
 *  graph, a component deleted elsewhere, and a part-qualified ref the canvas never writes. */
function stalePositionsDocument(): ProjectDocument {
  const document = metaGraphDocument();
  return {
    ...document,
    views: {
      topology: {
        "component:provenanced_node": { x: 40, y: 40 },
        "component:recorded_edge": { x: 80, y: 40 },
        "component:deleted_long_ago": { x: 120, y: 40 },
        "component:studied_in.property.recorded_in": { x: 160, y: 40 },
        "binding:orphan_binding": { x: 200, y: 40 },
        "component:target": { x: 240, y: 40 },
      },
    },
  };
}

/* ------------------------------------------------------------------- layout fixtures */

const NODE: VertexSize = { width: 180, height: 90 };
const EDGE: VertexSize = { width: 300, height: 120 };

/** A vertex the layout can be pointed at on its own, without a document behind it. */
function card(id: string, shape: VertexShape = "node"): VertexView {
  const item = component(id, shape, "concrete");
  return {
    id,
    ref: componentRef(id),
    component: item,
    title: id,
    subtitle: id,
    position: { x: 0, y: 0 },
    shape: vertexShape(item),
    endpoints: { source: item.source ?? null, target: item.target ?? null },
  };
}

function leg(id: string, source: string, target: string, kind: LinkKind = "relation"): LinkView {
  return {
    id,
    source,
    target,
    kind,
    role: kind === "hierarchy" ? "parent" : "out",
    label: "",
    ref: componentRef(source),
  };
}

const xOf = (placed: Record<string, Point>, id: string): number => (placed[id] as Point).x;
const yOf = (placed: Record<string, Point>, id: string): number => (placed[id] as Point).y;

/** The vertex ids grouped by the column their `x` puts them in, left to right. Because the
 * layout left-aligns a column, one `x` per column makes this an exact read of the layering. */
function columns(graph: TopologyGraph, placed: Record<string, Point>): string[][] {
  const byColumn = new Map<number, string[]>();
  for (const vertex of graph.vertices) {
    const x = xOf(placed, vertex.id);
    const bucket = byColumn.get(x);
    if (bucket) bucket.push(vertex.id);
    else byColumn.set(x, [vertex.id]);
  }
  return [...byColumn.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([, ids]) => [...ids].sort());
}

/** The ids of the links of one kind that run right to left, which the layout is only
 * allowed to produce for a cycle the document itself declares. */
function leftward(graph: TopologyGraph, placed: Record<string, Point>, kind: LinkKind): string[] {
  return graph.links
    .filter((link) => link.kind === kind && xOf(placed, link.source) > xOf(placed, link.target))
    .map((link) => link.id)
    .sort();
}

/** The endpoint legs touching one card. Hierarchy links are a separate question: a card
 * with nothing to join can still show what it inherits. */
function legsOf(graph: TopologyGraph, id: string): LinkView[] {
  return graph.links.filter(
    (link) => link.kind !== "hierarchy" && (link.source === id || link.target === id),
  );
}

/** The tightest gap between two cards along each axis, over their measured boxes. Two
 * cards on a diagonal owe each other a gutter on one axis only. */
function gaps(
  vertices: readonly VertexView[],
  placed: Record<string, Point>,
  sizes: (vertex: VertexView) => VertexSize,
): { tightestX: number; tightestY: number } {
  const boxes = vertices.map((vertex) => {
    const point = placed[vertex.id] as Point;
    const size = sizes(vertex);
    return { x: point.x, y: point.y, width: size.width, height: size.height };
  });
  let tightestX = Number.POSITIVE_INFINITY;
  let tightestY = Number.POSITIVE_INFINITY;
  for (const [index, a] of boxes.entries()) {
    for (const b of boxes.slice(index + 1)) {
      const faceToFace = a.y < b.y + b.height && b.y < a.y + a.height;
      const oneAboveOther = a.x < b.x + b.width && b.x < a.x + a.width;
      if (faceToFace) {
        tightestX = Math.min(tightestX, Math.max(a.x - (b.x + b.width), b.x - (a.x + a.width)));
      }
      if (oneAboveOther) {
        tightestY = Math.min(tightestY, Math.max(a.y - (b.y + b.height), b.y - (a.y + a.height)));
      }
    }
  }
  return { tightestX, tightestY };
}

/** A fixed-seed shuffle: a determinism test that itself moved about would be worthless. */
function shuffled(length: number, salt: number): number[] {
  const out = [...Array.from({ length }, (_unused, index) => index)];
  let seed = (0x9e3779b9 ^ salt) >>> 0;
  const next = (): number => {
    seed = (seed * 1_103_515_245 + 12_345) % 2_147_483_648;
    return seed / 2_147_483_648;
  };
  for (let index = out.length - 1; index > 0; index -= 1) {
    const swap = Math.floor(next() * (index + 1));
    const hold = out[index] as number;
    out[index] = out[swap] as number;
    out[swap] = hold;
  }
  return out;
}

function permute<T>(items: readonly T[], order: readonly number[]): T[] {
  return order.map((index) => items[index] as T);
}

const reverse = (length: number): number[] => [...Array.from({ length }, (_unused, index) => length - 1 - index)];

/** Reorderings enough that no code path can lean on the payload's order unnoticed. */
function permutations(vertexCount: number, linkCount: number): { vertices: number[]; links: number[] }[] {
  return [
    { vertices: reverse(vertexCount), links: reverse(linkCount) },
    { vertices: shuffled(vertexCount, 1), links: shuffled(linkCount, 2) },
    { vertices: shuffled(vertexCount, 3), links: shuffled(linkCount, 4) },
  ];
}

/** The sample plus a second category and a node under it, so an edge between two
 *  nodes crosses a category pair the sample has no category edge for yet. */
function pairableDocument(): ProjectDocument {
  return withComponents(clone(), [
    component("locatable", "node", "category"),
    { ...component("gadget", "node", "concrete"), parent: "locatable" },
  ]);
}

