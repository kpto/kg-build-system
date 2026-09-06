/**
 * Pure topology logic: every rule the three-tier hierarchy makes hard to state,
 * isolated so the UI can only ever compose a document the framework accepts.
 *
 * The three tiers (see NODE_EDGE_HIERARCHY_SPEC.md §1 and
 * `studio_backend.ir.document.Component`) are `template` (mix-in: contributes slots
 * and annotations, never enters the blueprint), `category` (a graph-visible abstract
 * parent) and `concrete` (bindable). The rules mirrored here — one category parent,
 * kind-paired mixins, node-side endpoints with category descent, `property(default=None)`
 * only for a nullable slot — are the ones the pydantic model *and* the class-creation
 * walk enforce, so the studio must never offer an edit that violates them.
 *
 * Nothing in this file touches React or the DOM: it reads a `ProjectDocument` and
 * returns a rebuilt one (models are frozen), which is what makes it unit-testable and
 * what keeps every mutation the canvas makes expressible as `apply(draft => ...)`.
 */

import type {
  Binding,
  Component,
  ComponentKind,
  ComponentTier,
  LogicalType,
  Point,
  ProjectDocument,
  Property,
} from "@/lib/ir";
import { isNullable, replaced, sectionItems } from "@/lib/ir";
import { buildRef, declarationName, freeId, parseRef, slugId } from "@/lib/ids";

/* ---------------------------------------------------------------------------- refs */

/** The IR ref a component id addresses on the canvas and in selection. */
export const componentRef = (id: string): string => buildRef("component", id);

/** The component id a (possibly part-qualified) ref addresses, or `null`. */
export function componentIdFromRef(ref: string | null | undefined): string | null {
  const parsed = parseRef(ref);
  return parsed && parsed.kind === "component" ? parsed.id : null;
}

/* ------------------------------------------------------------------ component index */

export function componentsOf(document: ProjectDocument | null | undefined): readonly Component[] {
  return sectionItems(document, "components");
}

export function componentById(
  document: ProjectDocument | null | undefined,
  id: string | null | undefined,
): Component | null {
  if (!id) return null;
  return componentsOf(document).find((item) => item.id === id) ?? null;
}

const takenComponentIds = (document: ProjectDocument): string[] =>
  componentsOf(document).map((item) => item.id);

/** Categories of one kind — the only legal single `parent` for that kind. */
export function categoriesOfKind(document: ProjectDocument, kind: ComponentKind): Component[] {
  return componentsOf(document).filter((item) => item.kind === kind && item.tier === "category");
}

/** Templates of one kind — kind-paired mixins only (spec R3). */
export function templatesOfKind(document: ProjectDocument, kind: ComponentKind): Component[] {
  return componentsOf(document).filter((item) => item.kind === kind && item.tier === "template");
}

/* ----------------------------------------------------------------- naming defaults */

/**
 * The tier suffix the generator renders the declaration name with. Mirrors
 * `generate/topology.py`'s `_TERMINAL_BASE`: a template is `…NodeTemplate`/`…EdgeTemplate`,
 * a category is `…AbstractNode`/…AbstractEdge`, a concrete is `…Node`/`…Edge`.
 */
const TIER_SUFFIX: Readonly<Record<ComponentKind, Record<ComponentTier, string>>> = {
  node: { template: "Node Template", category: "Abstract Node", concrete: "Node" },
  edge: { template: "Edge Template", category: "Abstract Edge", concrete: "Edge" },
};

export function deriveDeclarationName(
  id: string,
  kind: ComponentKind,
  tier: ComponentTier,
): string {
  return declarationName(id, TIER_SUFFIX[kind][tier]);
}

/* --------------------------------------------------------------------- vertex/edges */

/**
 * Whether a component is drawn as a vertex. Node components of every tier are vertices
 * (blue / dashed grey / amber); an edge of tier `category` or `concrete` is drawn as a
 * *link* between its endpoint vertices, and an edge template has no endpoints to hang a
 * link on, so it is an amber vertex like any other template.
 */
