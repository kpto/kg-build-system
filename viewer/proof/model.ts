/**
 * Proof model.
 *
 * One selected subject is expanded into a provenance model. The property level
 * reuses `buildLineage` and adds the attached meaning and the type/presence
 * chain. Node, edge, abstract and asset levels are derived views over the same
 * index; they never rebuild a second lineage model.
 */

import type {
  AssetLicense,
  AssetProfileDTO,
  ArtifactType,
  DataField,
  EntityKind,
  FieldLocation,
  LineageBranch,
  LineageEdge,
  LineageGraph,
  LineageLane,
  LineageNode,
  LineageNodeKind,
  LogicalType,
  ProjectionDTO,
  PropertySelection,
  PurposeDTO,
  Ref,
  RelationDTO,
  SemanticSubject,
  SemanticsFrameDTO,
  SemanticSubjectKind,
  SemanticText,
  StepId,
  TopologyEdge,
  TopologyNode,
  TopologyProperty,
  ViewerIndex,
  WorkflowStep,
} from "@/lib/types";
import { LINEAGE_LANES } from "@/lib/types";
import { buildLineage, propertySelection } from "@/lib/lineage";
import {
  collectFieldRefs,
  collectOperations,
  fieldRefKey,
  logicalTypeBase,
  logicalTypeName,
  logicalTypePresence,
} from "@/lib/expressions";
import {
  artifactDisplay,
  findComponentPropertyBindings,
  relationNamesFromRowSource,
  resolveAssetName,
  semanticSubjectKey,
} from "@/lib/indexes";
import { resolveFieldSources } from "./sources";
import { meaningText } from "@/lib/summary";

export type ProofLevel = "property" | "node" | "edge" | "abstract" | "asset";

/** A subject the proof panel can inspect, independent of the workbench shell. */
export interface ProofSubject {
  level: ProofLevel;
  kind: EntityKind | "asset" | "abstract";
  component: string;
  property?: string;
  propertyRef?: Ref;
}

/** The workbench selection fields the model reads. */
export interface ProofSelectionLike {
  kind?: string;
  level?: string;
  name?: string;
  component?: string;
  property?: string;
}

// ---------------------------------------------------------------------------
// Semantics
// ---------------------------------------------------------------------------

/** One subject's attached meaning. Evidence is read, never propagated. */
export interface ProofSemantics {
  key: string;
  kind: SemanticSubjectKind;
  name: string;
  ref?: Ref;
  ownerName?: string;
  entityKind?: EntityKind;
  claims: SemanticText[];
  /** The subject's purpose and the limitations it owns. */
  purpose?: PurposeDTO;
  limitations: SemanticText[];
  frames: SemanticsFrameDTO[];
}

function semanticsFromSubject(subject: SemanticSubject): ProofSemantics {
  return {
    key: subject.key,
    kind: subject.kind,
    name: subject.name,
    ref: subject.ref,
    ownerName: subject.ownerName,
    entityKind: subject.entityKind,
    claims: subject.semantics?.claims ?? [],
    purpose: subject.semantics?.purpose,
    limitations: subject.semantics?.purpose?.limitations ?? [],
    frames: subject.semantics?.frames ?? [],
  };
}

function dedupeSemantics(attachments: ProofSemantics[]): ProofSemantics[] {
  const seen = new Set<string>();
  const result: ProofSemantics[] = [];
  for (const attachment of attachments) {
    if (seen.has(attachment.key)) continue;
    seen.add(attachment.key);
    result.push(attachment);
  }
  return result;
}

function attachment(
  index: ViewerIndex,
  kind: SemanticSubjectKind,
  ...segments: Array<string | number>
): ProofSemantics | undefined {
  const subject = index.semanticsByKey.get(semanticSubjectKey(kind, ...segments));
  return subject ? semanticsFromSubject(subject) : undefined;
}

function graphAttachment(index: ViewerIndex): ProofSemantics | undefined {
  const declaration = index.graphDeclaration;
  if (!declaration) return undefined;
  return attachment(index, "graph", declaration.name);
}

function propertyAttachment(
  index: ViewerIndex,
  kind: EntityKind,
  component: string,
  property: string,
): ProofSemantics | undefined {
  return attachment(index, "property", kind, component, property);
}

function componentAttachment(
  index: ViewerIndex,
  kind: EntityKind,
  component: string,
): ProofSemantics | undefined {
  return attachment(index, kind, component);
}

function fieldAttachment(
  index: ViewerIndex,
  fieldRef: Ref,
): ProofSemantics | undefined {
  const location = index.fieldsByKey.get(fieldRefKey(fieldRef));
  if (!location) return undefined;
  return attachment(
    index,
    "field",
    location.ownerKind,
    location.ownerName,
    location.field.name,
  );
}

