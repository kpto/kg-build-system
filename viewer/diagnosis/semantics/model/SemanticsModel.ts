import type { CampaignView } from "@/shared/model/campaign";
import type { ActionModel, FieldModel, IconToken } from "@/shared/model/hierarchy";
import type {
  AuditFinding,
  AuditReport,
  AuditSubject,
  Severity,
} from "@/lib/reviewTypes";
import type {
  AnnotationDTO,
  EntityKind,
  Expression,
  MetaGraphIndex,
  TopologyEdge,
  TopologyNode,
  TopologyProperty,
  ViewerIndex,
} from "@/lib/types";
import {
  findComponentPropertyBindings,
  relationNamesFromRowSource,
} from "@/lib/indexes";
import { collectFieldRefs, fieldRefKey, walkExpression } from "@/lib/expressions";
import { componentImpact } from "@/lib/impact";
import { subjectFromSelection } from "@/diagnosis/model/selection";

export type SemanticsMode = "graph" | "cards";

export type SemanticsBadgeKind =
  | "traced"
  | "literal"
  | "fallback"
  | "multi-source"
  | "risk"
  | "impact";

export interface SemanticsBadgeModel {
  id: string;
  label: string;
  kind: SemanticsBadgeKind;
  title: string;
  /** Severity is data; the view owns the colour. */
  severity?: Severity;
  /** The numeric count behind a risk or impact badge; absent for status. */
  value?: number;
}

export interface SemanticsLegendEntryModel {
  id: SemanticsBadgeKind;
  label: string;
  meaning: string;
  kind: SemanticsBadgeKind;
}

export interface PropertySourceSummary {
  sources: string[];
  bindings: number[];
}

export interface SemanticsPropertyRowModel {
  id: string;
  kind: EntityKind;
  component: string;
  name: string;
  description?: string;
  annotations: AnnotationDTO[];
  /** The source field: source relation names and the backing binding indexes. */
  source: FieldModel;
  /** The declared value type, when the blueprint records one. */
  typeLabel?: string;
  bindings: number[];
  badges: SemanticsBadgeModel[];
  selected: boolean;
  actions: ActionModel[];
}

export interface SemanticsEntityModel {
  /** React Flow node id: topology:node:<name> or topology:edge:<name>. */
  id: string;
  /** Card index key: <kind>:<name>. */
  key: string;
  kind: EntityKind;
  name: string;
  labels: string[];
  description: string;
  abstract: boolean;
  propertyCount: number;
  properties: SemanticsPropertyRowModel[];
  annotations: AnnotationDTO[];
  /** The entity itself is the selected subject. */
  selected: boolean;
  /** The entity or one of its properties is the selected subject. */
  highlighted: boolean;
  /** Index into the shared group palette. */
  paletteIndex: number;
  actions: ActionModel[];
}

export interface SemanticsGroupModel {
  id: string;
  parent: string;
  title: string;
  question: string;
  count: number;
  propertyCount: number;
  paletteIndex: number;
  entities: SemanticsEntityModel[];
}

export interface SemanticsCardsModel {
  id: "semantics-cards";
  question: string;
  /** Changes only when the underlying blueprint changes. */
  sourceKey: string;
  groups: SemanticsGroupModel[];
  entityCount: number;
  propertyCount: number;
  groupCount: number;
  focusGroupId?: string;
  defaultCollapsedGroupIds: string[];
  empty: { title: string; hint: string } | null;
}

export interface SemanticsCanvasEdgeModel {
  id: string;
  source: string;
  target: string;
  label: "source" | "target";
  name: string;
  role: "source" | "target";
  /** Overrides the generated wire test id when the connector is aggregated. */
  testId?: string;
  active: boolean;
  dimmed: boolean;
}

export interface SemanticsEdgeGroupModel {
  /** React Flow id: one card for every edge that shares a source/target pair. */
  id: string;
  /** The relationship role: the shared parent edge name, or `relationship`. */
  role: string;
  sourceId: string;
  targetId: string;
  sourceName: string;
  targetName: string;
  /** Every individual edge name represented by this grouped card. */
  edgeNames: string[];
  paletteIndex: number;
  selected: boolean;
  highlighted: boolean;
  active: boolean;
  dimmed: boolean;
}