export function isVertex(component: Component): boolean {
  return component.kind === "node" || component.tier === "template";
}

/** A relation component drawn as a link (a category or concrete edge with endpoints). */
export function isLink(component: Component): boolean {
  return component.kind === "edge" && component.tier !== "template";
}

/* -------------------------------------------------------------------- kind/tier rules */

/** One category parent of the matching kind; templates take none (spec R1). */
export function canBeParent(childKind: ComponentKind, childTier: ComponentTier, parent: Component): boolean {
  return childTier !== "template" && parent.kind === childKind && parent.tier === "category";
}

/** A mixin is a same-kind template (spec R3 — kind pairing). */
export function canBeMixin(component: Component, mixin: Component): boolean {
  return mixin.kind === component.kind && mixin.tier === "template";
}

/** Endpoints are node-side; an edge-kind category is rejected (spec §6). */
export function canBeEndpoint(endpoint: Component | null): boolean {
  return endpoint !== null && endpoint.kind === "node";
}

/** Both endpoints must be present, node-kind components — the mismatched-kind guard. */
export function endpointsCompatible(
  document: ProjectDocument,
  sourceId: string | null,
  targetId: string | null,
): { ok: boolean; reason?: string } {
  const source = componentById(document, sourceId);
  const target = componentById(document, targetId);
  if (!source || !target) return { ok: false, reason: "both endpoints must name a component" };
  if (!canBeEndpoint(source) || !canBeEndpoint(target)) {
    return { ok: false, reason: "a relationship connects two node components" };
  }
  return { ok: true };
}

/** `true` when a concrete node/edge already has a usable category parent option. */
export function hasCategoryParentFor(document: ProjectDocument, kind: ComponentKind): boolean {
  return categoriesOfKind(document, kind).length > 0;
}

/* ------------------------------------------------------------------------- positions */

const round2 = (value: number): number => Math.round(value * 100) / 100;

/** The stored canvas position for a ref, or `null` when the document has none. */
export function positionOf(document: ProjectDocument, ref: string): Point | null {
  const point = document.views?.topology?.[ref];
  return point ? { x: point.x, y: point.y } : null;
}

/** Rebuild the document with one ref's position written (never in place). */
export function withPosition(
  document: ProjectDocument,
  ref: string,
  position: Point,
): ProjectDocument {
  const topology = { ...(document.views?.topology ?? {}) };
  topology[ref] = { x: round2(position.x), y: round2(position.y) };
  return { ...document, views: { ...(document.views ?? {}), topology } };
}

/**
 * A stable, deterministic layout position for a component the document has never been
 * told where to draw. It is a function of the vertex's index only, so the same document
 * always lays out the same way and a node jumps nowhere until the user drags it (which
 * then persists through `withPosition`).
 */
export function fallbackPosition(index: number): Point {
  const columns = 4;
  const column = index % columns;
  const row = Math.floor(index / columns);
  return { x: 80 + column * 260, y: 80 + row * 180 };
}

/** Roughly equal points, so a stored position and a fallback cell cannot sit on top. */
function collides(a: Point, b: Point): boolean {
  return Math.abs(a.x - b.x) < 200 && Math.abs(a.y - b.y) < 130;
}

/**
 * Assign fallback positions to the vertices that have none, skipping any grid cell that
 * already sits under a stored position. Deterministic on the document, so two renders of
 * the same document place the same nodes in the same spots.
 */
function assignFallbacks(
  needPosition: VertexView[],
  stored: Point[],
): Record<string, Point> {
  const placed = [...stored];
  const out: Record<string, Point> = {};
  let slot = 0;
  for (const vertex of needPosition) {
    let point = fallbackPosition(slot);
    while (placed.some((existing) => collides(point, existing))) {
      slot += 1;
      point = fallbackPosition(slot);
    }
    out[vertex.id] = point;
    placed.push(point);
    slot += 1;
  }
  return out;
}

/**
 * A free canvas point for a component the document has not placed yet, so a freshly
 * created node can be written into the document immediately instead of relying on the
 * transient fallback grid (which would move it again when another node appears).
 */