function dataAttachment(
  index: ViewerIndex,
  name: string,
): ProofSemantics | undefined {
  if (index.relationByName.has(name)) return attachment(index, "relation", name);
  if (index.projectionByName.has(name)) return attachment(index, "projection", name);
  if (index.structByName.has(name)) return attachment(index, "struct", name);
  return undefined;
}

// ---------------------------------------------------------------------------
// Type and presence chain
// ---------------------------------------------------------------------------

export type ProofTypeStage =
  | "property"
  | "binding"
  | "source"
  | "operator"
  | "post";

export interface ProofTypeStep {
  id: string;
  stage: ProofTypeStage;
  label: string;
  detail?: string;
  typeName?: string;
  presence: "present" | "nullable" | "unknown";
  mismatch?: boolean;
}

export interface ProofTypeChain {
  branchKey: string;
  steps: ProofTypeStep[];
  /** A base type differs between the declared property and the value. */
  mismatch: boolean;
  /** The declared property is present while a source access is nullable. */
  narrowed: boolean;
}

function entityProperty(
  index: ViewerIndex,
  selection: PropertySelection,
): TopologyProperty | undefined {
  const entity =
    selection.kind === "node"
      ? index.topologyNodesByName.get(selection.component)
      : index.topologyEdgesByName.get(selection.component);
  return entity?.properties?.find(
    (candidate) => candidate.name === selection.property,
  );
}

function expressionType(expression: LineageBranch["expression"]): LogicalType | undefined {
  if (!expression) return undefined;
  return expression.logical_type;
}

function postStepStage(step: WorkflowStep): ProofTypeStage {
  const operation = step.instruction.kind[0];
  return operation === "aggregate" ||
    operation === "deduplication" ||
    operation === "merging" ||
    operation === "conflict_validation"
    ? "post"
    : "operator";
}

function presenceOperator(name: string): boolean {
  return [
    "drop_null",
    "drop_null_items",
    "default_to",
    "coalesce",
    "filter",
  ].includes(name);
}

function buildTypeChain(
  index: ViewerIndex,
  selection: PropertySelection,
  branch: LineageBranch,
  propertyType: LogicalType | undefined,
): ProofTypeChain {
  const propertyBase = logicalTypeBase(propertyType);
  const mismatched = (type: LogicalType | undefined): boolean =>
    Boolean(type) &&
    propertyBase !== "unknown" &&
    logicalTypeBase(type) !== "unknown" &&
    logicalTypeBase(type) !== propertyBase;

  const steps: ProofTypeStep[] = [
    {
      id: "property",
      stage: "property",
      label: `${selection.component}.${selection.property}`,
      detail: "declared topology property",
      typeName: logicalTypeName(propertyType),
      presence: logicalTypePresence(propertyType),
    },
  ];

  const bindingType = expressionType(branch.expression);
  steps.push({
    id: "binding",
    stage: "binding",
    label: `binding ${branch.binding.index}`,
    detail: branch.binding.binding.name,
    typeName: logicalTypeName(bindingType),
    presence: logicalTypePresence(bindingType),
    mismatch: mismatched(bindingType),
  });

  for (const fieldRef of branch.fieldRefs) {
    const location = index.fieldsByKey.get(fieldRefKey(fieldRef));
    const type = location?.field.logical_type;
    steps.push({
      id: `source:${fieldRefKey(fieldRef)}`,
      stage: "source",
      label: fieldRefKey(fieldRef),
      detail: location
        ? `${location.ownerKind} field`
        : "unresolved field reference",
      typeName: logicalTypeName(type),
      presence: logicalTypePresence(type),
      mismatch: mismatched(type),
    });
  }

  for (const operation of collectOperations(branch.expression)) {
    steps.push({
      id: `operator:${operation.name}:${operation.depth}`,
      stage: presenceOperator(operation.name) ? "operator" : "operator",
      label: operation.name,
      detail: presenceOperator(operation.name)
        ? "presence operator"
        : "expression operator",
      typeName: logicalTypeName(operation.type),
      presence: logicalTypePresence(operation.type),
      mismatch: mismatched(operation.type),
    });
  }

  for (const step of branch.postSteps) {
    steps.push({
      id: `post:${step.id[0]}/${step.id[1]}`,
      stage: postStepStage(step),
      label: step.id[1],
      detail: step.instruction.kind.join("."),
      presence: "unknown",
    });
  }

  const bindingPresence = logicalTypePresence(bindingType);
  const sourceNullable = branch.fieldRefs.some((fieldRef) =>
    logicalTypePresence(
      index.fieldsByKey.get(fieldRefKey(fieldRef))?.field.logical_type,
    ) === "nullable",
  );

  return {
    branchKey: branch.key,
    steps,
    mismatch: steps.some((step) => step.mismatch),
    narrowed:
      logicalTypePresence(propertyType) === "present" &&
      (bindingPresence === "nullable" || sourceNullable),
  };
}