export interface SemanticsGraphFocusModel {
  groupId: string;
  /** Rendered React Flow ids, including grouped cards. */
  nodeIds: string[];
  /** Focused node entities. */
  nodeCards: SemanticsEntityModel[];
  /** Focused edge entities that remain individual cards. */
  edgeCards: SemanticsEntityModel[];
  /** Focused edge cards aggregated by source/target pair. */
  edgeGroups: SemanticsEdgeGroupModel[];
  nodeCount: number;
  /** Rendered edge-card nodes: ungrouped edges plus grouped cards. */
  edgeCardCount: number;
  /** Individual relationship edges represented in the focused composition. */
  edgeRelationshipCount: number;
  edgeGroupCount: number;
  groupedEdgeCount: number;
  edges: SemanticsCanvasEdgeModel[];
}

export interface SemanticsGraphModel {
  id: "semantics-graph";
  question: string;
  entityCards: SemanticsEntityModel[];
  edgeCards: SemanticsEntityModel[];
  edges: SemanticsCanvasEdgeModel[];
  selectedSubject?: AuditSubject;
  focus: SemanticsGraphFocusModel | null;
  whole: { entityCount: number; edgeCount: number };
}

export interface SemanticsOverlayModeModel {
  id: SemanticsMode;
  label: string;
  icon: IconToken;
}

export interface SemanticsOverlayModel {
  id: "semantics-overlay";
  label: string;
  modes: SemanticsOverlayModeModel[];
  defaultMode: SemanticsMode;
  wholeGraph: {
    label: string;
    focusLabel: string;
    title: string;
    focusTitle: string;
  };
  auditKey: {
    label: string;
    title: string;
    legend: SemanticsLegendEntryModel[];
  };
  hints: {
    cards: string;
    graph: string;
    wholeGraph: string;
  };
  counts: {
    wholeLabel: string;
    focusLabel: string;
    wholeNodes: number;
    wholeEdges: number;
    focusNodes: number;
    focusEdgeCards: number;
    focusEdgeRelationships: number;
    focusEdgeGroups: number;
    focusGroupedEdges: number;
    totalEntities: number;
    totalProperties: number;
  };
  scaleHint: {
    visible: boolean;
    wholeTitle: string;
    focusTitle: string;
    wholeChip: string;
    focusChip: string;
  };
}

export interface SemanticsCommands {
  openLineage: (kind: EntityKind, component: string, property: string) => void;
  openReview: (subject: AuditSubject) => void;
  selectEntity: (kind: EntityKind, name: string) => void;
}

export interface SemanticsModel {
  id: "semantics";
  question: string;
  metaGraph: MetaGraphIndex;
  cards: SemanticsCardsModel;
  graph: SemanticsGraphModel;
  overlay: SemanticsOverlayModel;
  commands: SemanticsCommands;
}

/**
 * The campaign-free input of the semantics builder.
 *
 * It exists for the legacy shell, which still supplies the three callbacks it
 * owns, and for tests. A campaign view is the normal entry point.
 */
export interface SemanticsSource {
  index: ViewerIndex;
  audit?: AuditReport;
  selectedSubject?: AuditSubject;
  onSelectProperty?: (
    kind: EntityKind,
    component: string,
    property: string,
  ) => void;
  onOpenReview?: (subject: AuditSubject) => void;
  onSelectEntity?: (kind: EntityKind, name: string) => void;
}

const LARGE_BLUEPRINT_THRESHOLD = 100;
const LARGE_GRID_THRESHOLD = 120;
const FALLBACK_OPERATORS = new Set(["coalesce", "default_to"]);
const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"];

const BADGE_LEGEND: SemanticsLegendEntryModel[] = [
  {
    id: "traced",
    label: "traced",
    meaning: "expression reads a source field",
    kind: "traced",
  },
  {
    id: "literal",
    label: "literal",
    meaning: "hard-coded value in the expression",
    kind: "literal",
  },
  {
    id: "fallback",
    label: "fallback",
    meaning: "coalesce / default_to literal",
    kind: "fallback",
  },
  {
    id: "multi-source",
    label: "multi-source",
    meaning: "branches read more than one relation",
    kind: "multi-source",
  },
  {
    id: "risk",
    label: "risk",
    meaning: "audit findings target this property",
    kind: "risk",
  },
  {
    id: "impact",
    label: "impact",
    meaning: "upstream + downstream steps affected",
    kind: "impact",
  },
];

