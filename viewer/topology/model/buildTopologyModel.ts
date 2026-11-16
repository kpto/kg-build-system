/**
 * Build the topology workbench model.
 *
 * Public API:
 *   buildTopologyModel(snapshot, index, { containment? })
 *
 * The model is DOM-free and is what the D3 function consumes. It carries only
 * design data: graph structure, labels, degree, category containment, semantics
 * presence and property counts.
 */

import type {
  EntityKind,
  TopologyEdge,
  TopologyNode,
  ViewerIndex,
  ViewerSnapshot,
} from "@/lib/types";
import { meaningText } from "@/lib/summary";
import type {
  BuildTopologyModelOptions,
  TopologyDetailOptions,
  TopologyFilters,
  TopologyFiltersModel,
  TopologyGraphModel,
  TopologyLinkModel,
  TopologyNodeModel,
  TopologySemanticsSummary,
} from "./TopologyGraphModel";
import {
  createTopologyDetail,
  createTopologyFilters,
} from "./TopologyGraphModel";

type TopologyComponent = TopologyNode | TopologyEdge;

interface RawSemantics {
  purpose?: unknown;
  claims?: unknown;
}

interface RawSemanticsText {
  text?: unknown;
  limitations?: unknown;
}

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

function emptySemantics(): TopologySemanticsSummary {
  return {
    present: false,
    claimCount: 0,
    purposePresent: false,
    limitationCount: 0,
  };
}

function readSemantics(component: TopologyComponent): TopologySemanticsSummary {
  const raw =
    (component as { meaning?: unknown; semantics?: unknown }).meaning ??
    (component as { semantics?: unknown }).semantics;
  if (!isObject(raw)) return emptySemantics();
  const semantics = raw as RawSemantics;

  let claimCount = 0;
  for (const item of Array.isArray(semantics.claims) ? semantics.claims : []) {
    if (isObject(item) && nonEmpty(item.text)) claimCount += 1;
  }

  let purposePresent = false;
  let limitationCount = 0;
  if (isObject(semantics.purpose)) {
    const purpose = semantics.purpose as RawSemanticsText;
    if (nonEmpty(purpose.text)) purposePresent = true;
    for (const limitation of Array.isArray(purpose.limitations)
      ? purpose.limitations
      : []) {
      if (isObject(limitation) && nonEmpty(limitation.text)) {
        limitationCount += 1;
      }
    }
  }

  return {
    present: claimCount + (purposePresent ? 1 : 0) + limitationCount > 0,
    claimCount,
    purposePresent,
    limitationCount,
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

function filterCounts(
  nodes: TopologyNodeModel[],
  edges: TopologyLinkModel[],
): TopologyFiltersModel["counts"] {
  const entities: Array<TopologyNodeModel | TopologyLinkModel> = [
    ...nodes,
    ...edges,
  ];
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
  };
}

/**
 * Build the force-graph model from a loaded snapshot and its index.
 *
 * The builder is pure and deterministic for a given snapshot/index: ids,
 * labels, link endpoints, ordering and counts do not depend on time, layout,
 * detail switches or DOM state.
 */
export function buildTopologyGraphModel(
  snapshot: ViewerSnapshot,
  index: ViewerIndex,
  options: BuildTopologyModelOptions = {},
): TopologyGraphModel {
  const includeContainment = options.containment ?? true;

  const components = index.topologyNodes ?? [];
  const edgeComponents = index.topologyEdges ?? [];

  const nodes: TopologyNodeModel[] = components.map((component) => {
    const label = componentLabel(index, component, "node");
    const semantics = readSemantics(component);
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
      description:
        meaningText(component.meaning ?? component.semantics) ??
        component.description,
      properties: component.properties?.length ?? 0,
      hasSemantics: semantics.present,
      semantics,
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
      description:
        meaningText(component.meaning ?? component.semantics) ??
        component.description,
      hasSemantics: semantics.present,
      semantics,
      edgeName: component.name,
    });
  }

  const containmentLinks: TopologyLinkModel[] = [];
  if (includeContainment) {
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
      });
    }
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
  };

  const detail: TopologyDetailOptions = createTopologyDetail();

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
    detail,
    stats,
    nodeById: new Map(nodes.map((node) => [node.id, node] as const)),
    linkById: new Map(links.map((link) => [link.id, link] as const)),
  };
}

export function buildTopologyModel(
  snapshot: ViewerSnapshot,
  index: ViewerIndex,
  options: BuildTopologyModelOptions = {},
): TopologyGraphModel {
  return buildTopologyGraphModel(snapshot, index, options);
}

export type { TopologyFilters };