// ---------------------------------------------------------------------------
// Trace
// ---------------------------------------------------------------------------

export interface ProofTraceEntry {
  id: string;
  label: string;
  lane: LineageLane;
  kind: LineageNodeKind;
  stepId?: StepId;
  artifacts: ArtifactType[];
  sqlPreview?: string;
  sourceLocation?: string;
  description?: string;
  workflowKind?: string;
}

export interface ProofTrace {
  source: ProofTraceEntry[];
  transformation: ProofTraceEntry[];
  binding: ProofTraceEntry[];
  post: ProofTraceEntry[];
  target: ProofTraceEntry[];
}

function postStepKind(step: WorkflowStep): LineageNodeKind {
  switch (step.instruction.kind[0]) {
    case "aggregate":
      return "aggregate";
    case "deduplication":
      return "deduplication";
    case "merging":
      return "merging";
    case "conflict_validation":
      return "conflict";
    default:
      return "step";
  }
}

function stepTraceEntry(
  step: WorkflowStep,
  lane: LineageLane,
  kind: LineageNodeKind,
): ProofTraceEntry {
  return {
    id: `step:${step.id[0]}/${step.id[1]}`,
    label: step.id[1],
    lane,
    kind,
    stepId: step.id,
    artifacts: (step.outputs ?? []).map((output) => output.type),
    sqlPreview:
      typeof step.instruction.payload?.sql === "string"
        ? step.instruction.payload.sql
        : undefined,
    description:
      typeof step.instruction.payload?.description === "string"
        ? step.instruction.payload.description
        : undefined,
    workflowKind: step.instruction.kind.join("."),
  };
}

function buildTrace(branch: LineageBranch): ProofTrace {
  return {
    source: branch.sourceSteps.map((step) =>
      stepTraceEntry(step, "source", "table"),
    ),
    transformation: branch.transformationSteps.map((step) =>
      stepTraceEntry(step, "transformation", "projection"),
    ),
    binding: branch.bindingStep
      ? [stepTraceEntry(branch.bindingStep, "binding", "binding")]
      : [],
    post: branch.postSteps.map((step) =>
      stepTraceEntry(step, "post", postStepKind(step)),
    ),
    target: branch.targetSteps.map((step) =>
      stepTraceEntry(step, "target", "target"),
    ),
  };
}

// ---------------------------------------------------------------------------
// Branch
// ---------------------------------------------------------------------------

export interface ProofBranch {
  key: string;
  label: string;
  branch: LineageBranch;
  nodes: ProofNode[];
  edges: LineageEdge[];
  typeChain: ProofTypeChain;
  /** Every attached card on this branch, in lane order. */
  semantics: ProofSemantics[];
  trace: ProofTrace;
}

export interface ProofNode extends LineageNode {
  semantics: ProofSemantics[];
}

function nodeAttachments(
  index: ViewerIndex,
  node: LineageNode,
  selection: PropertySelection,
  branch: LineageBranch,
): ProofSemantics[] {
  const attachments: ProofSemantics[] = [];
  switch (node.kind) {
    case "asset":
      if (node.component) {
        const asset = attachment(index, "asset", node.component);
        if (asset) attachments.push(asset);
      }
      break;
    case "table":
      if (node.component) {
        const relation = attachment(index, "relation", node.component);
        if (relation) attachments.push(relation);
      }
      break;
    case "projection":
      if (node.component) {
        const projection = attachment(index, "projection", node.component);
        if (projection) attachments.push(projection);
      }
      break;
    case "field":
      if (node.ref) {
        const field = fieldAttachment(index, node.ref);
        if (field) attachments.push(field);
      }
      break;
    case "binding":
      if (node.id === `semantic:binding:${selection.component}.${branch.binding.index}`) {
        const binding = attachment(index, "binding", branch.binding.index);
        if (binding) attachments.push(binding);
      }
      break;
    case "property":
    case "target": {
      const property = propertyAttachment(
        index,
        selection.kind,
        selection.component,
        selection.property,
      );
      if (property) attachments.push(property);
      break;
    }
    default:
      break;
  }
  return attachments;
}

function branchSemanticsForNodes(
  index: ViewerIndex,
  selection: PropertySelection,
  branch: LineageBranch,
  nodes: ProofNode[],
): ProofSemantics[] {
  return dedupeSemantics(
    nodes.flatMap((node) => nodeAttachments(index, node, selection, branch)),
  );
}

function branchLabel(branch: LineageBranch): string {
  const source = branch.sourceRelations.at(0) ?? branch.relationNames.at(0);
  const asset = branch.assetNames.at(0);
  return [asset, source, `binding ${branch.binding.index}`]
    .filter(Boolean)
    .join(" · ");
}

// ---------------------------------------------------------------------------
// Summaries for component, abstract and asset levels
// ---------------------------------------------------------------------------

