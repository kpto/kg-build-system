import { describe, expect, it } from "vitest";

import {
  createComponent,
  createEdgePair,
  buildGraph,
  categoryEndpoint,
  deleteImpact,
  deriveIdentity,
  emptySlot,
  findCategoryEdgeForPair,
  freePosition,
  normalizeSlot,
  positionOf,
  removeComponentCascade,
  setSlotOptional,
  setSlotType,
  slotAllowsOptional,
  withPosition,
  canBeMixin,
  canBeParent,
  canBeEndpoint,
  DEFAULT_FILTERS,
} from "./logic";
import { SAMPLE_DOCUMENT } from "@/lib/sampleDocument";
import type { Component, ProjectDocument } from "@/lib/ir";
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

describe("buildGraph — drawing the three tiers", () => {
  it("draws node components and templates as vertices, edges as links", () => {
    const graph = buildGraph(clone(), DEFAULT_FILTERS);
    const vertexIds = new Set(graph.vertices.map((v) => v.id));
    expect(vertexIds.has("site")).toBe(true);
    expect(vertexIds.has("documented")).toBe(true);
    expect(vertexIds.has("provenanced_node")).toBe(true);
    // has_unit is a concrete edge -> a link, not a vertex.
    expect(vertexIds.has("has_unit")).toBe(false);
    const relation = graph.links.find((l) => l.id === "link:has_unit");
    expect(relation?.kind).toBe("relation");
    expect(relation?.source).toBe("site");
    expect(relation?.target).toBe("unit");
  });

  it("adds is-a hierarchy links for parent and mixin edges", () => {
    const graph = buildGraph(clone(), DEFAULT_FILTERS);
    expect(graph.links.some((l) => l.id === "hier:site:parent" && l.kind === "hierarchy")).toBe(
      true,
    );
    expect(
      graph.links.some((l) => l.id === "hier:site:mixin:provenanced_node" && l.kind === "hierarchy"),
    ).toBe(true);
  });

  it("hides template vertices and their hierarchy links when filtered out", () => {
    const graph = buildGraph(clone(), { ...DEFAULT_FILTERS, showTemplates: false });
    expect(graph.vertices.some((v) => v.id === "provenanced_node")).toBe(false);
    expect(graph.links.some((l) => l.kind === "hierarchy" && l.source === "provenanced_node")).toBe(
      false,
    );
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

/** The sample plus a second category and a node under it, so an edge between two
 *  nodes crosses a category pair the sample has no category edge for yet. */
function pairableDocument(): ProjectDocument {
  return withComponents(clone(), [
    component("locatable", "node", "category"),
    { ...component("gadget", "node", "concrete"), parent: "locatable" },
  ]);
}