export function freePosition(document: ProjectDocument): Point {
  const taken: Point[] = Object.values(document.views?.topology ?? {});
  for (const component of componentsOf(document)) {
    const point = positionOf(document, componentRef(component.id));
    if (point) taken.push(point);
  }
  let slot = 0;
  let point = fallbackPosition(slot);
  while (taken.some((existing) => collides(point, existing))) {
    slot += 1;
    point = fallbackPosition(slot);
  }
  return point;
}

/* ----------------------------------------------------------------------- property slots */

/** `property(default=None)` (spec / AUTHORING_IR_CONTRACT.md) needs a nullable slot. */
export function slotAllowsOptional(type: LogicalType | null | undefined): boolean {
  return type != null && isNullable(type);
}

/** Never carry `optional` on a non-nullable slot — the framework would reject it. */
export function normalizeSlot(property: Property): Property {
  if (property.optional && !slotAllowsOptional(property.logical_type)) {
    return { ...property, optional: false };
  }
  return property;
}

export function setSlotType(property: Property, type: LogicalType): Property {
  return normalizeSlot({ ...property, logical_type: type });
}

export function setSlotOptional(property: Property, optional: boolean): Property {
  if (optional && !slotAllowsOptional(property.logical_type)) return property;
  return { ...property, optional };
}

/** An empty slot a fresh component or a new row can start from (nullable, so a
 *  binding may leave it unfilled and the optional toggle is immediately usable). */
export const emptySlot = (name: string): Property => ({
  name,
  logical_type: { kind: "nullable", value: { kind: "unit", name: "str" } },
  description: null,
  optional: false,
});

/* ------------------------------------------------------------------------- deletion */

export interface DeleteImpact {
  readonly componentId: string;
  /** Bindings that point at the component and would dangle. */
  readonly bindings: readonly Binding[];
  /** Components that name it as their `parent` (the category tree below it). */
  readonly children: readonly Component[];
  /** Components that mix it in. */
  readonly mixinUsers: readonly Component[];
  /** Edges that declare it as a `source`/`target` endpoint. */
  readonly endpointUsers: readonly Component[];
  /** Anything a delete would orphan — the warning is required when this is `true`. */
  readonly dangling: boolean;
}

/** What breaks if one component disappears, computed straight from the document. */
export function deleteImpact(document: ProjectDocument, componentId: string): DeleteImpact {
  const bindings = sectionItems(document, "bindings").filter(
    (binding) => (binding as Binding).component === componentId,
  ) as Binding[];
  const children: Component[] = [];
  const mixinUsers: Component[] = [];
  const endpointUsers: Component[] = [];
  for (const component of componentsOf(document)) {
    if (component.id === componentId) continue;
    if (component.parent === componentId) children.push(component);
    if (component.mixins?.includes(componentId)) mixinUsers.push(component);
    if (component.source === componentId || component.target === componentId) {
      endpointUsers.push(component);
    }
  }
  const dangling =
    bindings.length + children.length + mixinUsers.length + endpointUsers.length > 0;
  return { componentId, bindings, children, mixinUsers, endpointUsers, dangling };
}

/**
 * Remove a component and repair the references that would otherwise dangle: its bindings
 * go with it, children re-parent onto the removed node's own parent (the category chain
 * compresses), and it is dropped from every mixin list and cleared from every endpoint.
 */