export interface ProofPropertySummary {
  component: string;
  kind: EntityKind;
  property: string;
  propertyRef: Ref;
  logicalType?: LogicalType;
  branchCount: number;
  sources: string[];
  assets: string[];
  projections: string[];
  bindingIndexes: number[];
  steps: StepId[];
  semantics: ProofSemantics[];
}

function expressionFieldRefs(
  entry: ReturnType<typeof findComponentPropertyBindings>[number],
): Ref[] {
  const expression =
    entry.expression ??
    entry.binding.binding.properties?.[entry.property];
  return collectFieldRefs(expression);
}

function entrySources(
  index: ViewerIndex,
  entry: ReturnType<typeof findComponentPropertyBindings>[number],
): { sources: string[]; assets: string[]; projections: string[] } {
  return resolveFieldSources(index, expressionFieldRefs(entry));
}

function summariseProperty(
  index: ViewerIndex,
  kind: EntityKind,
  component: string,
  property: TopologyProperty,
): ProofPropertySummary {
  const entries = findComponentPropertyBindings(
    index,
    kind,
    component,
    property.name,
  );
  const uniqueEntries = entries.filter(
    (entry, position, all) =>
      all.findIndex(
        (candidate) => candidate.binding.index === entry.binding.index,
      ) === position,
  );
  const sources = new Set<string>();
  const assets = new Set<string>();
  const projections = new Set<string>();
  for (const entry of uniqueEntries) {
    const resolved = entrySources(index, entry);
    for (const source of resolved.sources) sources.add(source);
    for (const asset of resolved.assets) assets.add(asset);
    for (const projection of resolved.projections) projections.add(projection);
  }
  const semantics = dedupeSemantics(
    [
      propertyAttachment(index, kind, component, property.name),
      ...uniqueEntries.map((entry) =>
        attachment(index, "binding", entry.binding.index),
      ),
    ].filter((value): value is ProofSemantics => Boolean(value)),
  );
  return {
    component,
    kind,
    property: property.name,
    propertyRef: property.ref,
    logicalType: property.logical_type,
    branchCount: uniqueEntries.length,
    sources: [...sources],
    assets: [...assets],
    projections: [...projections],
    bindingIndexes: uniqueEntries.map((entry) => entry.binding.index),
    steps: uniqueEntries
      .map((entry) => entry.binding.step?.id)
      .filter((step): step is StepId => Boolean(step)),
    semantics,
  };
}

function entityComponent(
  index: ViewerIndex,
  kind: EntityKind,
  component: string,
): TopologyNode | TopologyEdge | undefined {
  return kind === "node"
    ? index.topologyNodesByName.get(component)
    : index.topologyEdgesByName.get(component);
}

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------

export interface ProofComponent {
  kind: EntityKind;
  name: string;
  abstract: boolean;
  description?: string;
  labels: string[];
  provenance?: { source?: string; target?: string };
  semantics: ProofSemantics[];
  properties: ProofPropertySummary[];
}

export interface ProofAbstractDescendant {
  name: string;
  description?: string;
  labels: string[];
  properties: ProofPropertySummary[];
}

export interface ProofAbstract {
  name: string;
  description?: string;
  labels: string[];
  semantics: ProofSemantics[];
  descendants: ProofAbstractDescendant[];
}

export interface ProofAssetRelation {
  name: string;
  description?: string;
  kind: "relation" | "projection";
  columns: number;
  semantics: ProofSemantics[];
}

export interface ProofAssetField {
  key: string;
  ownerName: string;
  ownerKind: FieldLocation["ownerKind"];
  field: DataField;
  semantics: ProofSemantics[];
}

export interface ProofAsset {
  name: string;
  profile?: AssetProfileDTO;
  license?: AssetLicense | string | null;
  semantics: ProofSemantics[];
  relations: ProofAssetRelation[];
  projections: ProofAssetRelation[];
  fields: ProofAssetField[];
  properties: ProofPropertySummary[];
}

export interface ProofModel {
  level: ProofLevel;
  subject: ProofSubject;
  /** The graph declaration purpose, attached to the root of every level. */
  rootSemantics: ProofSemantics[];
  /** Attached semantics for the selected subject at the current level. */
  subjectSemantics: ProofSemantics[];
  property?: PropertySelection;
  lineage?: LineageGraph;
  branches: ProofBranch[];
  nodes: ProofNode[];
  lanes: Array<{ id: LineageLane; label: string }>;
  typeChain?: ProofTypeChain;
  component?: ProofComponent;
  abstract?: ProofAbstract;
  asset?: ProofAsset;
  properties: ProofPropertySummary[];
  empty: boolean;
}

function baseModel(subject: ProofSubject, index: ViewerIndex): ProofModel {
  return {
    level: subject.level,
    subject,
    rootSemantics: dedupeSemantics(
      [graphAttachment(index)].filter(
        (value): value is ProofSemantics => Boolean(value),
      ),
    ),
    subjectSemantics: [],
    branches: [],
    nodes: [],
    lanes: LINEAGE_LANES,
    properties: [],
    empty: true,
  };
}

