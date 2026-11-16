/**
 * In-memory topology model for the D3 workbench function.
 *
 * The model owns the design graph: stable identities, labels, degree, category
 * containment, attached meaning and property counts. It is a pure
 * visualisation model; coordinates, hover, applied filters and detail switches
 * stay in the view.
 *
 * This is deliberately not a DTO: it contains maps and derived values and is
 * never serialised. The snapshot DTOs remain the source of truth.
 */

export type TopologyEntityKind = "node" | "edge";
export type TopologyLinkKind = "edge" | "containment";
export type TopologyAbstractFilter = "all" | "concrete" | "abstract";
export type TopologySemanticsFilter = "all" | "present" | "missing";
export type TopologyLabelDetail = "off" | "hubs" | "all";
export type TopologyEdgeDetail = "off" | "relations";

/** What a node or relation says about itself. */
export interface TopologySemanticsSummary {
  present: boolean;
  claimCount: number;
  purposePresent: boolean;
  limitationCount: number;
}

export interface TopologyNodeModel {
  id: string;
  name: string;
  label: string;
  /** Topology node components are the entity nodes of the force graph. */
  kind: "node";
  abstract: boolean;
  degree: number;
  relationDegree: number;
  children: number;
  category: string;
  parent?: string;
  labels: string[];
  description?: string;
  /** Number of declared properties. */
  properties: number;
  hasSemantics: boolean;
  semantics: TopologySemanticsSummary;
}

export interface TopologyLinkModel {
  id: string;
  name: string;
  label: string;
  /** Relationship links are topology edge components; containment is structure. */
  kind: TopologyLinkKind;
  /** Node ids, not names. */
  source: string;
  target: string;
  sourceName: string;
  targetName: string;
  directed: boolean;
  abstract: boolean;
  category: string;
  parent?: string;
  labels: string[];
  description?: string;
  hasSemantics: boolean;
  semantics: TopologySemanticsSummary;
  /** Present only on relationship links. */
  edgeName?: string;
}

export interface TopologyFilters {
  kinds: {
    node: boolean;
    edge: boolean;
  };
  abstract: TopologyAbstractFilter;
  semantics: TopologySemanticsFilter;
}

export interface TopologyFilterCounts {
  kinds: { node: number; edge: number };
  abstract: Record<TopologyAbstractFilter, number>;
  semantics: Record<TopologySemanticsFilter, number>;
}

export interface TopologyFiltersModel {
  defaultState: TopologyFilters;
  counts: TopologyFilterCounts;
}

/**
 * How much of the design graph is drawn.
 *
 * The defaults are the low-detail view: circles, thin relation links and labels
 * only for the busiest nodes. Containment, semantics and properties are opt-in.
 */
export interface TopologyDetailOptions {
  labels: TopologyLabelDetail;
  edgeLabels: boolean;
  containment: boolean;
  semantics: boolean;
  properties: boolean;
  clusters: boolean;
  edges: TopologyEdgeDetail;
}

export interface TopologyModelStats {
  nodes: number;
  abstractNodes: number;
  edgeLinks: number;
  containmentLinks: number;
  links: number;
  semantics: number;
}

export interface TopologyGraphModel {
  id: "topology";
  snapshot: string;
  graphKey: string;
  nodes: TopologyNodeModel[];
  links: TopologyLinkModel[];
  filters: TopologyFiltersModel;
  detail: TopologyDetailOptions;
  stats: TopologyModelStats;
  nodeById: Map<string, TopologyNodeModel>;
  linkById: Map<string, TopologyLinkModel>;
}

export interface TopologyVisibleGraph {
  nodes: TopologyNodeModel[];
  links: TopologyLinkModel[];
  hiddenNodes: number;
  hiddenLinks: number;
}

export interface TopologySelection {
  kind: TopologyEntityKind;
  name: string;
}

export type TopologyEntity = TopologyNodeModel | TopologyLinkModel;

export interface BuildTopologyModelOptions {
  /** Include child -> parent category links. The view hides them by default. */
  containment?: boolean;
}

export function createTopologyFilters(): TopologyFilters {
  return {
    kinds: { node: true, edge: true },
    abstract: "all",
    semantics: "all",
  };
}

