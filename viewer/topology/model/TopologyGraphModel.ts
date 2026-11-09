/**
 * In-memory topology model for the D3 workbench function.
 *
 * The model owns the graph itself: stable identities, labels, degree, category
 * containment, attached semantics and the review/audit status of every entity.
 * Coordinates, hover, filters-as-applied and the simulation stay in the view.
 *
 * This is deliberately not a DTO: it contains maps and derived values and is
 * never serialised. The snapshot DTOs remain the source of truth.
 */

import type {
  AuditReport,
  DecisionStatus,
  DecisionView,
  ReviewSidecar,
  Severity,
} from "@/lib/reviewTypes";

export type TopologyEntityKind = "node" | "edge";
export type TopologyLinkKind = "edge" | "containment";
export type TopologyAbstractFilter = "all" | "concrete" | "abstract";
export type TopologySemanticsFilter = "all" | "present" | "missing";
export type TopologyFindingsFilter = "all" | "with" | "without";
export type TopologyDecisionFilter = "all" | "none" | DecisionStatus;

export interface TopologySemanticsSummary {
  present: boolean;
  claimCount: number;
  frameCount: number;
  limitationCount: number;
  claims: string[];
  frames: string[];
  limitations: string[];
}

export interface TopologyFindingSummary {
  total: number;
  worst?: Severity;
  rules: string[];
  severities: Record<Severity, number>;
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
  properties: number;
  annotations: number;
  hasSemantics: boolean;
  semantics: TopologySemanticsSummary;
  findings: TopologyFindingSummary;
  decisionStatus?: DecisionStatus;
  decisionStatuses: DecisionStatus[];
  decisionIds: string[];
}

export interface TopologyLinkModel {
  id: string;
  name: string;
  label: string;
  /** Relationship links are topology edge components; containment is category structure. */
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
  findings: TopologyFindingSummary;
  decisionStatus?: DecisionStatus;
  decisionStatuses: DecisionStatus[];
  decisionIds: string[];
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
  findings: TopologyFindingsFilter;
  decision: TopologyDecisionFilter;
}

export interface TopologyFilterCounts {
  kinds: { node: number; edge: number };
  abstract: Record<TopologyAbstractFilter, number>;
  semantics: Record<TopologySemanticsFilter, number>;
  findings: Record<TopologyFindingsFilter, number>;
  decision: Record<string, number>;
}

export interface TopologyFiltersModel {
  defaultState: TopologyFilters;
  counts: TopologyFilterCounts;
}

export interface TopologyModelStats {
  nodes: number;
  abstractNodes: number;
  edgeLinks: number;
  containmentLinks: number;
  links: number;
  semantics: number;
  findings: number;
  decisions: number;
}

export interface TopologyGraphModel {
  id: "topology";
  snapshot: string;
  graphKey: string;
  nodes: TopologyNodeModel[];
  links: TopologyLinkModel[];
  filters: TopologyFiltersModel;
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
  review?: ReviewSidecar;
  audit?: AuditReport;
  decisions?: DecisionView[];
}

export function createTopologyFilters(): TopologyFilters {
  return {
    kinds: { node: true, edge: true },
    abstract: "all",
    semantics: "all",
    findings: "all",
    decision: "all",
  };
}

export function cloneTopologyFilters(filters: TopologyFilters): TopologyFilters {
  return {
    kinds: { ...filters.kinds },
    abstract: filters.abstract,
    semantics: filters.semantics,
    findings: filters.findings,
    decision: filters.decision,
  };
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

function matchesFindings(
  value: TopologyFindingSummary,
  filter: TopologyFindingsFilter,
): boolean {
  if (filter === "all") return true;
  return filter === "with" ? value.total > 0 : value.total === 0;
}

function matchesDecision(
  value: DecisionStatus | undefined,
  filter: TopologyDecisionFilter,
): boolean {
  if (filter === "all") return true;
  if (filter === "none") return value === undefined;
  return value === filter;
}

function statusVisible(
  entity: TopologyNodeModel | TopologyLinkModel,
  filters: TopologyFilters,
): boolean {
  return (
    matchesAbstract(entity.abstract, filters.abstract) &&
    matchesSemantics(entity.hasSemantics, filters.semantics) &&
    matchesFindings(entity.findings, filters.findings) &&
    matchesDecision(entity.decisionStatus, filters.decision)
  );
}

/**
 * Apply the sidebar filters without touching the model.
 *
 * Node status filters decide which entities are eligible. The node kind switch
 * hides node markers; the edge kind switch hides relationship links. Containment
 * links follow the node switch because they describe category structure rather
 * than relations. When node markers are off but relations are on, endpoint
 * nodes stay in the visible graph so links still have geometry.
 */
export function applyTopologyFilters(
  model: TopologyGraphModel,
  filters: TopologyFilters,
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

  const relationLinks = filters.kinds.edge
    ? model.links.filter(
        (link) =>
          link.kind === "edge" &&
          statusVisible(link, filters) &&
          eligibleIds.has(link.source) &&
          eligibleIds.has(link.target),
      )
    : [];

  const containmentLinks = filters.kinds.node
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
      (link) => link.kind === "edge" && (link.edgeName ?? link.name) === selection.name,
    )
  );
}

export function isTopologyNode(
  entity: TopologyEntity | undefined,
): entity is TopologyNodeModel {
  return entity?.kind === "node";
}