function propertySubject(
  index: ViewerIndex,
  kind: EntityKind,
  component: string,
  property: string,
): ProofSubject {
  const entity = entityComponent(index, kind, component);
  const declaration = entity?.properties?.find(
    (candidate) => candidate.name === property,
  );
  return {
    level: "property",
    kind,
    component,
    property,
    propertyRef:
      declaration?.ref ?? [
        "topology",
        "property",
        `${component}.${property}`,
      ],
  };
}

function firstPropertyOf(
  index: ViewerIndex,
  kind: EntityKind,
  component: string,
): string | undefined {
  return entityComponent(index, kind, component)?.properties?.at(0)?.name;
}

/** Expand one property into a branch, type chain and attached evidence. */
function buildPropertyProof(
  index: ViewerIndex,
  subject: ProofSubject,
): ProofModel {
  if (subject.kind !== "node" && subject.kind !== "edge") {
    return baseModel(subject, index);
  }
  let property = subject.property;
  if (!property) {
    property = firstPropertyOf(index, subject.kind, subject.component);
  }
  if (!property) {
    return baseModel(
      { ...subject, level: "node", property: undefined },
      index,
    );
  }

  const selection = propertySelection(
    subject.kind,
    subject.component,
    property,
  );
  const modelSubject = propertySubject(
    index,
    subject.kind,
    subject.component,
    property,
  );
  const lineage = buildLineage(index, selection);
  const propertyType = entityProperty(index, selection)?.logical_type;

  const nodesById = new Map(lineage.nodes.map((node) => [node.id, node]));
  const edgesById = new Map(lineage.edges.map((edge) => [edge.id, edge]));

  const branches = lineage.branches.map((branch) => {
    const branchNodeIds = [...branch.nodeIds];
    if (!branchNodeIds.includes(lineage.terminalNodeId)) {
      branchNodeIds.push(lineage.terminalNodeId);
    }
    const branchNodes = dedupeNodes(
      branchNodeIds
        .map((id) => nodesById.get(id))
        .filter((node): node is LineageNode => Boolean(node)),
    ).map<ProofNode>((node) => ({
      ...node,
      semantics: nodeAttachments(index, node, selection, branch),
    }));
    const branchEdges = branch.edgeIds
      .map((id) => edgesById.get(id))
      .filter((edge): edge is LineageEdge => Boolean(edge));
    return {
      key: branch.key,
      label: branchLabel(branch),
      branch,
      nodes: branchNodes,
      edges: branchEdges,
      typeChain: buildTypeChain(index, selection, branch, propertyType),
      semantics: branchSemanticsForNodes(index, selection, branch, branchNodes),
      trace: buildTrace(branch),
    };
  });

  const nodes = dedupeNodes(lineage.nodes).map<ProofNode>((node) => ({
    ...node,
    semantics: nodeAttachments(
      index,
      node,
      selection,
      branches[0]?.branch ?? ({} as LineageBranch),
    ),
  }));

  const typeChain = branches[0]?.typeChain;

  return {
    ...baseModel(modelSubject, index),
    property: selection,
    lineage,
    branches,
    nodes,
    typeChain,
    subjectSemantics: dedupeSemantics([
      componentAttachment(index, subject.kind, subject.component),
      propertyAttachment(index, subject.kind, subject.component, property),
      ...(branches.flatMap((branch) =>
        branch.semantics.filter((item) => item.kind === "binding"),
      )),
    ].filter((value): value is ProofSemantics => Boolean(value))),
    properties: [],
    empty: branches.length === 0,
  };
}

function dedupeNodes(nodes: LineageNode[]): LineageNode[] {
  const seen = new Set<string>();
  const result: LineageNode[] = [];
  for (const node of nodes) {
    if (seen.has(node.id)) continue;
    seen.add(node.id);
    result.push(node);
  }
  return result;
}

function buildComponentProof(
  index: ViewerIndex,
  subject: ProofSubject,
): ProofModel {
  if (subject.kind !== "node" && subject.kind !== "edge") {
    return baseModel(subject, index);
  }
  const kind: EntityKind = subject.kind;
  const entity = entityComponent(index, kind, subject.component);
  if (!entity) return baseModel(subject, index);
  const properties = (entity.properties ?? []).map((property) =>
    summariseProperty(index, kind, subject.component, property),
  );
  const component: ProofComponent = {
    kind,
    name: entity.name,
    abstract: Boolean(entity.abstract),
    description:
      meaningText(entity.meaning ?? entity.semantics) ?? entity.description,
    labels: entity.labels ?? [],
    provenance:
      subject.kind === "edge"
        ? {
            source: (entity as TopologyEdge).source?.[2],
            target: (entity as TopologyEdge).target?.[2],
          }
        : undefined,
    semantics: dedupeSemantics(
      [
        componentAttachment(index, subject.kind, subject.component),
      ].filter((value): value is ProofSemantics => Boolean(value)),
    ),
    properties,
  };
  return {
    ...baseModel(subject, index),
    component,
    properties,
    subjectSemantics: component.semantics,
    empty: properties.length === 0,
  };
}