export function cloneTopologyFilters(filters: TopologyFilters): TopologyFilters {
  return {
    kinds: { ...filters.kinds },
    abstract: filters.abstract,
    semantics: filters.semantics,
  };
}

export function createTopologyDetail(): TopologyDetailOptions {
  return {
    labels: "hubs",
    edgeLabels: false,
    containment: false,
    semantics: false,
    properties: false,
    clusters: true,
    edges: "relations",
  };
}

export function cloneTopologyDetail(
  detail: TopologyDetailOptions,
): TopologyDetailOptions {
  return { ...detail };
}

function matchesAbstract(
  value: boolean,
  filter: TopologyAbstractFilter,
): boolean {
  if (filter === "all") return true;
  return filter === "concrete" ? !value : value;
}

function matchesSemantics(
  value: boolean,
  filter: TopologySemanticsFilter,
): boolean {
  if (filter === "all") return true;
  return filter === "present" ? value : !value;
}

function statusVisible(
  entity: TopologyNodeModel | TopologyLinkModel,
  filters: TopologyFilters,
): boolean {
  return (
    matchesAbstract(entity.abstract, filters.abstract) &&
    matchesSemantics(entity.hasSemantics, filters.semantics)
  );
}

/**
 * Apply the sidebar filters and the detail switches without touching the model.
 *
 * Node status filters decide which entities are eligible. The node kind switch
 * hides node markers; the edge kind switch and the `edges` detail switch hide
 * relationship links. Containment links follow both the node switch and the
 * `containment` detail switch. When node markers are off but relations are on,
 * endpoint nodes stay in the visible graph so links still have geometry.
 */
export function applyTopologyFilters(
  model: TopologyGraphModel,
  filters: TopologyFilters,
  detail: TopologyDetailOptions = model.detail,
): TopologyVisibleGraph {
  if (!filters.kinds.node && !filters.kinds.edge) {
    return {
      nodes: [],
      links: [],
      hiddenNodes: model.nodes.length,
      hiddenLinks: model.links.length,
    };
  }

  const eligibleNodes = model.nodes.filter((node) => statusVisible(node, filters));
  const eligibleIds = new Set(eligibleNodes.map((node) => node.id));

  const relationLinks =
    filters.kinds.edge && detail.edges === "relations"
      ? model.links.filter(
          (link) =>
            link.kind === "edge" &&
            statusVisible(link, filters) &&
            eligibleIds.has(link.source) &&
            eligibleIds.has(link.target),
        )
      : [];

  const containmentLinks =
    filters.kinds.node && detail.containment
      ? model.links.filter(
          (link) =>
            link.kind === "containment" &&
            eligibleIds.has(link.source) &&
            eligibleIds.has(link.target),
        )
      : [];

  let nodes: TopologyNodeModel[];
  if (filters.kinds.node) {
    nodes = eligibleNodes;
  } else {
    const endpoints = new Set<string>();
    for (const link of relationLinks) {
      endpoints.add(link.source);
      endpoints.add(link.target);
    }
    nodes = eligibleNodes.filter((node) => endpoints.has(node.id));
  }

  const visibleIds = new Set(nodes.map((node) => node.id));
  const links = [...relationLinks, ...containmentLinks].filter(
    (link) => visibleIds.has(link.source) && visibleIds.has(link.target),
  );

  return {
    nodes,
    links,
    hiddenNodes: model.nodes.length - nodes.length,
    hiddenLinks: model.links.length - links.length,
  };
}

/** Find the entity named by a workbench selection. */
export function findTopologyEntity(
  model: TopologyGraphModel,
  selection: TopologySelection | undefined,
): TopologyEntity | undefined {
  if (!selection) return undefined;
  if (selection.kind === "node") {
    return (
      model.nodeById.get(selection.name) ??
      model.nodes.find((node) => node.name === selection.name)
    );
  }
  return (
    model.linkById.get(selection.name) ??
    model.links.find(
      (link) =>
        link.kind === "edge" && (link.edgeName ?? link.name) === selection.name,
    )
  );
}

export function isTopologyNode(
  entity: TopologyEntity | undefined,
): entity is TopologyNodeModel {
  return entity?.kind === "node";
}
