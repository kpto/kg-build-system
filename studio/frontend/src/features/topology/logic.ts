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

/* ------------------------------------------------------------------- vertex shapes */

/**
 * The card a component is drawn as.
 *
 * Every visible component is a vertex, an edge included: a relation drawn as a line between
 * two nodes can never itself be the child of a category, so its `is-a` would be undrawable.
 * Reifying it as a card of its own — the metagraph reading as node card → edge card → node
 * card — is what lets the edge hierarchy onto the canvas at all.
 *
 * Only the two kinds that reach the blueprint are ever drawn; a template has no card and
 * `templateCatalogue` is its surface instead.
 */
export type VertexShape = "node" | "edge";

/** Edge kind is edge-shaped at every tier that gets drawn. */
export function vertexShape(component: Component): VertexShape {
  return component.kind === "edge" ? "edge" : "node";
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
 * Rebuild the document with many positions written at once (never in place), for a
 * whole-canvas tidy layout.
 *
 * Keys are component ids, or the refs a caller already holds — either way the id has to
 * resolve to a component of this document, because a stored position for something that is
 * not drawn is junk the next load would have to guess about.
 */
export function withPositions(
  document: ProjectDocument,
  positions: Readonly<Record<string, Point>>,
): ProjectDocument {
  const topology = { ...(document.views?.topology ?? {}) };
  let written = false;
  for (const key of Object.keys(positions).sort()) {
    const point = positions[key];
    if (!point || !Number.isFinite(point.x) || !Number.isFinite(point.y)) continue;
    const id = componentIdFromRef(key) ?? key;
    if (!componentById(document, id)) continue;
    topology[componentRef(id)] = { x: round2(point.x), y: round2(point.y) };
    written = true;
  }
  if (!written) return document;
  return { ...document, views: { ...(document.views ?? {}), topology } };
}

/**
 * Rebuild the document with every canvas position that cannot be drawn any more forgotten.
 *
 * `views.topology` only ever accumulates. Templates kept their points after they left the
 * graph (they are not vertices — see `vertexVisible`), a component deleted by another
 * surface leaves its ref behind, and both sit in the document forever. What is *not* a leak
 * is a position for a component that exists and is merely hidden by the current scope
 * filters: deleting where somebody put a category because a checkbox moved would destroy
 * their work on a view blip, and the document is their data.
 *
 * So the decision is made from the document — does a component with this id exist, and is it
 * drawable at all — and deliberately not from a `TopologyGraph`, which is the *filtered*
 * view of it.
 */
export function prunePositions(document: ProjectDocument): ProjectDocument {
  const stored = document.views?.topology;
  if (!stored) return document;
  const topology: Record<string, Point> = {};
  let dropped = false;
  // Sorted, so pruning the same content twice rebuilds the same key order.
  for (const key of Object.keys(stored).sort()) {
    const point = stored[key];
    if (point && isDrawableRef(document, key)) topology[key] = point;
    else dropped = true;
  }
  if (!dropped) return document;
  return { ...document, views: { ...(document.views ?? {}), topology } };
}

/**
 * Whether a stored position addresses something the canvas could draw: exactly the ref of a
 * component that exists and is no template. Anything else — a foreign ref kind, a
 * part-qualified ref, an id with no component behind it — is not a place anything sits.
 */
function isDrawableRef(document: ProjectDocument, key: string): boolean {
  const id = componentIdFromRef(key);
  if (id === null || key !== componentRef(id)) return false;
  const component = componentById(document, id);
  return component !== null && component.tier !== "template";
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
 *
 * Every drawn component is a vertex, so the taken set spans node cards and edge cards
 * alike: it is every stored position, which covers an edge ref exactly like a node ref,
 * plus the stored position of any component the document still places (a template keeps
 * one even though it is no longer drawn, and a new card has no business landing on it).
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
  showCategories: boolean;
  showHierarchy: boolean;
}

export const DEFAULT_FILTERS: TopologyFilters = {
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
  readonly shape: VertexShape;
  /**
   * The declared endpoint ids, whether or not they resolve to a drawn vertex. A card
   * keeps them so the canvas can say *what* dangles; the layout gives it no legs until
   * both ends are actually on the canvas.
   */
  readonly endpoints: { readonly source: string | null; readonly target: string | null };
}

export type LinkKind = "relation" | "category" | "hierarchy";

/**
 * What the link means at the vertex it touches, so one edge card can draw its two legs
 * differently: `in` arrives at the card, `out` leaves it, `parent` arrives at the child of
 * an is-a link.
 *
 * There is no `mixin` role: a mix-in template is not a vertex (see `vertexVisible`), so it
 * has no card for such a link to run between. The template library lists who mixes what.
 */
export type LinkRole = "in" | "out" | "parent";

export interface LinkView {
  readonly id: string;
  /** Vertex id, never a component ref — React Flow addresses nodes by id. */
  readonly source: string;
  readonly target: string;
  readonly kind: LinkKind;
  readonly role: LinkRole;
  readonly label: string;
  /** The component ref selection resolves to when this link is clicked. */
  readonly ref: string;
}

export interface TopologyGraph {
  readonly vertices: readonly VertexView[];
  readonly links: readonly LinkView[];
  /** Every component id in the document, drawn or not, for "reveal" lookups. */
  readonly refsById: Readonly<Record<string, string>>;
}

const vertexTitle = (component: Component): string =>
  component.name || component.declaration_name || component.id;

const vertexSubtitle = (component: Component): string =>
  component.label ?? `${component.kind} ${component.tier}`;

/** Drawn-visibility given the scope filters. */
function vertexVisible(component: Component, filters: TopologyFilters): boolean {
  // A template is never drawn, whatever the filters say: it does not reach the blueprint,
  // so it is not a vertex of the metagraph (`meta_graph.topology.effective_components`
  // keeps bound components, their abstract ancestors and endpoint categories only). It is a
  // reusable declaration fragment and `templateCatalogue` is its surface.
  if (component.tier === "template") return false;
  if (component.tier === "category") return filters.showCategories;
  return true;
}

/**
 * Flatten the document into the metagraph the canvas draws: every visible component is a
 * vertex (node card or edge card), and every link between them is either one leg of an
 * edge card or one step of a hierarchy.
 *
 * The vertex set is the framework's own metagraph, not the whole document: a mix-in
 * template never reaches the blueprint, so it is not a vertex and no link points at one
 * (`templateCatalogue` is where the templates live).
 *
 * An edge card is joined to its endpoints by two legs — `source → card` (`in`,
 * unlabelled) and `card → target` (`out`, carrying the relation's label), so the predicate
 * is written once per relation instead of twice along one polyline. Hierarchy links
 * (`parent → child`) fire for edge cards exactly as they do for node cards, which is the
 * whole point of drawing an edge as a card.
 */
export function buildGraph(
  document: ProjectDocument,
  filters: TopologyFilters = DEFAULT_FILTERS,
): TopologyGraph {
  const components = distinctComponents(componentsOf(document));
  const visible = new Set<string>();
  const raw: VertexView[] = [];
  const needPosition: VertexView[] = [];
  const stored: Point[] = [];
  for (const component of components) {
    if (!vertexVisible(component, filters) || visible.has(component.id)) continue;
    visible.add(component.id);
    const ref = componentRef(component.id);
    const storedPosition = positionOf(document, ref);
    const vertex: VertexView = {
      id: component.id,
      ref,
      component,
      title: vertexTitle(component),
      subtitle: vertexSubtitle(component),
      position: storedPosition ?? { x: 0, y: 0 },
      shape: vertexShape(component),
      endpoints: { source: component.source ?? null, target: component.target ?? null },
    };
    raw.push(vertex);
    if (storedPosition) stored.push(storedPosition);
    else needPosition.push(vertex);
  }

  const fallbacks = assignFallbacks(needPosition, stored);
  const vertices: VertexView[] = raw.map((vertex) => {
    const fallback = fallbacks[vertex.id];
    return fallback ? { ...vertex, position: fallback } : vertex;
  });

  const links: LinkView[] = [];

  // Endpoint legs. Both ends have to be drawn for the card to be joinable at all: a card
  // naming a hidden or dangling component keeps its zero legs and its vertex, because the
  // way out of a dangling endpoint is to be able to see and select the card that dangles.
  for (const vertex of vertices) {
    if (vertex.shape !== "edge") continue;
    const source = vertex.endpoints.source;
    const target = vertex.endpoints.target;
    if (!source || !target) continue;
    if (!visible.has(source) || !visible.has(target)) continue;
    const kind: LinkKind = vertex.component.tier === "category" ? "category" : "relation";
    const label = vertex.component.label ?? vertex.component.name;
    // A card that names itself as an endpoint cannot be joined to itself — that link would
    // have no direction and React Flow would draw it as a self-loop.
    if (source !== vertex.id) {
      links.push({
        id: `link:${vertex.id}:in`,
        source,
        target: vertex.id,
        kind,
        role: "in",
        label: "",
        ref: vertex.ref,
      });
    }
    if (target !== vertex.id) {
      links.push({
        id: `link:${vertex.id}:out`,
        source: vertex.id,
        target,
        kind,
        role: "out",
        label,
        ref: vertex.ref,
      });
    }
  }

  if (filters.showHierarchy) {
    for (const component of components) {
      if (!visible.has(component.id)) continue;
      const parent = component.parent ?? null;
      // Mixes are not drawn: a template is not a vertex, so there is nothing to link to.
      // `templateCatalogue` reports the same fact as data, which is where it belongs.
      if (parent && parent !== component.id && visible.has(parent)) {
        links.push({
          id: `hier:${component.id}:parent`,
          source: parent,
          target: component.id,
          kind: "hierarchy",
          role: "parent",
          label: "is-a",
          ref: componentRef(component.id),
        });
      }
    }
  }

  const refsById: Record<string, string> = {};
  for (const vertex of vertices) refsById[vertex.id] = vertex.ref;
  // A component that is drawn but currently filtered out (a hidden category, the endpoint of
  // a card that kept its vertex) stays revealable. A template does not: there is no vertex to
  // centre, and the library handles it.
  for (const component of components) {
    if (component.tier === "template" || component.id in refsById) continue;
    refsById[component.id] = componentRef(component.id);
  }

  return { vertices, links, refsById };
}

/**
 * The components with each id once, in declaration order.
 *
 * A document arriving over HTTP is not guaranteed to be id-unique, and a repeated id would
 * repeat every link derived from it — two React Flow edges with one id is a real defect, so
 * the second copy is dropped here rather than drawn twice.
 */
function distinctComponents(components: readonly Component[]): Component[] {
  const seen = new Set<string>();
  const out: Component[] = [];
  for (const component of components) {
    if (seen.has(component.id)) continue;
    seen.add(component.id);
    out.push(component);
  }
  return out;
}

/* --------------------------------------------------------------- template library */

export interface TemplateEntry {
  readonly component: Component;
  /** Components that list this template in `mixins`, in document order. */
  readonly users: readonly Component[];
  /** Slot names the template contributes, i.e. its own `properties`. */
  readonly slotNames: readonly string[];
}

/**
 * Every mix-in template in the document, as the library lists it.
 *
 * Templates are exactly what `buildGraph` leaves out: a template never reaches the
 * blueprint, so it is not a vertex of the metagraph and drawing one was a box floating in
 * the middle of the graph, connected to nothing. What it *is* — a reusable bundle of slots
 * and annotations — is a row here, with the components that mix it in and the slots it
 * contributes.
 *
 * A template mixed into nothing still appears, with `users` empty: an unused template is
 * otherwise invisible, and "declared but never mixed in" is precisely the thing worth
 * surfacing. Ordered node templates first and then by id, so the list cannot reshuffle
 * because a component elsewhere in the document moved.
 */
export function templateCatalogue(document: ProjectDocument): TemplateEntry[] {
  const components = componentsOf(document);

  // Document order, one entry per mixing component (a template listed twice by one
  // component is still one user).
  const usersOf = new Map<string, Component[]>();
  for (const component of components) {
    for (const mixin of new Set(component.mixins ?? [])) {
      const bucket = usersOf.get(mixin);
      if (bucket) bucket.push(component);
      else usersOf.set(mixin, [component]);
    }
  }

  const kindFirst = (component: Component): number => (component.kind === "node" ? 0 : 1);
  return components
    .filter((component) => component.tier === "template")
    .sort((a, b) => kindFirst(a) - kindFirst(b) || byId(a.id, b.id))
    .map((component) => ({
      component,
      users: usersOf.get(component.id) ?? [],
      slotNames: (component.properties ?? []).map((property) => property.name),
    }));
}

/* --------------------------------------------------------------------- auto layout */

/** The box one card occupies, so the layout spaces real cards rather than guesses. */
export interface VertexSize {
  readonly width: number;
  readonly height: number;
}

/** What the node and edge cards are styled to before anything has been measured. */
export const DEFAULT_NODE_SIZE: VertexSize = { width: 216, height: 64 };
export const DEFAULT_EDGE_SIZE: VertexSize = { width: 232, height: 88 };

/** Every coordinate lands on this grid, so a written position stays tidy to look at. */
const LAYOUT_GRID = 4;
/** Clear space between two columns, and between two cards in one column. Both are well
 * over the minimum gutter, which is what makes the grid snapping below safe: flooring a
 * coordinate can only ever take `(LAYOUT_GRID - 1)` out of the gap. */
const COLUMN_GUTTER = 80;
const ROW_GUTTER = 44;

/** A total order that never depends on insertion order or locale. */
const byId = (a: string, b: string): number => (a < b ? -1 : a > b ? 1 : 0);

/** Down onto the grid and never below the origin. */
const snap = (value: number): number =>
  Number.isFinite(value) ? Math.max(0, Math.floor(value / LAYOUT_GRID) * LAYOUT_GRID) : 0;

/** A measured box that cannot be NaN, zero or negative. */
const positive = (value: number, fallback: number): number =>
  Number.isFinite(value) && value > 0 ? value : fallback;

interface Adjacency {
  /** `id → targets`, ascending. */
  readonly forward: Map<string, string[]>;
  /** `id → sources`, ascending. */
  readonly back: Map<string, string[]>;
}

/**
 * `source → target` and its inverse over one class of links: self-loops, links to a
 * vertex that is not drawn and repeated connections between the same pair all drop out,
 * and both lists come back sorted. Everything downstream folds over these lists, so the
 * sorted-ness is what makes a shuffled `links` array lay out identically.
 */
function adjacency(
  ids: ReadonlySet<string>,
  links: readonly LinkView[],
  include: (link: LinkView) => boolean,
): Adjacency {
  const forward = new Map<string, string[]>();
  const back = new Map<string, string[]>();
  for (const id of ids) {
    forward.set(id, []);
    back.set(id, []);
  }
  const seen = new Set<string>();
  for (const link of links) {
    if (link.source === link.target || !include(link)) continue;
    if (!ids.has(link.source) || !ids.has(link.target)) continue;
    // `:` cannot occur in a component id, so two pairs can never read as one.
    const pair = `${link.source}:${link.target}`;
    if (seen.has(pair)) continue;
    seen.add(pair);
    (forward.get(link.source) as string[]).push(link.target);
    (back.get(link.target) as string[]).push(link.source);
  }
  for (const id of ids) {
    (forward.get(id) as string[]).sort(byId);
    (back.get(id) as string[]).sort(byId);
  }
  return { forward, back };
}

/** Both link classes, joined into one undirected neighbour list per vertex. */
function neighboursOf(ids: readonly string[], legs: Adjacency, hierarchy: Adjacency): Map<string, string[]> {
  const out = new Map<string, string[]>();
  for (const id of ids) {
    const neighbours = new Set<string>([
      ...(legs.forward.get(id) ?? []),
      ...(legs.back.get(id) ?? []),
      ...(hierarchy.forward.get(id) ?? []),
      ...(hierarchy.back.get(id) ?? []),
    ]);
    out.set(id, [...neighbours].sort(byId));
  }
  return out;
}

/**
 * Why one card has to sit right of another, in the order a cycle gives them up: an is-a
 * step never, a concrete relation leg only when the hierarchy forces it, and a category's
 * declaration leg first of all.
 */
type ConstraintStrength = "is-a" | "flow" | "declaration";

const GIVE_UP_FIRST: Record<ConstraintStrength, number> = { declaration: 0, flow: 1, "is-a": 2 };

/** One rightward layout constraint: `to` is drawn at least one column right of `from`. */
interface Constraint {
  readonly from: string;
  readonly to: string;
  readonly strength: ConstraintStrength;
}

/**
 * The links that decide columns, as rightward constraints.
 *
 * - every is-a step, `parent → child`, strongest: x must never fight the hierarchy, so a
 *   category sits left of everything that descends from it and an edge category left of the
 *   concrete cards that inherit it;
 * - every `relation` leg, strong: a concrete edge card between the two node columns it
 *   joins is the data flow the horizontal axis exists to be read as;
 * - a `category` leg's **`in` direction only** — `endpoint → card`, the weakest: the card
 *   lands one column right of the deepest node category it joins, so an unused category
 *   edge does not drift to the far side of the canvas with its legs stretched back over
 *   everything.
 *
 * The `out` leg of a category is never a constraint, and that asymmetry is the point: a
 * category declares which node *kinds* may be joined, so it may position itself but it must
 * never push an endpoint — and above all never push an endpoint *category* rightwards, which
 * is what once put `documented` to the right of its own children and made its is-a arrows
 * point backwards. A self-join like `documented → documented` has no "between" column to
 * occupy, and gets none. Both legs are still drawn; the out leg simply takes whatever
 * column the stronger rules left it, including one to the left.
 */
function layoutConstraints(links: readonly LinkView[], drawn: ReadonlySet<string>): Constraint[] {
  const byPair = new Map<string, Constraint>();
  const offer = (from: string, to: string, strength: ConstraintStrength): void => {
    const pair = `${from}:${to}`;
    const existing = byPair.get(pair);
    // Two rules can name the same pair (a category card that is also someone's parent).
    // Keep the stronger one, so which link arrived first cannot change the layout.
    if (existing && GIVE_UP_FIRST[existing.strength] <= GIVE_UP_FIRST[strength]) return;
    byPair.set(pair, { from, to, strength });
  };

  for (const link of links) {
    if (link.source === link.target) continue;
    if (!drawn.has(link.source) || !drawn.has(link.target)) continue;
    if (link.kind === "hierarchy") offer(link.source, link.target, "is-a");
    else if (link.kind === "relation") offer(link.source, link.target, "flow");
    else if (link.role === "in") offer(link.source, link.target, "declaration");
  }
  return [...byPair.values()].sort((a, b) => byId(a.from, b.from) || byId(a.to, b.to));
}

/** `from → [constraints leaving it]`, in the order the constraints were sorted in. */
function outgoingOf(constraints: readonly Constraint[]): Map<string, Constraint[]> {
  const outgoing = new Map<string, Constraint[]>();
  for (const constraint of constraints) {
    const bucket = outgoing.get(constraint.from);
    if (bucket) bucket.push(constraint);
    else outgoing.set(constraint.from, [constraint]);
  }
  return outgoing;
}

/** The constraints that sit on a cycle: dropping them all leaves an acyclic set. */
function cyclicConstraints(
  outgoing: ReadonlyMap<string, readonly Constraint[]>,
  constraints: readonly Constraint[],
): Constraint[] {
  // A constraint closes a cycle when its target can still walk back to its source without
  // using it. Graphs this size make the linear scans cheaper than the bookkeeping.
  const reaches = (from: string, target: string, skip: Constraint): boolean => {
    const seenIds = new Set<string>([from]);
    const queue = [from];
    for (let head = 0; head < queue.length; head += 1) {
      for (const next of outgoing.get(queue[head] as string) ?? []) {
        if (next === skip || seenIds.has(next.to)) continue;
        seenIds.add(next.to);
        queue.push(next.to);
      }
    }
    return seenIds.has(target);
  };
  return constraints.filter((constraint) => reaches(constraint.to, constraint.from, constraint));
}

/** How far the loop count is chased before it is called "many" — see `cycleLoad`. */
const LOAD_CAP = 32;
const WALK_CAP = 4096;

/**
 * How many loops one constraint carries: the number of distinct paths from its target back
 * to its source without using it, i.e. the number of cycles it sits on.
 *
 * Both counts are capped. The exact number never matters — only which of two constraints
 * carries more — and a densely cyclic document must not cost the layout more than a bounded
 * walk. A capped count still orders correctly up to the cap, and ties fall through to the
 * strength and the pair, both total orders.
 */
function cycleLoad(outgoing: ReadonlyMap<string, readonly Constraint[]>, constraint: Constraint): number {
  let found = 0;
  let visits = 0;
  const walk = (id: string, onPath: Set<string>): void => {
    if (found >= LOAD_CAP || visits >= WALK_CAP) return;
    for (const next of outgoing.get(id) ?? []) {
      if (next === constraint || onPath.has(next.to)) continue;
      visits += 1;
      if (next.to === constraint.from) {
        found += 1;
        continue;
      }
      onPath.add(next.to);
      walk(next.to, onPath);
      onPath.delete(next.to);
      if (found >= LOAD_CAP || visits >= WALK_CAP) return;
    }
  };
  walk(constraint.to, new Set([constraint.to]));
  return found;
}

/**
 * Drop the constraints that cannot hold at once, so the layering below is always a longest
 * path over a DAG.
 *
 * A document really can ask for the impossible: the demo declares `publication is-a
 * documented` *and* `reported_for: publication → documented`, so "left of what you inherit"
 * and "right of whatever points at you" close a loop — and `documented → related`, the
 * category's own `in` leg, closes a second loop through the same `reported_for` leg.
 *
 * So each round gives up the constraint that **carries the most loops**, which untangles
 * several cycles at once and so costs the fewest leftward arrows; an is-a step is only ever a
 * candidate when nothing weaker is on a cycle at all, which is what keeps the promise that x
 * never fights the hierarchy. Ties go to the weaker kind (a category's declaration before a
 * concrete flow leg) and then to the lexicographically greatest pair, so the choice is a
 * function of the constraint set alone, never of the order it arrived in.
 *
 * The link whose constraint was dropped is still drawn; it points leftwards, which shows the
 * cycle instead of hiding it.
 */
function acyclicConstraints(constraints: readonly Constraint[]): Constraint[] {
  let kept = [...constraints];
  for (;;) {
    const outgoing = outgoingOf(kept);
    const cyclic = cyclicConstraints(outgoing, kept);
    if (cyclic.length === 0) return kept;
    const expendable = cyclic.filter((constraint) => constraint.strength !== "is-a");
    const candidates = expendable.length > 0 ? expendable : cyclic;
    const loads = new Map(candidates.map((constraint) => [`${constraint.from}:${constraint.to}`, cycleLoad(outgoing, constraint)]));
    const drop = [...candidates].sort(
      (a, b) =>
        (loads.get(`${b.from}:${b.to}`) as number) - (loads.get(`${a.from}:${a.to}`) as number) ||
        GIVE_UP_FIRST[a.strength] - GIVE_UP_FIRST[b.strength] ||
        byId(b.from, a.from) ||
        byId(b.to, a.to),
    )[0] as Constraint;
    kept = kept.filter((constraint) => constraint !== drop);
  }
}

/**
 * Longest-path layering over the constraints: a card nothing points at sits in column 0 and
 * every card one column right of the deepest card that must precede it — which is what puts
 * a concrete edge card horizontally *between* the two node columns it joins while keeping
 * the is-a tree reading left to right.
 *
 * The set handed over is acyclic, so this terminates; the `walking` guard is defence in
 * depth for a caller that skips `acyclicConstraints`.
 */
function constraintLayers(ids: readonly string[], constraints: readonly Constraint[]): Map<string, number> {
  const upstream = new Map<string, Constraint[]>();
  for (const constraint of constraints) {
    const bucket = upstream.get(constraint.to);
    if (bucket) bucket.push(constraint);
    else upstream.set(constraint.to, [constraint]);
  }

  const layer = new Map<string, number>();
  const walking = new Set<string>();
  const depth = (id: string): number => {
    const settled = layer.get(id);
    if (settled !== undefined) return settled;
    if (walking.has(id)) return 0;
    walking.add(id);
    let deepest = 0;
    for (const constraint of upstream.get(id) ?? []) {
      deepest = Math.max(deepest, depth(constraint.from) + 1);
    }
    walking.delete(id);
    layer.set(id, deepest);
    return deepest;
  };

  // Sorted ids, so which card starts a walk cannot depend on the payload's order.
  for (const id of ids) depth(id);
  return layer;
}

/** Ids no constraint touches — they say nothing about depth, so they get a column of their
 * own after the last one rather than being scattered through the flow. */
function unconstrained(ids: readonly string[], constraints: readonly Constraint[]): string[] {
  const touched = new Set<string>();
  for (const constraint of constraints) {
    touched.add(constraint.from);
    touched.add(constraint.to);
  }
  return ids.filter((id) => !touched.has(id));
}

/** The average slot of the neighbours on the far side of `column`, or `null` to keep the
 * card where it is. Summing in id order keeps the total free of rounding drift. */
function centroidSlot(
  neighbours: ReadonlyMap<string, readonly string[]>,
  layer: ReadonlyMap<string, number>,
  slotOf: ReadonlyMap<string, number>,
  id: string,
  column: number,
  downwards: boolean,
): number | null {
  let total = 0;
  let weight = 0;
  for (const other of neighbours.get(id) ?? []) {
    const otherColumn = layer.get(other) ?? 0;
    if (downwards ? otherColumn >= column : otherColumn <= column) continue;
    const slot = slotOf.get(other);
    if (slot === undefined) continue;
    total += slot;
    weight += 1;
  }
  return weight === 0 ? null : total / weight;
}

/**
 * Deterministic left-to-right layout of the metagraph.
 *
 * `x` carries structure and it carries it in one direction: the constraints in
 * `layoutConstraints` (every is-a step, every concrete edge leg, and a category card's own
 * `in` leg) are turned into columns, so a relation reads source card → edge card → target
 * card along the horizontal axis and an is-a arrow never points backwards. Where the document
 * makes that impossible — a concrete edge aimed at a category node that is also an ancestor
 * of its own source — the is-a step holds and the weaker leg doubles back, visibly.
 *
 * `y` only spreads a column, ordered by one centroid sweep in each direction so a card sits
 * level with the cards it joins and the siblings of one category land next to each other.
 * Cards never overlap: columns are as wide as their widest card plus `COLUMN_GUTTER`, and a
 * column's cards are packed on a pitch of its tallest card plus `ROW_GUTTER`.
 *
 * Every coordinate is a non-negative multiple of `LAYOUT_GRID`, and the whole thing is a
 * pure function of the *sets* of vertices and links: the same graph handed over in any
 * order lays out the same way, which matters because a layout the user can trigger twice
 * must not move anything the second time.
 *
 * @param sizes the measured box of a card, defaulting to the size the card is styled to.
 * @returns vertex id → top-left point; `{}` for an empty graph.
 */
export function autoLayout(
  vertices: readonly VertexView[],
  links: readonly LinkView[],
  sizes?: (vertex: VertexView) => VertexSize,
): Record<string, Point> {
  const cards = new Map<string, VertexView>();
  for (const vertex of vertices) {
    if (vertex && !cards.has(vertex.id)) cards.set(vertex.id, vertex);
  }
  const ids = [...cards.keys()].sort(byId);
  if (ids.length === 0) return {};

  const sizeOf = (id: string): VertexSize => {
    const vertex = cards.get(id);
    if (!vertex) return DEFAULT_NODE_SIZE;
    const estimate = vertex.shape === "edge" ? DEFAULT_EDGE_SIZE : DEFAULT_NODE_SIZE;
    const given = sizes?.(vertex) ?? estimate;
    return {
      width: positive(given.width, estimate.width),
      height: positive(given.height, estimate.height),
    };
  };

  const idSet = new Set(ids);
  // Every link is a neighbour for the vertical sweep; only some of them are column
  // constraints, which is the split `layoutConstraints` makes.
  const legs = adjacency(idSet, links, (link) => link.kind !== "hierarchy");
  const hierarchy = adjacency(idSet, links, (link) => link.kind === "hierarchy");
  const constraints = acyclicConstraints(layoutConstraints(links, idSet));
  const layer = constraintLayers(ids, constraints);

  // A card no constraint touches — an unused edge category, a card whose endpoint dangles,
  // anything with nothing to say about depth — goes into a final column of its own rather
  // than being scattered through columns it has no business in.
  const spare = unconstrained(ids, constraints);
  if (spare.length > 0) {
    const deepest = ids.reduce((deepestSoFar, id) => Math.max(deepestSoFar, layer.get(id) ?? 0), 0);
    for (const id of spare) layer.set(id, deepest + 1);
  }

  const columns = new Map<number, string[]>();
  for (const id of ids) {
    const column = layer.get(id) ?? 0;
    const bucket = columns.get(column);
    if (bucket) bucket.push(id);
    else columns.set(column, [id]);
  }
  const ordered = [...columns.keys()].sort((a, b) => a - b);
  const slotOf = new Map<string, number>();
  for (const column of ordered) {
    (columns.get(column) as string[]).forEach((id, index) => slotOf.set(id, index));
  }

  const neighbours = neighboursOf(ids, legs, hierarchy);
  const sweep = (downwards: boolean): void => {
    for (const column of downwards ? ordered : [...ordered].reverse()) {
      const inColumn = columns.get(column) as string[];
      const keyed = inColumn.map((id) => ({
        id,
        key: centroidSlot(neighbours, layer, slotOf, id, column, downwards),
        before: slotOf.get(id) ?? 0,
      }));
      // A card with nothing to lean on keeps its slot; ties break on the slot it had and
      // then the id, both total orders.
      keyed.sort(
        (a, b) => (a.key ?? a.before) - (b.key ?? b.before) || a.before - b.before || byId(a.id, b.id),
      );
      keyed.forEach((entry, index) => {
        inColumn[index] = entry.id;
        slotOf.set(entry.id, index);
      });
    }
  };
  sweep(true);
  sweep(false);

  const boxes = new Map<number, { width: number; pitch: number; block: number }>();
  let tallest = 0;
  for (const column of ordered) {
    const inColumn = columns.get(column) as string[];
    const width = inColumn.reduce((widest, id) => Math.max(widest, sizeOf(id).width), 0);
    const height = inColumn.reduce((lowest, id) => Math.max(lowest, sizeOf(id).height), 0);
    const pitch = height + ROW_GUTTER;
    const block = (inColumn.length - 1) * pitch + height;
    boxes.set(column, { width, pitch, block });
    tallest = Math.max(tallest, block);
  }

  const out: Record<string, Point> = {};
  let cursor = 0;
  for (const column of ordered) {
    const inColumn = columns.get(column) as string[];
    const box = boxes.get(column) as { width: number; pitch: number; block: number };
    const x = snap(cursor);
    // Shorter columns hang off the same mid-line, so a lone card does not sit above
    // everything it is joined to.
    const top = snap((tallest - box.block) / 2);
    // Every card of a column shares its left edge — deliberately not centred on the column
    // width. Two cards in one column then have an identical `x`, so "this arrow points
    // leftwards" means "it goes to an earlier column" and nothing else, rather than being
    // true of an arrow between two cards that are as far right as each other.
    inColumn.forEach((id, index) => {
      out[id] = { x, y: snap(top + index * box.pitch) };
    });
    cursor = x + box.width + COLUMN_GUTTER;
  }
  return out;
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