function abstractAncestor(
  index: ViewerIndex,
  name: string | undefined,
): TopologyNode | undefined {
  let current = name ? index.topologyNodesByName.get(name) : undefined;
  const visited = new Set<string>();
  while (current && !visited.has(current.name)) {
    visited.add(current.name);
    if (current.abstract) return current;
    current = current.parent?.[2]
      ? index.topologyNodesByName.get(current.parent[2])
      : undefined;
  }
  return index.topologyNodes.find((node) => node.abstract);
}

function descendantsOf(
  index: ViewerIndex,
  name: string,
): TopologyNode[] {
  const result: TopologyNode[] = [];
  const visit = (parent: string) => {
    for (const node of index.topologyNodes) {
      if (node.parent?.[2] !== parent) continue;
      if (node.abstract) {
        visit(node.name);
        continue;
      }
      result.push(node);
    }
  };
  visit(name);
  return result;
}

function buildAbstractProof(
  index: ViewerIndex,
  subject: ProofSubject,
): ProofModel {
  const node = abstractAncestor(index, subject.component);
  if (!node) return baseModel(subject, index);
  const abstractSubject: ProofSubject = {
    level: "abstract",
    kind: "abstract",
    component: node.name,
  };
  const descendants = descendantsOf(index, node.name).map((descendant) => ({
    name: descendant.name,
    description:
      meaningText(descendant.meaning ?? descendant.semantics) ??
      descendant.description,
    labels: descendant.labels ?? [],
    properties: (descendant.properties ?? []).map((property) =>
      summariseProperty(index, "node", descendant.name, property),
    ),
  }));
  const semantics = dedupeSemantics(
    [componentAttachment(index, "node", node.name)].filter(
      (value): value is ProofSemantics => Boolean(value),
    ),
  );
  const abstract: ProofAbstract = {
    name: node.name,
    description:
      meaningText(node.meaning ?? node.semantics) ?? node.description,
    labels: node.labels ?? [],
    semantics,
    descendants,
  };
  return {
    ...baseModel(abstractSubject, index),
    abstract,
    subjectSemantics: semantics,
    properties: descendants.flatMap((descendant) => descendant.properties),
    empty: descendants.length === 0,
  };
}