export function removeComponentCascade(document: ProjectDocument, componentId: string): ProjectDocument {
  const removed = componentById(document, componentId);
  const newParent = removed?.parent ?? null;
  let next: ProjectDocument = {
    ...document,
    components: componentsOf(document)
      .filter((component) => component.id !== componentId)
      .map((component) => {
        let changed = component;
        if (changed.parent === componentId) changed = { ...changed, parent: newParent };
        if (changed.mixins?.includes(componentId)) {
          changed = { ...changed, mixins: changed.mixins.filter((id) => id !== componentId) };
        }
        if (changed.source === componentId) changed = { ...changed, source: newParent };
        if (changed.target === componentId) changed = { ...changed, target: newParent };
        return changed;
      }),
  };
  // A binding names its component, so every binding of the removed node or edge goes too.
  next = {
    ...next,
    bindings: sectionItems(document, "bindings").filter(
      (binding) => (binding as Binding).component !== componentId,
    ) as Binding[],
  };
  // Forget the deleted ref's stored canvas position too.
  if (next.views?.topology) {
    const topology = { ...next.views.topology };
    delete topology[componentRef(componentId)];
    next = { ...next, views: { ...next.views, topology } };
  }
  return next;
}

/* ------------------------------------------------------------------------ creation */

/** The identity parts a new component derives from its display name (mirror ids.ts). */
export function deriveIdentity(
  document: ProjectDocument,
  displayName: string,
  kind: ComponentKind,
  tier: ComponentTier,
): { id: string; name: string; declaration_name: string } {
  const base = slugId(displayName, kind);
  const id = freeId(base, takenComponentIds(document));
  return { id, name: id, declaration_name: deriveDeclarationName(id, kind, tier) };
}

export interface NewComponentSpec {
  displayName: string;
  kind: ComponentKind;
  tier: ComponentTier;
  /** A chosen category parent (required for `concrete`; ignored for `template`). */
  parentId?: string | null;
}

export interface CreatedComponent {
  readonly component: Component;
  /** The category parent created on demand when a concrete node had none. */
  readonly createdCategory: Component | null;
}

/** The framework-legal defaults for a fresh vertex component. */
export function createComponent(
  document: ProjectDocument,
  spec: NewComponentSpec,
): CreatedComponent {
  const { kind, tier } = spec;
  const identity = deriveIdentity(document, spec.displayName, kind, tier);
  let parent: string | null = null;
  let createdCategory: Component | null = null;

  if (tier === "category" || tier === "concrete") {
    const chosen = componentById(document, spec.parentId ?? null);
    if (tier === "category" && chosen && chosen.kind === kind && chosen.tier === "category") {
      parent = chosen.id;
    }
    if (tier === "concrete") {
      if (chosen && canBeParent(kind, tier, chosen)) {
        parent = chosen.id;
      } else {
        // Concrete needs a category parent; mint an `unnamed`-style one on demand.
        const categoryIdentity = deriveIdentity(document, "unnamed", kind, "category");
        createdCategory = baseComponent(categoryIdentity, kind, "category", "Unnamed");
        parent = createdCategory.id;
      }
    }
  }

  // Templates carry no label (their options are annotations only, spec §3).
  const label = tier === "template" ? null : spec.displayName;
  const component = baseComponent(identity, kind, tier, label, parent);
  return { component, createdCategory };
}

function baseComponent(
  identity: { id: string; name: string; declaration_name: string },
  kind: ComponentKind,
  tier: ComponentTier,
  label: string | null,
  parent: string | null = null,
): Component {
  return {
    id: identity.id,
    kind,
    tier,
    declaration_name: identity.declaration_name,
    name: identity.name,
    description: null,
    label,
    parent,
    mixins: [],
    source: null,
    target: null,
    properties: [],
    annotations: [],
  };
}

/** The category id an edge endpoint descends from: the node's own category parent. */
export function categoryEndpoint(document: ProjectDocument, componentId: string): string | null {
  const component = componentById(document, componentId);
  if (!component) return null;
  if (component.tier === "category") return component.id;
  return component.parent ?? component.id;
}

/** An edge category whose declared endpoints are exactly this category pair, if any. */
export function findCategoryEdgeForPair(
  document: ProjectDocument,
  sourceCategory: string | null,
  targetCategory: string | null,
): Component | null {
  if (!sourceCategory || !targetCategory) return null;
  return (
    componentsOf(document).find(
      (component) =>
        component.kind === "edge" &&
        component.tier === "category" &&
        component.source === sourceCategory &&
        component.target === targetCategory,
    ) ?? null
  );
}