interface TopologyItem {
  kind: EntityKind;
  name: string;
  labels: string[];
  description?: string;
  abstract: boolean;
  properties: TopologyProperty[];
  annotations: AnnotationDTO[];
  parent?: string[];
}

interface GroupSeed {
  parent: string;
  paletteIndex: number;
  items: TopologyItem[];
}

function topologyItemFromNode(node: TopologyNode): TopologyItem {
  return {
    kind: "node",
    name: node.name,
    labels: node.labels ?? [],
    description: node.description,
    abstract: Boolean(node.abstract),
    properties: node.properties ?? [],
    annotations: node.annotations ?? [],
    parent: node.parent,
  };
}

function topologyItemFromEdge(edge: TopologyEdge): TopologyItem {
  return {
    kind: "edge",
    name: edge.name,
    labels: edge.labels ?? [],
    description: edge.description,
    abstract: Boolean(edge.abstract),
    properties: edge.properties ?? [],
    annotations: edge.annotations ?? [],
    parent: edge.parent,
  };
}

/** Last parent ref segment; a missing parent is the explicit fallback group. */
function parentGroup(item: TopologyItem): string {
  const parent = item.parent?.at(-1);
  return parent && parent.trim() ? parent : "uncategorized";
}

/**
 * Deterministic parent groups: each group is a section, each item an entity row
 * group. Group order is lexical; item order is name then kind.
 */
function groupSeeds(index: ViewerIndex): GroupSeed[] {
  const groups = new Map<string, TopologyItem[]>();
  const items = [
    ...index.topologyNodes.map(topologyItemFromNode),
    ...index.topologyEdges.map(topologyItemFromEdge),
  ];
  for (const item of items) {
    const parent = parentGroup(item);
    const group = groups.get(parent) ?? [];
    group.push(item);
    groups.set(parent, group);
  }

  return [...groups.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([parent, group], paletteIndex) => ({
      parent,
      paletteIndex,
      items: [...group].sort(
        (left, right) =>
          left.name.localeCompare(right.name) ||
          left.kind.localeCompare(right.kind),
      ),
    }));
}

function entityKey(item: TopologyItem): string {
  return `${item.kind}:${item.name}`;
}

function entityId(item: TopologyItem): string {
  return `topology:${item.kind}:${item.name}`;
}

function matchesSelectedSubject(
  selected: AuditSubject | undefined,
  kind: EntityKind,
  name: string,
): boolean {
  if (!selected) return false;
  const subjectName = selected.component ?? selected.name;
  if (selected.kind === kind && subjectName === name) return true;
  if (
    selected.kind === "property" &&
    subjectName === name &&
    (!selected.entityKind || selected.entityKind === kind)
  ) {
    return true;
  }
  return false;
}

function matchesSelectedProperty(
  selected: AuditSubject | undefined,
  kind: EntityKind,
  component: string,
  property: string,
): boolean {
  if (!selected || selected.kind !== "property") return false;
  return (
    (selected.component ?? selected.name) === component &&
    selected.property === property &&
    (!selected.entityKind || selected.entityKind === kind)
  );
}

function resolvedSources(index: ViewerIndex, name: string): string[] {
  if (!name) return [];
  const projection = index.projectionByName.get(name);
  if (projection) {
    const sources = relationNamesFromRowSource(projection.row_source);
    if (sources.length) return sources;
  }
  return [name];
}

/**
 * Name the source relations and binding indexes that feed one property.
 *
 * A property expression references a field owned by a projection. The reviewer
 * needs the underlying table, not the projection, so a projection owner is
 * resolved through its row source.
 */
export function propertySourceSummary(
  index: ViewerIndex,
  kind: EntityKind,
  component: string,
  property: string,
): PropertySourceSummary {
  const entries = findComponentPropertyBindings(
    index,
    kind,
    component,
    property,
  );
  const sources = new Set<string>();
  for (const entry of entries) {
    for (const ref of entry.fieldRefs) {
      const key = fieldRefKey(ref);
      const owner =
        index.fieldsByKey.get(key)?.ownerName ?? key.split(".")[0] ?? "";
      for (const source of resolvedSources(index, owner)) sources.add(source);
    }
    for (const relation of relationNamesFromRowSource(entry.binding.binding.rows)) {
      for (const source of resolvedSources(index, relation)) sources.add(source);
    }
  }
  return {
    sources: [...sources].filter(Boolean).sort(),
    bindings: entries.map((entry) => entry.binding.index),
  };
}