function assetPropertySummaries(
  index: ViewerIndex,
  assetName: string,
): ProofPropertySummary[] {
  const seen = new Set<string>();
  const result: ProofPropertySummary[] = [];
  for (const entries of index.propertyIndex.values()) {
    const entry = entries.find((candidate) => {
      const fieldRefs = expressionFieldRefs(candidate);
      return fieldRefs.some((fieldRef) => {
        const ownerName =
          index.fieldsByKey.get(fieldRefKey(fieldRef))?.ownerName ??
          fieldRef[2]?.split(".")[0];
        return ownerName
          ? resolveAssetName(index, ownerName) === assetName
          : false;
      });
    });
    if (!entry) continue;
    const key = `${entry.kind}:${entry.component}:${entry.property}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const entity = entityComponent(index, entry.kind, entry.component);
    const property = entity?.properties?.find(
      (candidate) => candidate.name === entry.property,
    );
    if (!property) continue;
    result.push(
      summariseProperty(index, entry.kind, entry.component, property),
    );
  }
  return result;
}

function dataRelation(
  index: ViewerIndex,
  name: string,
  kind: "relation" | "projection",
  value: RelationDTO | ProjectionDTO,
): ProofAssetRelation {
  return {
    name,
    description: value.description,
    kind,
    columns: value.columns?.length ?? 0,
    semantics: dedupeSemantics(
      [dataAttachment(index, name)].filter(
        (candidate): candidate is ProofSemantics => Boolean(candidate),
      ),
    ),
  };
}

function buildAssetProof(
  index: ViewerIndex,
  subject: ProofSubject,
): ProofModel {
  const asset = index.assetsByName.get(subject.component);
  if (!asset) return baseModel(subject, index);
  const assetSubject: ProofSubject = {
    level: "asset",
    kind: "asset",
    component: asset.name,
  };
  const relations = index.relations
    .filter((relation) => resolveAssetName(index, relation.name) === asset.name)
    .map((relation) => dataRelation(index, relation.name, "relation", relation));
  const projections = index.projections
    .filter((projection) => resolveAssetName(index, projection.name) === asset.name)
    .map((projection) =>
      dataRelation(index, projection.name, "projection", projection),
    );
  const relationNames = new Set(relations.map((relation) => relation.name));
  const projectionNames = new Set(projections.map((projection) => projection.name));
  const fields: ProofAssetField[] = index.fields
    .filter(
      (location) =>
        relationNames.has(location.ownerName) ||
        projectionNames.has(location.ownerName),
    )
    .map((location) => ({
      key: location.key,
      ownerName: location.ownerName,
      ownerKind: location.ownerKind,
      field: location.field,
      semantics: dedupeSemantics(
        [fieldAttachment(index, location.field.ref ?? [])].filter(
          (candidate): candidate is ProofSemantics => Boolean(candidate),
        ),
      ),
    }));
  const semantics = dedupeSemantics(
    [attachment(index, "asset", asset.name)].filter(
      (value): value is ProofSemantics => Boolean(value),
    ),
  );
  const properties = assetPropertySummaries(index, asset.name);
  const assetModel: ProofAsset = {
    name: asset.name,
    profile: asset.profile,
    license: asset.governance?.license ?? null,
    semantics,
    relations,
    projections,
    fields,
    properties,
  };
  return {
    ...baseModel(assetSubject, index),
    asset: assetModel,
    subjectSemantics: semantics,
    properties,
    empty:
      relations.length === 0 &&
      projections.length === 0 &&
      properties.length === 0,
  };
}

// ---------------------------------------------------------------------------
// Selection
// ---------------------------------------------------------------------------

/** The first concrete node property, then an edge property, then an asset. */
export function defaultProofSubject(index: ViewerIndex): ProofSubject {
  const concreteNode = index.topologyNodes.find(
    (node) => !node.abstract && (node.properties?.length ?? 0) > 0,
  );
  if (concreteNode) {
    return propertySubject(
      index,
      "node",
      concreteNode.name,
      concreteNode.properties?.[0]?.name ?? "",
    );
  }
  const concreteEdge = index.topologyEdges.find(
    (edge) => !edge.abstract && (edge.properties?.length ?? 0) > 0,
  );
  if (concreteEdge) {
    return propertySubject(
      index,
      "edge",
      concreteEdge.name,
      concreteEdge.properties?.[0]?.name ?? "",
    );
  }
  const asset = index.assets.at(0);
  if (asset) {
    return { level: "asset", kind: "asset", component: asset.name };
  }
  const node = index.topologyNodes.at(0);
  if (node) {
    return { level: "node", kind: "node", component: node.name };
  }
  return { level: "asset", kind: "asset", component: "" };
}

function firstPropertyUsingField(
  index: ViewerIndex,
  fieldRef: Ref,
): ProofSubject | undefined {
  for (const entries of index.propertyIndex.values()) {
    for (const entry of entries) {
      const fieldRefs = expressionFieldRefs(entry);
      if (!fieldRefs.some((candidate) => fieldRefKey(candidate) === fieldRefKey(fieldRef))) {
        continue;
      }
      return propertySubject(index, entry.kind, entry.component, entry.property);
    }
  }
  return undefined;
}

/** Resolve the workbench selection into a proof subject with a fallback. */
export function resolveProofSubject(
  index: ViewerIndex,
  selection: ProofSelectionLike | undefined,
): ProofSubject {
  if (!selection) return defaultProofSubject(index);
  const level = selection.level;
  const kind = selection.kind;
  const component = selection.component ?? selection.name;

  if (
    (level === "property" || kind === "property" || (!level && selection.property)) &&
    component &&
    selection.property
  ) {
    const entityKind: EntityKind | undefined = index.topologyNodesByName.has(component)
      ? "node"
      : index.topologyEdgesByName.has(component)
        ? "edge"
        : undefined;
    if (entityKind) {
      return propertySubject(index, entityKind, component, selection.property);
    }
  }
  if ((level === "node" || level === "edge") && component) {
    const wanted = level === "node" ? "node" : "edge";
    if (index.topologyComponentsByName.has(component)) {
      const actual = index.topologyNodesByName.has(component) ? "node" : "edge";
      return { level: wanted, kind: actual, component };
    }
  }
  if (level === "abstract") {
    return {
      level: "abstract",
      kind: "abstract",
      component: component ?? "",
    };
  }
  if (level === "asset" || kind === "asset") {
    if (component && index.assetsByName.has(component)) {
      return { level: "asset", kind: "asset", component };
    }
  }
  if ((kind === "relation" || kind === "projection" || kind === "struct") && component) {
    const assetName = resolveAssetName(index, component);
    if (assetName) {
      return { level: "asset", kind: "asset", component: assetName };
    }
  }
  if (kind === "field" && component) {
    const location = index.fieldsByKey.get(component);
    if (location) {
      const resolved = firstPropertyUsingField(
        index,
        location.field.ref ?? [],
      );
      if (resolved) return resolved;
      const assetName = resolveAssetName(index, location.ownerName);
      if (assetName) {
        return { level: "asset", kind: "asset", component: assetName };
      }
    }
  }
  if ((kind === "node" || kind === "edge") && component) {
    if (index.topologyComponentsByName.has(component)) {
      const actual = index.topologyNodesByName.has(component) ? "node" : "edge";
      return { level: actual, kind: actual, component };
    }
  }
  return defaultProofSubject(index);
}

/** Build the model for one workbench selection. */
export function buildProof(
  index: ViewerIndex,
  selection: ProofSelectionLike | ProofSubject | undefined,
): ProofModel {
  const subject = resolveProofSubject(
    index,
    selection as ProofSelectionLike | undefined,
  );
  switch (subject.level) {
    case "property":
      return buildPropertyProof(index, subject);
    case "node":
    case "edge":
      return buildComponentProof(index, subject);
    case "abstract":
      return buildAbstractProof(index, subject);
    case "asset":
      return buildAssetProof(index, subject);
  }
}

/** The node/edge proof body is also the fallback for the abstract selector. */
export function defaultAbstractSubject(index: ViewerIndex): ProofSubject {
  const node = index.topologyNodes.find((candidate) => candidate.abstract);
  return {
    level: "abstract",
    kind: "abstract",
    component: node?.name ?? "",
  };
}

function firstComponentOfKind(
  index: ViewerIndex,
  kind: EntityKind,
): TopologyNode | TopologyEdge | undefined {
  const values = kind === "node" ? index.topologyNodes : index.topologyEdges;
  return (
    values.find(
      (candidate) => !candidate.abstract && (candidate.properties?.length ?? 0) > 0,
    ) ?? values.at(0)
  );
}

/**
 * Move one selected subject to another level.
 *
 * The subject is the anchor: a property keeps its component when the selector
 * moves to Node or Abstract, and a component returns to its first property when
 * the selector moves back to Property. The fallback is deterministic.
 */
export function proofSubjectForLevel(
  index: ViewerIndex,
  subject: ProofSubject,
  level: ProofLevel,
): ProofSubject {
  if (subject.level === level) return subject;
  switch (level) {
    case "property": {
      if (
        (subject.kind === "node" || subject.kind === "edge") &&
        subject.component
      ) {
        return propertySubject(
          index,
          subject.kind,
          subject.component,
          subject.property ?? firstPropertyOf(index, subject.kind, subject.component) ?? "",
        );
      }
      return defaultProofSubject(index);
    }
    case "node":
    case "edge": {
      const kind: EntityKind = level;
      if (subject.kind === "node" || subject.kind === "edge") {
        const target = firstComponentOfKind(index, kind);
        return {
          level,
          kind,
          component:
            subject.kind === kind ? subject.component : target?.name ?? "",
        };
      }
      const target = firstComponentOfKind(index, kind);
      return { level, kind, component: target?.name ?? "" };
    }
    case "abstract": {
      if (subject.kind === "abstract") return subject;
      const node = abstractAncestor(
        index,
        subject.kind === "node" || subject.kind === "edge"
          ? subject.component
          : undefined,
      );
      return {
        level: "abstract",
        kind: "abstract",
        component: node?.name ?? defaultAbstractSubject(index).component,
      };
    }
    case "asset": {
      if (subject.kind === "asset") return subject;
      if (
        (subject.kind === "node" || subject.kind === "edge") &&
        subject.component
      ) {
        const property =
          subject.property ??
          firstPropertyOf(index, subject.kind, subject.component);
        if (property) {
          for (const entry of findComponentPropertyBindings(
            index,
            subject.kind,
            subject.component,
            property,
          )) {
            const assetName = entrySources(index, entry).assets.at(0);
            if (assetName) {
              return { level: "asset", kind: "asset", component: assetName };
            }
          }
        }
      }
      const asset = index.assets.at(0);
      return {
        level: "asset",
        kind: "asset",
        component: asset?.name ?? "",
      };
    }
  }
}

/** Every attached card the current proof exposes, deduplicated by subject. */
export function collectProofSemantics(model: ProofModel): ProofSemantics[] {
  return dedupeSemantics([
    ...model.rootSemantics,
    ...model.subjectSemantics,
    ...model.branches.flatMap((branch) => branch.semantics),
  ]);
}

/** Render one branch's lane order for the canvas and the trace panel. */
export function branchLaneNodes(branch: ProofBranch): Map<LineageLane, ProofNode[]> {
  const lanes = new Map<LineageLane, ProofNode[]>();
  for (const lane of LINEAGE_LANES) lanes.set(lane.id, []);
  for (const node of branch.nodes) {
    const group = lanes.get(node.lane) ?? [];
    group.push(node);
    lanes.set(node.lane, group);
  }
  return lanes;
}

/** A stable label for an artifact, kept here so the view does not format it. */
export function traceArtifactLabel(type: ArtifactType): string {
  return artifactDisplay(type);
}