export interface NewEdgeSpec {
  /** The human predicate, e.g. "has unit" — becomes the component id + name. */
  predicate: string;
  /** The semantic edge label, e.g. "HAS_UNIT". */
  label: string;
  sourceId: string;
  targetId: string;
  /** Create a category edge when none covers the endpoint pair (the UI default). */
  createCategoryIfMissing: boolean;
}

export type CreatedEdge =
  | {
      readonly ok: true;
      readonly concrete: Component;
      readonly createdCategory: Component | null;
      readonly parentRef: string | null;
    }
  | { readonly ok: false; readonly reason: string };

/**
 * Build a concrete edge between two node vertices plus the category parent it legally
 * requires: reuse an existing edge category over the endpoints' category pair, else mint
 * one when the user opted in. A concrete edge cannot exist without a category parent, so
 * when there is neither an existing category nor consent to create one, the flow refuses.
 */
export function createEdgePair(document: ProjectDocument, spec: NewEdgeSpec): CreatedEdge {
  const check = endpointsCompatible(document, spec.sourceId, spec.targetId);
  if (!check.ok) return { ok: false, reason: check.reason ?? "invalid endpoints" };

  const sourceCategory = categoryEndpoint(document, spec.sourceId);
  const targetCategory = categoryEndpoint(document, spec.targetId);

  const identity = deriveIdentity(document, spec.predicate, "edge", "concrete");

  // Rebuild the taken-id view after we know the concrete id, so a category never collides.
  let createdCategory: Component | null = null;
  let parentId: string | null = null;

  const existing = findCategoryEdgeForPair(document, sourceCategory, targetCategory);
  if (existing) {
    parentId = existing.id;
  } else if (spec.createCategoryIfMissing) {
    const categoryTaken = new Set([...takenComponentIds(document), identity.id]);
    const categorySlug = slugId(`${sourceCategory ?? "from"}_to_${targetCategory ?? "to"}`, "relation");
    const categoryId = freeId(categorySlug, categoryTaken);
    createdCategory = {
      id: categoryId,
      kind: "edge",
      tier: "category",
      declaration_name: deriveDeclarationName(categoryId, "edge", "category"),
      name: categoryId,
      description: null,
      label: spec.label,
      parent: null,
      mixins: [],
      source: sourceCategory,
      target: targetCategory,
      properties: [],
      annotations: [],
    };
    parentId = categoryId;
  } else {
    return {
      ok: false,
      reason: "a concrete edge needs a category parent — create one or reuse another",
    };
  }

  const concrete: Component = {
    id: identity.id,
    kind: "edge",
    tier: "concrete",
    declaration_name: identity.declaration_name,
    name: identity.name,
    description: null,
    label: spec.label,
    parent: parentId,
    mixins: [],
    source: spec.sourceId,
    target: spec.targetId,
    properties: [],
    annotations: [],
  };

  return {
    ok: true,
    concrete,
    createdCategory,
    parentRef: parentId ? componentRef(parentId) : null,
  };
}

/* ------------------------------------------------------------------------ graph build */

export interface TopologyFilters {
  showTemplates: boolean;
  showCategories: boolean;
  showHierarchy: boolean;
}

export const DEFAULT_FILTERS: TopologyFilters = {
  showTemplates: true,
  showCategories: true,
  showHierarchy: true,
};

export interface VertexView {
  readonly id: string;
  readonly ref: string;
  readonly component: Component;
  readonly title: string;
  readonly subtitle: string;
  readonly position: Point;
}

export type LinkKind = "relation" | "category" | "hierarchy";

export interface LinkView {
  readonly id: string;
  readonly source: string;
  readonly target: string;
  readonly kind: LinkKind;
  readonly label: string;
  /** The component ref selection resolves to when this link is clicked. */
  readonly ref: string;
}

export interface TopologyGraph {
  readonly vertices: readonly VertexView[];
  readonly links: readonly LinkView[];
  /** Every component that is drawn (vertices + links), for "reveal" lookups. */
  readonly refsById: Readonly<Record<string, string>>;
}