function expressionHasLiteral(expression: Expression | undefined): boolean {
  let found = false;
  walkExpression(expression, (node) => {
    if (node.kind === "literal") found = true;
  });
  return found;
}

function expressionHasFallback(expression: Expression | undefined): boolean {
  let found = false;
  walkExpression(expression, (node) => {
    if (
      node.kind === "operation" &&
      FALLBACK_OPERATORS.has(node.operator.at(-1) ?? "")
    ) {
      found = true;
    }
  });
  return found;
}

function propertyFindings(
  audit: AuditReport | undefined,
  component: string,
  property: string,
): AuditFinding[] {
  if (!audit) return [];
  return audit.findings.filter(
    (finding) =>
      finding.subject?.kind === "property" &&
      (finding.subject.component ?? finding.subject.name) === component &&
      finding.subject.property === property,
  );
}

function propertyBadges(
  index: ViewerIndex,
  audit: AuditReport | undefined,
  kind: EntityKind,
  component: string,
  property: string,
  summary: PropertySourceSummary,
  impactCount: number,
  impactTitle: string,
): SemanticsBadgeModel[] {
  const entries = findComponentPropertyBindings(
    index,
    kind,
    component,
    property,
  );
  const expressions = entries
    .map((entry) => entry.expression)
    .filter((expression): expression is Expression => Boolean(expression));
  const traced =
    entries.some((entry) => entry.fieldRefs.length > 0) ||
    expressions.some((expression) => collectFieldRefs(expression).length > 0);
  const literal = expressions.some(expressionHasLiteral);
  const fallback = expressions.some(expressionHasFallback);
  const multiSource = summary.sources.length > 1;
  const findings = propertyFindings(audit, component, property);
  const riskSeverity = SEVERITY_ORDER.find((severity) =>
    findings.some((finding) => finding.severity === severity),
  );

  const badges: SemanticsBadgeModel[] = [];
  if (traced) {
    badges.push({
      id: "traced",
      label: "traced",
      kind: "traced",
      title: `${expressions.length} expression branch(es) reference a source field`,
    });
  }
  if (literal) {
    badges.push({
      id: "literal",
      label: "literal",
      kind: "literal",
      title: "The property expression contains a literal value",
    });
  }
  if (fallback) {
    badges.push({
      id: "fallback",
      label: "fallback",
      kind: "fallback",
      title:
        "The property expression falls back to a literal when the source is missing",
    });
  }
  if (multiSource) {
    badges.push({
      id: "multi-source",
      label: "multi-source",
      kind: "multi-source",
      title: `Branches read from ${summary.sources.join(", ")}`,
    });
  }
  if (audit && findings.length) {
    badges.push({
      id: "risk",
      label: `risk:${findings.length}`,
      kind: "risk",
      severity: riskSeverity,
      value: findings.length,
      title: findings.map((finding) => finding.rule).join(", "),
    });
  }
  badges.push({
    id: "impact",
    label: `impact:${impactCount}`,
    kind: "impact",
    value: impactCount,
    title: impactTitle,
  });
  return badges;
}

function propertyRows(
  index: ViewerIndex,
  audit: AuditReport | undefined,
  selectedSubject: AuditSubject | undefined,
  item: TopologyItem,
  impactCount: number,
  impactTitle: string,
  openLineage?: SemanticsCommands["openLineage"],
): SemanticsPropertyRowModel[] {
  return item.properties.map((property) => {
    const summary = propertySourceSummary(
      index,
      item.kind,
      item.name,
      property.name,
    );
    const sourceTitle = summary.sources.length
      ? summary.sources.join(", ")
      : "no source relation";
    const bindingTitle = summary.bindings.length
      ? summary.bindings.map((binding) => `#${binding}`).join(", ")
      : "no binding";
    const sourceLabel = summary.sources.length
      ? summary.sources.join(", ")
      : "direct";
    const description =
      property.description ??
      `${property.name} · source ${sourceTitle} · binding ${bindingTitle}`;

    return {
      id: `${item.kind}:${item.name}:${property.name}`,
      kind: item.kind,
      component: item.name,
      name: property.name,
      description: property.description,
      annotations: property.annotations ?? [],
      source: {
        id: "source",
        label: "source",
        value: sourceLabel,
        title: `source ${sourceTitle} · binding ${bindingTitle}`,
      },
      typeLabel:
        property.logical_type?.name ?? property.logical_type?.kind ?? undefined,
      bindings: summary.bindings,
      badges: propertyBadges(
        index,
        audit,
        item.kind,
        item.name,
        property.name,
        summary,
        impactCount,
        impactTitle,
      ),
      selected: matchesSelectedProperty(
        selectedSubject,
        item.kind,
        item.name,
        property.name,
      ),
      actions: openLineage
        ? [
            {
              id: "open-lineage",
              label: "Open lineage",
              icon: "lineage",
              title: description,
              run: () => openLineage(item.kind, item.name, property.name),
            },
          ]
        : [],
    };
  });
}

