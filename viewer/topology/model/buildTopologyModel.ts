/**
 * Build the topology workbench model.
 *
 * Public API:
 *   buildTopologyModel(snapshot, index, { review?, audit?, decisions? })
 *
 * The model is DOM-free and is what the D3 function consumes.
 */

import { buildAudit } from "@/lib/audit";
import { deriveDecisions } from "@/lib/decisions";
import type {
  AuditFinding,
  AuditReport,
  DecisionStatus,
  DecisionView,
  ReviewSidecar,
  Severity,
} from "@/lib/reviewTypes";
import type {
  EntityKind,
  TopologyEdge,
  TopologyNode,
  ViewerIndex,
  ViewerSnapshot,
} from "@/lib/types";
import type {  BuildTopologyModelOptions,
  TopologyFindingSummary,
  TopologyFilters,
  TopologyFiltersModel,
  TopologyGraphModel,
  TopologyLinkModel,
  TopologyNodeModel,
  TopologySemanticsSummary,
} from "./TopologyGraphModel";
import { createTopologyFilters } from "./TopologyGraphModel";

type TopologyComponent = TopologyNode | TopologyEdge;

interface RawSemantics {
  claims?: unknown;
  frames?: unknown;
}

interface RawSemanticsText {
  text?: unknown;
  limitations?: unknown;
}

const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"];
const DECISION_RANK: Record<DecisionStatus, number> = {
  accepted: 1,
  waived: 2,
  proposed: 3,
  open: 4,
  rejected: 5,
};

function isObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function nonEmpty(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function humanize(value: string): string {
  const words = value
    .replace(/[_-]+/g, " ")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (!words.length) return value;
  return words
    .map((word, index) => {
      const lower = word.toLowerCase();
      return index === 0 ? lower.charAt(0).toUpperCase() + lower.slice(1) : lower;
    })
    .join(" ");
}

function emptySeverities(): Record<Severity, number> {
  return { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
}

function emptyFindings(): TopologyFindingSummary {
  return { total: 0, rules: [], severities: emptySeverities() };
}

function emptySemantics(): TopologySemanticsSummary {
  return {
    present: false,
    claimCount: 0,
    frameCount: 0,
    limitationCount: 0,
    claims: [],
    frames: [],
    limitations: [],
  };
}

function readSemantics(component: TopologyComponent): TopologySemanticsSummary {
  const raw = (component as { semantics?: unknown }).semantics;
  if (!isObject(raw)) return emptySemantics();
  const semantics = raw as RawSemantics;

  const claims: string[] = [];
  for (const item of Array.isArray(semantics.claims) ? semantics.claims : []) {
    if (isObject(item) && nonEmpty(item.text)) claims.push(item.text.trim());
  }

  const frames: string[] = [];
  const limitations: string[] = [];
  for (const item of Array.isArray(semantics.frames) ? semantics.frames : []) {
    if (!isObject(item)) continue;
    const frame = item as RawSemanticsText;
    if (nonEmpty(frame.text)) frames.push(frame.text.trim());
    for (const limitation of Array.isArray(frame.limitations)
      ? frame.limitations
      : []) {
      if (isObject(limitation) && nonEmpty(limitation.text)) {
        limitations.push(limitation.text.trim());
      }
    }
  }

  return {
    present: claims.length + frames.length + limitations.length > 0,
    claimCount: claims.length,
    frameCount: frames.length,
    limitationCount: limitations.length,
    claims,
    frames,
    limitations,
  };
}

function summarizeFindings(items: AuditFinding[]): TopologyFindingSummary {
  if (!items.length) return emptyFindings();
  const severities = emptySeverities();
  const rules = new Set<string>();
  let worst: Severity | undefined;
  for (const finding of items) {
    severities[finding.severity] += 1;
    rules.add(finding.rule);
    if (
      worst === undefined ||
      SEVERITY_ORDER.indexOf(finding.severity) < SEVERITY_ORDER.indexOf(worst)
    ) {
      worst = finding.severity;
    }
  }
  return {
    total: items.length,
    worst,
    rules: [...rules].sort((left, right) => left.localeCompare(right)),
    severities,
  };
}

function summarizeDecisions(items: DecisionView[]): {
  status?: DecisionStatus;
  statuses: DecisionStatus[];
  ids: string[];
} {
  if (!items.length) return { statuses: [], ids: [] };
  const statuses = [...new Set(items.map((item) => item.status))].sort(
    (left, right) =>
      DECISION_RANK[right] - DECISION_RANK[left] ||
      left.localeCompare(right),
  );
  return {
    status: statuses[0],
    statuses,
    ids: [...new Set(items.map((item) => item.id))].sort((left, right) =>
      left.localeCompare(right),
    ),
  };
}

function nodeId(name: string): string {
  return `topology:node:${name}`;
}

function edgeId(name: string): string {
  return `topology:edge:${name}`;
}

function containmentId(child: string, parent: string): string {
  return `topology:contains:${child}->${parent}`;
}

function parentName(component: TopologyComponent): string | undefined {
  const parent = component.parent?.at(-1);
  return parent && parent.trim() ? parent : undefined;
}

function componentLabel(
  index: ViewerIndex,
  component: TopologyComponent,
  kind: EntityKind,
): string {
  const meta = index.metaGraph?.byName.get(component.name);
  const match =
    meta?.find((entry) => entry.kind === kind && nonEmpty(entry.label)) ??
    meta?.find((entry) => nonEmpty(entry.label));
  if (match?.label) return match.label;
  const label = component.labels?.find((value) => nonEmpty(value));
  if (label) return label;
  return humanize(component.name);
}

function resolveSubject(
  subject: AuditFinding["subject"],
  index: ViewerIndex,
): { kind: EntityKind; name: string } | undefined {
  if (!subject) return undefined;
  const name = subject.component ?? subject.name;
  if (!name) return undefined;

  if (subject.kind === "node" && index.topologyNodesByName.has(name)) {
    return { kind: "node", name };
  }
  if (subject.kind === "edge" && index.topologyEdgesByName.has(name)) {
    return { kind: "edge", name };
  }
  if (subject.entityKind === "node" && index.topologyNodesByName.has(name)) {
    return { kind: "node", name };
  }
  if (subject.entityKind === "edge" && index.topologyEdgesByName.has(name)) {
    return { kind: "edge", name };
  }
  if (subject.kind === "property" || subject.kind === "binding") {
    if (index.topologyNodesByName.has(name)) return { kind: "node", name };
    if (index.topologyEdgesByName.has(name)) return { kind: "edge", name };
  }
  return undefined;
}

function entityKey(kind: EntityKind, name: string): string {
  return `${kind}\u0000${name}`;
}

function groupByEntity<T>(
  items: T[],
  resolve: (item: T) => { kind: EntityKind; name: string } | undefined,
): Map<string, T[]> {
  const grouped = new Map<string, T[]>();
  for (const item of items) {
    const target = resolve(item);
    if (!target) continue;
    const key = entityKey(target.kind, target.name);
    const bucket = grouped.get(key) ?? [];
    bucket.push(item);
    grouped.set(key, bucket);
  }
  return grouped;
}

function filterCounts(
  nodes: TopologyNodeModel[],
  edges: TopologyLinkModel[],
): TopologyFiltersModel["counts"] {
  const entities: Array<TopologyNodeModel | TopologyLinkModel> = [
    ...nodes,
    ...edges,
  ];
  const decision: Record<string, number> = {
    all: entities.length,
    none: entities.filter((entity) => !entity.decisionStatus).length,
    accepted: 0,
    waived: 0,
    proposed: 0,
    open: 0,
    rejected: 0,
  };
  for (const entity of entities) {
    if (entity.decisionStatus) {
      decision[entity.decisionStatus] = (decision[entity.decisionStatus] ?? 0) + 1;
    }
  }
  return {
    kinds: { node: nodes.length, edge: edges.length },
    abstract: {
      all: nodes.length,
      concrete: nodes.filter((node) => !node.abstract).length,
      abstract: nodes.filter((node) => node.abstract).length,
    },
    semantics: {
      all: entities.length,
      present: entities.filter((entity) => entity.hasSemantics).length,
      missing: entities.filter((entity) => !entity.hasSemantics).length,
    },
    findings: {
      all: entities.length,
      with: entities.filter((entity) => entity.findings.total > 0).length,
      without: entities.filter((entity) => entity.findings.total === 0).length,
    },
    decision,
  };
}

/**
 * Build the force-graph model from a loaded snapshot and its index.
 *
 * The builder is pure and deterministic for a given snapshot/index/review: ids,
 * labels, link endpoints, ordering and counts do not depend on time, layout or
 * DOM state.
 */
export function buildTopologyGraphModel(
  snapshot: ViewerSnapshot,
  index: ViewerIndex,
  options: BuildTopologyModelOptions = {},
): TopologyGraphModel {
  const audit =
    options.audit ??
    buildAudit(index, options.review);
  const decisions =
    options.decisions ??
    deriveDecisions(index, options.review);

  const findings = groupByEntity(audit.findings, (finding) =>
    resolveSubject(finding.subject, index),
  );
  const decisionGroups = groupByEntity(decisions, (decision) =>
    resolveSubject(decision.subject, index),
  );

  const components = index.topologyNodes ?? [];
  const edgeComponents = index.topologyEdges ?? [];
  const componentByName = new Map(
    components.map((component) => [component.name, component] as const),
  );

  const nodes: TopologyNodeModel[] = components.map((component) => {
    const label = componentLabel(index, component, "node");
    const semantics = readSemantics(component);
    const findingSummary = summarizeFindings(
      findings.get(entityKey("node", component.name)) ?? [],
    );
    const decisionSummary = summarizeDecisions(
      decisionGroups.get(entityKey("node", component.name)) ?? [],
    );
    const parent = parentName(component);
    return {
      id: nodeId(component.name),
      name: component.name,
      label,
      kind: "node",
      abstract: Boolean(component.abstract),
      degree: 0,
      relationDegree: 0,
      children: 0,
      category: parent ?? (component.abstract ? "root" : "uncategorized"),
      parent,
      labels: [...(component.labels ?? [])],
      description: component.description,
      properties: component.properties?.length ?? 0,
      annotations: component.annotations?.length ?? 0,
      hasSemantics: semantics.present,
      semantics,
      findings: findingSummary,
      decisionStatus: decisionSummary.status,
      decisionStatuses: decisionSummary.statuses,
      decisionIds: decisionSummary.ids,
    };
  });
  const byName = new Map(nodes.map((node) => [node.name, node] as const));

  const edgeLinks: TopologyLinkModel[] = [];
  for (const component of edgeComponents) {
    const sourceName = component.source?.at(-1);
    const targetName = component.target?.at(-1);
    if (
      !sourceName ||
      !targetName ||
      !byName.has(sourceName) ||
      !byName.has(targetName)
    ) {
      continue;
    }
    const semantics = readSemantics(component);
    const findingSummary = summarizeFindings(
      findings.get(entityKey("edge", component.name)) ?? [],
    );
    const decisionSummary = summarizeDecisions(
      decisionGroups.get(entityKey("edge", component.name)) ?? [],
    );
    const parent = parentName(component);
    edgeLinks.push({
      id: edgeId(component.name),
      name: component.name,
      label: componentLabel(index, component, "edge"),
      kind: "edge",
      source: nodeId(sourceName),
      target: nodeId(targetName),
      sourceName,
      targetName,
      directed: true,
      abstract: Boolean(component.abstract),
      category: parent ?? "relationship",
      parent,
      labels: [...(component.labels ?? [])],
      description: component.description,
      hasSemantics: semantics.present,
      semantics,
      findings: findingSummary,
      decisionStatus: decisionSummary.status,
      decisionStatuses: decisionSummary.statuses,
      decisionIds: decisionSummary.ids,
      edgeName: component.name,
    });
  }

  const containmentLinks: TopologyLinkModel[] = [];
  for (const node of nodes) {
    if (!node.parent || !byName.has(node.parent)) continue;
    const parent = byName.get(node.parent)!;
    containmentLinks.push({
      id: containmentId(node.name, parent.name),
      name: `is_a:${node.name}`,
      label: `in ${parent.label}`,
      kind: "containment",
      source: node.id,
      target: parent.id,
      sourceName: node.name,
      targetName: parent.name,
      directed: true,
      abstract: false,
      category: "containment",
      parent: parent.name,
      labels: [],
      hasSemantics: false,
      semantics: emptySemantics(),
      findings: emptyFindings(),
      decisionStatuses: [],
      decisionIds: [],
    });
  }

  for (const link of edgeLinks) {
    const source = byName.get(link.sourceName);
    const target = byName.get(link.targetName);
    if (source) {
      source.degree += 1;
      source.relationDegree += 1;
    }
    if (target) {
      target.degree += 1;
      target.relationDegree += 1;
    }
  }
  for (const link of containmentLinks) {
    const source = byName.get(link.sourceName);
    const target = byName.get(link.targetName);
    if (source) source.degree += 1;
    if (target) {
      target.degree += 1;
      target.children += 1;
    }
  }

  const links = [...edgeLinks, ...containmentLinks];
  nodes.sort((left, right) => left.id.localeCompare(right.id));
  links.sort((left, right) => left.id.localeCompare(right.id));

  const entities: Array<TopologyNodeModel | TopologyLinkModel> = [
    ...nodes,
    ...edgeLinks,
  ];
  const graphKey = `${snapshot.name}:${nodes.length}:${edgeLinks.length}:${containmentLinks.length}`;
  const stats = {
    nodes: nodes.length,
    abstractNodes: nodes.filter((node) => node.abstract).length,
    edgeLinks: edgeLinks.length,
    containmentLinks: containmentLinks.length,
    links: links.length,
    semantics: entities.filter((entity) => entity.hasSemantics).length,
    findings: entities.reduce((total, entity) => total + entity.findings.total, 0),
    decisions: entities.reduce(
      (total, entity) => total + entity.decisionIds.length,
      0,
    ),
  };

  return {
    id: "topology",
    snapshot: snapshot.name,
    graphKey,
    nodes,
    links,
    filters: {
      defaultState: createTopologyFilters(),
      counts: filterCounts(nodes, edgeLinks),
    },
    stats,
    nodeById: new Map(nodes.map((node) => [node.id, node] as const)),
    linkById: new Map(links.map((link) => [link.id, link] as const)),
  };
}


function isViewerIndex(value: unknown): value is ViewerIndex {
  return Boolean(
    value &&
      typeof value === "object" &&
      "topologyNodesByName" in value &&
      "topologyEdgesByName" in value,
  );
}

export function buildTopologyModel(
  snapshot: ViewerSnapshot,
  index: ViewerIndex,
  options: BuildTopologyModelOptions = {},
): TopologyGraphModel {
  return buildTopologyGraphModel(snapshot, index, options);
}

export type { TopologyFilters };