const vertexTitle = (component: Component): string =>
  component.name || component.declaration_name || component.id;

const vertexSubtitle = (component: Component): string =>
  component.label ?? `${component.kind} ${component.tier}`;

/** Drawn-visibility given the scope filters. */
function vertexVisible(component: Component, filters: TopologyFilters): boolean {
  if (component.tier === "template") return filters.showTemplates;
  if (component.tier === "category") return filters.showCategories;
  return true;
}

/**
 * Flatten the document into canvas vertices and links. Vertices are node components and
 * templates; links are category/concrete edge components (green concrete, purple
 * category) plus grey dashed is-a hierarchy edges (parent → child, template → mixer).
 */
export function buildGraph(
  document: ProjectDocument,
  filters: TopologyFilters = DEFAULT_FILTERS,
): TopologyGraph {
  const components = componentsOf(document);
  const raw: VertexView[] = [];
  const drawnIds = new Set<string>();
  const needPosition: VertexView[] = [];
  const stored: Point[] = [];
  for (const component of components) {
    if (!isVertex(component) || !vertexVisible(component, filters)) continue;
    const ref = componentRef(component.id);
    const storedPosition = positionOf(document, ref);
    const vertex: VertexView = {
      id: component.id,
      ref,
      component,
      title: vertexTitle(component),
      subtitle: vertexSubtitle(component),
      position: storedPosition ?? { x: 0, y: 0 },
    };
    raw.push(vertex);
    drawnIds.add(component.id);
    if (storedPosition) stored.push(storedPosition);
    else needPosition.push(vertex);
  }

  const fallbacks = assignFallbacks(needPosition, stored);
  const vertices: VertexView[] = raw.map((vertex) => {
    const fallback = fallbacks[vertex.id];
    return fallback ? { ...vertex, position: fallback } : vertex;
  });

  const links: LinkView[] = [];

  for (const component of components) {
    if (!isLink(component)) continue;
    if (component.tier === "category" && !filters.showCategories) continue;
    if (!drawnIds.has(component.source ?? "") || !drawnIds.has(component.target ?? "")) continue;
    links.push({
      id: `link:${component.id}`,
      source: component.source as string,
      target: component.target as string,
      kind: component.tier === "category" ? "category" : "relation",
      label: component.label ?? component.name,
      ref: componentRef(component.id),
    });
  }

  if (filters.showHierarchy) {
    for (const component of components) {
      if (!drawnIds.has(component.id)) continue;
      const parent = component.parent;
      if (parent && drawnIds.has(parent)) {
        links.push({
          id: `hier:${component.id}:parent`,
          source: parent,
          target: component.id,
          kind: "hierarchy",
          label: "is-a",
          ref: componentRef(component.id),
        });
      }
      for (const mixin of component.mixins ?? []) {
        if (!drawnIds.has(mixin)) continue;
        links.push({
          id: `hier:${component.id}:mixin:${mixin}`,
          source: mixin,
          target: component.id,
          kind: "hierarchy",
          label: "mixes",
          ref: componentRef(component.id),
        });
      }
    }
  }

  const refsById: Record<string, string> = {};
  for (const vertex of vertices) refsById[vertex.id] = vertex.ref;
  for (const component of components) if (!(component.id in refsById)) refsById[component.id] = componentRef(component.id);

  return { vertices, links, refsById };
}

/* -------------------------------------------------------------------- identity edits */

/** Rename a component's display name in place, keeping `id` and `declaration_name`. */
export function renameComponent(document: ProjectDocument, id: string, displayName: string): ProjectDocument {
  const component = componentById(document, id);
  if (!component) return document;
  return replaced(document, "components", { ...component, name: displayName });
}

/** Apply a field-level patch to one component, keeping it frozen-model clean. */
export function patchComponent(
  document: ProjectDocument,
  id: string,
  changes: Partial<Component>,
): ProjectDocument {
  const component = componentById(document, id);
  if (!component) return document;
  return replaced(document, "components", { ...component, ...changes });
}