function entityModel(
  index: ViewerIndex,
  audit: AuditReport | undefined,
  selectedSubject: AuditSubject | undefined,
  item: TopologyItem,
  paletteIndex: number,
  openLineage?: SemanticsCommands["openLineage"],
  openReview?: SemanticsCommands["openReview"],
): SemanticsEntityModel {
  const impact = componentImpact(index, item.kind, item.name);
  const impactCount = impact.upstream.length + impact.downstream.length;
  const impactTitle = `${impact.upstream.length} upstream and ${impact.downstream.length} downstream steps; targets ${
    impact.targets.join(", ") || "not recorded"
  }`;
  const description =
    item.description?.trim() || `What defines ${item.name}?`;

  return {
    id: entityId(item),
    key: entityKey(item),
    kind: item.kind,
    name: item.name,
    labels: item.labels,
    description,
    abstract: item.abstract,
    propertyCount: item.properties.length,
    properties: propertyRows(
      index,
      audit,
      selectedSubject,
      item,
      impactCount,
      impactTitle,
      openLineage,
    ),
    annotations: item.annotations,
    selected: Boolean(
      selectedSubject &&
        selectedSubject.kind === item.kind &&
        (selectedSubject.component ?? selectedSubject.name) === item.name,
    ),
    highlighted: matchesSelectedSubject(
      selectedSubject,
      item.kind,
      item.name,
    ),
    paletteIndex,
    actions: openReview
      ? [
          {
            id: "open-review",
            label: "Review",
            icon: "review",
            title: `Open review for ${item.kind} ${item.name}`,
            run: () =>
              openReview({
                kind: item.kind,
                name: item.name,
                component: item.name,
              }),
          },
        ]
      : [],
  };
}

function focusGroupForSubject(
  groups: GroupSeed[],
  subject: AuditSubject | undefined,
): GroupSeed | undefined {
  if (!groups.length) return undefined;
  return (
    groups.find((group) =>
      group.items.some((item) =>
        matchesSelectedSubject(subject, item.kind, item.name),
      ),
    ) ?? groups[0]
  );
}

function defaultCollapsedGroupIds(
  groups: GroupSeed[],
  entityCount: number,
  subject: AuditSubject | undefined,
): string[] {
  if (entityCount <= LARGE_GRID_THRESHOLD) return [];
  const expanded = focusGroupForSubject(groups, subject)?.parent;
  return groups
    .filter((group) => group.parent !== expanded)
    .map((group) => group.parent);
}

function canvasEdges(
  index: ViewerIndex,
  selectedSubject: AuditSubject | undefined,
): SemanticsCanvasEdgeModel[] {
  const selectedName = selectedSubject?.component ?? selectedSubject?.name;
  const selectedKind =
    selectedSubject?.kind === "property"
      ? selectedSubject.entityKind
      : selectedSubject?.kind;
  const edges: SemanticsCanvasEdgeModel[] = [];

  for (const edge of index.topologyEdges) {
    const edgeNode = `topology:edge:${edge.name}`;
    const source = edge.source?.[2];
    const target = edge.target?.[2];
    if (!source || !target) continue;
    if (
      !index.topologyNodesByName.has(source) ||
      !index.topologyNodesByName.has(target)
    ) {
      continue;
    }
    const sourceNode = `topology:node:${source}`;
    const targetNode = `topology:node:${target}`;
    const active = Boolean(
      selectedName &&
        ((selectedKind === "edge" && selectedName === edge.name) ||
          (selectedKind === "node" &&
            (source === selectedName || target === selectedName))),
    );
    for (const [from, to, label, role] of [
      [sourceNode, edgeNode, "source", "source"],
      [edgeNode, targetNode, "target", "target"],
    ] as const) {
      edges.push({
        id: `${from}->${to}`,
        source: from,
        target: to,
        label,
        name: edge.name,
        role,
        active,
        dimmed: Boolean(selectedName) && !active,
      });
    }
  }

  return edges;
}

function focusModel(
  index: ViewerIndex,
  group: GroupSeed | undefined,
  edges: SemanticsCanvasEdgeModel[],
  entityCards: SemanticsEntityModel[],
  edgeCards: SemanticsEntityModel[],
): SemanticsGraphFocusModel | null {
  if (!group) return null;
  const ids = new Set<string>();
  const addNode = (name: string | undefined) => {
    if (name && index.topologyNodesByName.has(name)) {
      ids.add(`topology:node:${name}`);
    }
  };
  const addEdge = (edge: TopologyEdge) => {
    ids.add(`topology:edge:${edge.name}`);
    addNode(edge.source?.[2]);
    addNode(edge.target?.[2]);
  };

  for (const item of group.items) {
    if (item.kind === "edge") {
      const edge = index.topologyEdgesByName.get(item.name);
      if (edge) addEdge(edge);
      else ids.add(`topology:edge:${item.name}`);
      continue;
    }

    ids.add(`topology:node:${item.name}`);
    for (const edge of index.topologyEdges) {
      const source = edge.source?.[2];
      const target = edge.target?.[2];
      if (source === item.name || target === item.name) addEdge(edge);
    }
  }

  const nodeIdSet = new Set(
    [...ids].filter((id) => id.startsWith("topology:node:")),
  );
  const nodeCards = entityCards.filter((entity) => nodeIdSet.has(entity.id));
  const focusedEdgeCards = edgeCards.filter((entity) => ids.has(entity.id));

  /*
   * A composition can contain many parallel edge cards for one source/target
   * pair. They carry the same connectors and make the focused canvas tall
   * without adding orientation. Focus renders one grouped card per pair with
   * the relationship names inside it; the whole graph keeps one card per edge.
   */
  const buckets = new Map<string, SemanticsEntityModel[]>();
  const bucketOrder: string[] = [];
  for (const entity of focusedEdgeCards) {
    const edge = index.topologyEdgesByName.get(entity.name);
    const source = edge?.source?.[2];
    const target = edge?.target?.[2];
    const endpointsReady =
      Boolean(source && target) &&
      nodeIdSet.has(`topology:node:${source}`) &&
      nodeIdSet.has(`topology:node:${target}`);
    const key = endpointsReady
      ? `${source}\u0000${target}`
      : `single:${entity.id}`;
    if (!buckets.has(key)) {
      buckets.set(key, []);
      bucketOrder.push(key);
    }
    buckets.get(key)?.push(entity);
  }

  const edgeGroups: SemanticsEdgeGroupModel[] = [];
  const ungroupedEdgeCards: SemanticsEntityModel[] = [];
  const focusedEdges: SemanticsCanvasEdgeModel[] = [];

  for (const key of bucketOrder) {
    const bucket = buckets.get(key) ?? [];
    if (bucket.length === 1) {
      const entity = bucket[0];
      ungroupedEdgeCards.push(entity);
      focusedEdges.push(...edges.filter((edge) => edge.name === entity.name));
      continue;
    }

    const first = bucket[0];
    const firstEdge = index.topologyEdgesByName.get(first.name);
    const sourceName = firstEdge?.source?.[2] ?? "";
    const targetName = firstEdge?.target?.[2] ?? "";
    const sourceId = `topology:node:${sourceName}`;
    const targetId = `topology:node:${targetName}`;
    const groupId = `topology:edge-group:${sourceName}|${targetName}`;
    const names = bucket.map((entity) => entity.name);
    const nameSet = new Set(names);
    const pairEdges = edges.filter(
      (edge) => nameSet.has(edge.name) && edge.role === "source",
    );
    const active = pairEdges.some((edge) => edge.active);
    const dimmed =
      pairEdges.length > 0 && pairEdges.every((edge) => edge.dimmed);
    const roles = new Set(
      bucket
        .map((entity) => index.topologyEdgesByName.get(entity.name)?.parent?.[2])
        .filter((role): role is string => Boolean(role)),
    );
    const role = roles.size === 1 ? [...roles][0] : "relationship";
    const testId = `bp-edge-group-${first.name}`;

    edgeGroups.push({
      id: groupId,
      role,
      sourceId,
      targetId,
      sourceName,
      targetName,
      edgeNames: names,
      paletteIndex: first.paletteIndex,
      selected: bucket.some((entity) => entity.selected),
      highlighted: bucket.some((entity) => entity.highlighted),
      active,
      dimmed,
    });

    focusedEdges.push(
      {
        id: `${sourceId}->${groupId}`,
        source: sourceId,
        target: groupId,
        label: "source",
        name: first.name,
        role: "source",
        testId: `${testId}-source`,
        active,
        dimmed,
      },
      {
        id: `${groupId}->${targetId}`,
        source: groupId,
        target: targetId,
        label: "target",
        name: first.name,
        role: "target",
        testId: `${testId}-target`,
        active,
        dimmed,
      },
    );
  }

  const groupedEdgeCount = edgeGroups.reduce(
    (total, grouped) => total + grouped.edgeNames.length,
    0,
  );
  const renderedIds = [
    ...nodeCards.map((entity) => entity.id),
    ...ungroupedEdgeCards.map((entity) => entity.id),
    ...edgeGroups.map((grouped) => grouped.id),
  ];

  return {
    groupId: group.parent,
    nodeIds: renderedIds,
    nodeCards,
    edgeCards: ungroupedEdgeCards,
    edgeGroups,
    nodeCount: nodeCards.length,
    edgeCardCount: ungroupedEdgeCards.length + edgeGroups.length,
    edgeRelationshipCount: focusedEdgeCards.length,
    edgeGroupCount: edgeGroups.length,
    groupedEdgeCount,
    edges: focusedEdges,
  };
}

function commandsFromSource(
  source: SemanticsSource,
): SemanticsCommands {
  return {
    openLineage: source.onSelectProperty ?? (() => {}),
    openReview: source.onOpenReview ?? (() => {}),
    selectEntity: source.onSelectEntity ?? (() => {}),
  };
}

/**
 * Build the semantic representation from the campaign.
 *
 * Cards is the semantic index (group -> entity -> property -> source field);
 * Graph is the same entities as composable cards. Both read one group model, so
 * switching representation never changes what the reviewer is looking at.
 */
export function buildSemanticsModel(campaign: CampaignView): SemanticsModel {
  return buildSemanticsModelFromSource({
    index: campaign.record.index,
    audit: campaign.record.audit ?? undefined,
    selectedSubject: subjectFromSelection(
      campaign.selection,
      campaign.record.index,
    ),
    onSelectProperty: (kind, component, property) =>
      campaign.commands.selectProperty(kind, component, property),
    onOpenReview: (subject) => campaign.commands.openReview(subject),
    onSelectEntity: (kind, name) =>
      campaign.commands.select({
        kind: "topology",
        entityKind: kind,
        name,
      }),
  });
}

export function buildSemanticsModelFromSource(
  source: SemanticsSource,
): SemanticsModel {
  const { index } = source;
  const audit = source.audit;
  const selectedSubject = source.selectedSubject;
  const commands = commandsFromSource(source);
  const groups = groupSeeds(index);
  const focusGroup = focusGroupForSubject(groups, selectedSubject);

  const modelGroups: SemanticsGroupModel[] = groups.map((group) => {
    const entities = group.items.map((item) =>
      entityModel(
        index,
        audit,
        selectedSubject,
        item,
        group.paletteIndex,
        source.onSelectProperty,
        source.onOpenReview,
      ),
    );
    return {
      id: group.parent,
      parent: group.parent,
      title: group.parent,
      question: "which entities and what defines them?",
      count: entities.length,
      propertyCount: entities.reduce(
        (total, entity) => total + entity.propertyCount,
        0,
      ),
      paletteIndex: group.paletteIndex,
      entities,
    };
  });

  const allEntities = modelGroups.flatMap((group) => group.entities);
  const entityCount = allEntities.length;
  const propertyCount = allEntities.reduce(
    (total, entity) => total + entity.propertyCount,
    0,
  );
  const entityCards = allEntities.filter((entity) => entity.kind === "node");
  const edgeCards = allEntities.filter((entity) => entity.kind === "edge");
  const edges = canvasEdges(index, selectedSubject);
  const focus = focusModel(index, focusGroup, edges, entityCards, edgeCards);
  const topologyCount = index.stats.topologyNodes + index.stats.topologyEdges;
  const wholeGraphNodes = index.stats.topologyNodes;
  const wholeGraphEdges = index.stats.topologyEdges;
  const focusNodes = focus?.nodeCount ?? 0;
  const focusEdgeCards = focus?.edgeCardCount ?? 0;
  const focusEdgeRelationships = focus?.edgeRelationshipCount ?? 0;
  const focusEdgeGroups = focus?.edgeGroupCount ?? 0;
  const focusGroupedEdges = focus?.groupedEdgeCount ?? 0;
  const focusLabel =
    focusEdgeGroups > 0
      ? `${focusNodes} nodes · ${focusEdgeCards} edge cards · ${focusGroupedEdges} edges grouped`
      : `${focusNodes} nodes · ${focusEdgeCards} edge cards`;
  const defaultMode: SemanticsMode =
    topologyCount > LARGE_BLUEPRINT_THRESHOLD ? "cards" : "graph";
  const sourceKey = `${index.snapshot.name}:${wholeGraphNodes}:${wholeGraphEdges}`;

  return {
    id: "semantics",
    question: "what is the blueprint made of, and what defines each entity?",
    metaGraph: index.metaGraph,
    cards: {
      id: "semantics-cards",
      question: "which entities exist, and what defines each one?",
      sourceKey,
      groups: modelGroups,
      entityCount,
      propertyCount,
      groupCount: modelGroups.length,
      focusGroupId: focusGroup?.parent,
      defaultCollapsedGroupIds: defaultCollapsedGroupIds(
        groups,
        entityCount,
        selectedSubject,
      ),
      empty:
        entityCount === 0
          ? {
              title: "No topology entities in this blueprint.",
              hint: "Load a snapshot whose blueprint graph carries nodes or edges, then return to Blueprint / Cards.",
            }
          : null,
    },
    graph: {
      id: "semantics-graph",
      question: "how do the entities connect, and which composition is in focus?",
      entityCards,
      edgeCards,
      edges,
      selectedSubject,
      focus,
      whole: {
        entityCount: topologyCount,
        edgeCount: wholeGraphEdges,
      },
    },
    overlay: {
      id: "semantics-overlay",
      label: "Blueprint representation controls",
      modes: [
        { id: "graph", label: "Graph", icon: "branch" },
        { id: "cards", label: "Cards", icon: "layers" },
      ],
      defaultMode,
      wholeGraph: {
        label: "Whole graph",
        focusLabel: "Focus graph",
        title: `Show the whole ${topologyCount}-entity graph`,
        focusTitle: "Show the focused composition",
      },
      auditKey: {
        label: "Audit key",
        title: "Show or hide the property audit key",
        legend: BADGE_LEGEND,
      },
      hints: {
        cards: "Entity index · sticky groups · click any property row for lineage",
        graph:
          "Focused composition · drag to pan · Whole graph for every subject",
        wholeGraph:
          "Whole graph · drag to pan · Focus graph for one composition",
      },
      counts: {
        wholeLabel: `${wholeGraphNodes} nodes · ${wholeGraphEdges} edges`,
        focusLabel,
        wholeNodes: wholeGraphNodes,
        wholeEdges: wholeGraphEdges,
        focusNodes,
        focusEdgeCards,
        focusEdgeRelationships,
        focusEdgeGroups,
        focusGroupedEdges,
        totalEntities: entityCount,
        totalProperties: propertyCount,
      },
      scaleHint: {
        visible: topologyCount > LARGE_BLUEPRINT_THRESHOLD,
        wholeTitle: `${wholeGraphNodes} nodes · ${wholeGraphEdges} edges`,
        focusTitle: `${focusNodes} focused nodes · ${focusEdgeCards} edge cards`,
        wholeChip: "use Cards or Read to inspect at this scale",
        focusChip: "focused composition; pan to explore",
      },
    },
    commands,
  };
}
