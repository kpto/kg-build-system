/**
 * The constitution of one subject: how it comes to be.
 *
 * The subject's purpose is the root; the declarations that bring it into being
 * hang below it and every edge follows production (supply → subject). What
 * constitutes a subject depends on its kind:
 *
 * - a record (node, edge, property, abstract category) is produced by its
 *   bindings, each supplied by a relation and that relation's provenance; its
 *   graph ancestry states where it sits;
 * - a source relation is produced by its asset, and an asset is the origin;
 * - a derived relation is produced by the source relations it scans and their
 *   assets;
 * - a binding is the meeting of a record and a relation: its components are the
 *   target record (purpose and identity only) and the relations it reads.
 *
 * The purpose box carries the subject's own concept mark. A declaration shared
 * by several consumers is one node with one edge per consumer. A level keeps
 * its own meaning, so the branches show production and supply, never inherited
 * text.
 */

import {
  axisRelationFor,
  buildAxisMap,
  type AxisBinding,
  type AxisMap,
  type AxisRelation,
  type AxisSubject,
} from "@/lib/axis";
import { collectFieldRefs } from "@/lib/expressions";
import { relationNamesFromRowSource, resolveAssetName, stepKey } from "@/lib/indexes";
import type { IndexedBinding, ViewerIndex } from "@/lib/types";
import type { CollectionId } from "@/workbench/collections";

import {
  attachedMeaning,
  componentMeaning,
  graphMeaning,
  propertyMeaning,
  purposeLevels,
  type DesignMeaningValue,
  type PurposeLevel,
  type PurposeLevelKind,
} from "@/shared/design/meaning";

export type ConstitutionTarget =
  | { kind: "node" | "edge"; name: string }
  | { kind: "abstract"; name: string }
  | { kind: "relation"; name: string }
  | { kind: "projection"; name: string }
  | { kind: "asset"; name: string };

/** The frame a box sits in; a workflow subject adds the workflow frame. */
export type ConstitutionFrameId =
  | "graph"
  | "fulfilment"
  | "relation"
  | "workflow"
  | "layers";

/** One box in the constitution tree. */
export interface ConstitutionNode {
  kind: PurposeLevelKind;
  name: string;
  label: string;
  meaning: DesignMeaningValue;
  current?: boolean;
  /** Extra grouping fact, such as `+3 records`. */
  detail?: string;
  /** A document this box can open; the current box has none. */
  open?: ConstitutionTarget;
  /** Short body text for a box with no semantic meaning, such as a layer. */
  text?: string;
  /** The virtual collection this box opens, when it is a layer. */
  collection?: { id: CollectionId; component?: string };
  /** The owner when the box is a step or a binding. */
  component?: string;
  /** The step identity when the box is a step. */
  stepId?: [string, string];
  /** An explicit frame, used by layer and workflow boxes. */
  frame?: ConstitutionFrameId;
}

/** One relation and its provenance: scanned relations, then the asset. */
export interface ConstitutionRelation {
  node: ConstitutionNode;
  children: ConstitutionRelation[];
}

/** One binding: the meeting of one relation and one record. */
export interface ConstitutionBinding {
  index: number;
  /** The binding's display handle; a binding name is not its identity. */
  name: string;
  /** The record the binding writes, so its pill can open that document. */
  component: string;
  /** The relations this binding's row source reads. */
  relations: string[];
  purpose?: string;
  meaning: DesignMeaningValue;
}

export interface ConstitutionModel {
  /** The direction this DAG reads: below the subject or one level above it. */
  direction?: "dependency" | "contribution";
  /** The one purpose the subject is read under. */
  purpose: ConstitutionNode;
  /** Record-axis levels, ordered from the root toward the subject. */
  graph: ConstitutionNode[];
  /** Every relation a binding reads, each with its full provenance. */
  relation: ConstitutionRelation[];
  /** One node per binding; together they are the record's fulfilment. */
  bindings: ConstitutionBinding[];
  /** Workflow steps below or above a step subject. */
  workflow?: ConstitutionNode[];
  /** A collection's layer DAG: the layers below or above the purpose. */
  layers?: ConstitutionNode[];
  /** Explicit edges between layer boxes, by scene node id. */
  layerEdges?: Array<{ source: string; target: string }>;
  /** A note shown when the DAG has no layer or component. */
  note?: string;
}

export interface ConstitutionSubjectLike {
  level: string;
  kind?: string;
  component: string;
  property?: string;
  /** The display name when it differs from the owner component, as for a step. */
  name?: string;
  /** The step identity when the subject is a workflow step. */
  stepId?: [string, string];
  /** The binding's index when the subject is a binding document. */
  bindingIndex?: number;
}

const LABELS: Record<PurposeLevelKind, string> = {
  graph: "Purpose",
  abstract: "Category",
  node: "Node",
  edge: "Edge",
  property: "Property",
  asset: "Asset",
  relation: "Source relation",
  projection: "Derived relation",
  binding: "Binding",
  step: "Step",
};

/** The purpose box carries the subject's own concept, never the graph mark. */
const SUBJECT_CONCEPTS: Record<string, PurposeLevelKind> = {
  property: "property",
  node: "node",
  edge: "edge",
  abstract: "abstract",
  asset: "asset",
  relation: "relation",
  projection: "projection",
  binding: "binding",
  step: "step",
};

function subjectConcept(subject: ConstitutionSubjectLike): PurposeLevelKind {
  return SUBJECT_CONCEPTS[subject.level] ?? "graph";
}

/** Map a detail subject onto the axis subject the fulfilment read model takes. */
export function axisSubjectFor(
  subject: ConstitutionSubjectLike,
): AxisSubject | undefined {
  switch (subject.level) {
    case "property":
      return {
        kind: "property",
        component: subject.component,
        property: subject.property,
      };
    case "node":
    case "edge":
    case "abstract":
    case "asset":
    case "relation":
    case "projection":
      return { kind: subject.level, component: subject.component };
    default:
      return undefined;
  }
}

function subjectMeaning(
  index: ViewerIndex,
  subject: ConstitutionSubjectLike,
): DesignMeaningValue {
  switch (subject.level) {
    case "property": {
      const kind = index.topologyNodesByName.has(subject.component)
        ? "node"
        : "edge";
      return propertyMeaning(
        index,
        kind,
        subject.component,
        subject.property ?? "",
      );
    }
    case "node":
    case "edge":
      return componentMeaning(index, subject.level, subject.component);
    case "abstract":
      return componentMeaning(index, "node", subject.component);
    case "asset": {
      const asset = index.assetsByName.get(subject.component);
      return attachedMeaning(asset?.meaning ?? asset?.semantics);
    }
    case "relation": {
      const relation = index.relationByName.get(subject.component);
      return attachedMeaning(relation?.meaning ?? relation?.semantics);
    }
    case "projection": {
      const projection = index.projectionByName.get(subject.component);
      return attachedMeaning(projection?.meaning ?? projection?.semantics);
    }
    case "binding": {
      const binding = index.bindings.find(
        (candidate) => candidate.index === subject.bindingIndex,
      );
      return attachedMeaning(binding?.binding.meaning ?? binding?.binding.semantics);
    }
    case "step":
      return EMPTY_MEANING;
    default:
      return graphMeaning(index);
  }
}

/** A step and a collection layer carry no semantic purpose of their own. */
export const EMPTY_MEANING: DesignMeaningValue = {
  purpose: undefined,
  claims: [],
  limitations: [],
  frames: [],
};

function relationMeaning(index: ViewerIndex, name: string): DesignMeaningValue {
  const source = index.relationByName.get(name);
  if (source) {
    return attachedMeaning(source.meaning ?? source.semantics);
  }
  const derived = index.projectionByName.get(name);
  return attachedMeaning(derived?.meaning ?? derived?.semantics);
}

function assetMeaning(index: ViewerIndex, name: string): DesignMeaningValue {
  const asset = index.assetsByName.get(name);
  return attachedMeaning(asset?.meaning ?? asset?.semantics);
}

function bindingMeaning(
  index: ViewerIndex,
  binding: AxisBinding,
): DesignMeaningValue {
  const declaration = index.bindings.find(
    (candidate) => candidate.index === binding.index,
  )?.binding;
  if (declaration) {
    return attachedMeaning(declaration.meaning ?? declaration.semantics);
  }
  return {
    purpose: binding.purpose,
    limitations: binding.limitations.map((text) => ({ text })),
    claims: [],
    frames: [],
  };
}

function purposeNode(level: PurposeLevel): ConstitutionNode {
  const open =
    level.kind === "abstract"
      ? ({ kind: "abstract", name: level.name } as const)
      : level.kind === "node" || level.kind === "edge"
        ? ({ kind: level.kind, name: level.name } as const)
        : level.kind === "asset"
          ? ({ kind: "asset", name: level.name } as const)
          : undefined;
  return {
    kind: level.kind,
    name: level.name,
    label: level.kind === "graph" ? "Graph" : LABELS[level.kind],
    meaning: level.meaning,
    current: level.current,
    ...(open ? { open } : {}),
  };
}

function relationNode(
  index: ViewerIndex,
  relation: AxisRelation,
  current: boolean,
): ConstitutionNode {
  const kind = relation.kind === "source" ? "relation" : "projection";
  return {
    kind,
    name: relation.name,
    label: LABELS[kind],
    meaning: relationMeaning(index, relation.name),
    current,
    open: { kind, name: relation.name },
  };
}

function assetNode(
  index: ViewerIndex,
  name: string,
  current: boolean,
): ConstitutionNode {
  return {
    kind: "asset",
    name,
    label: LABELS.asset,
    meaning: assetMeaning(index, name),
    current,
    open: { kind: "asset", name },
  };
}

function relationKey(relation: AxisRelation): string {
  return `${relation.kind === "source" ? "relation" : "projection"}:${relation.name}`;
}

/**
 * One relation's provenance: a derived relation reads its scanned relations,
 * and an asset-backed source relation shows its asset. Every scanned relation
 * is kept, not just the first, and the asset hangs under the source relation.
 */
function relationTree(
  index: ViewerIndex,
  relation: AxisRelation,
  subject: ConstitutionSubjectLike,
  seen: Set<string>,
): ConstitutionRelation {
  const key = relationKey(relation);
  const node = relationNode(
    index,
    relation,
    (subject.level === "relation" || subject.level === "projection") &&
      relation.name === subject.component,
  );
  if (seen.has(key)) return { node, children: [] };
  const next = new Set(seen).add(key);
  const children: ConstitutionRelation[] = [];
  if (relation.kind === "derived") {
    for (const name of relation.scanned) {
      const scanned = axisRelationFor(index, name);
      if (scanned) children.push(relationTree(index, scanned, subject, next));
    }
  }
  // A source relation is asset-backed. A derived relation's asset is reached
  // through its scanned source relations; only a relation with no scanned
  // relation falls back to its own resolved asset.
  const assetName =
    relation.kind === "source"
      ? relation.asset
      : relation.scanned.length
        ? undefined
        : relation.asset;
  if (assetName) {
    children.push({
      node: assetNode(
        index,
        assetName,
        subject.level === "asset" && subject.component === assetName,
      ),
      children: [],
    });
  }
  return { node, children };
}

/**
 * The subject's own components.
 *
 * A record's components are the relations its bindings read; a source
 * relation's is its asset; a derived relation's are the source relations it
 * scans and their assets; an asset is the origin and has none. The subject
 * itself is the purpose box, so it is not repeated in the branch.
 */
function relationTrees(
  index: ViewerIndex,
  subject: ConstitutionSubjectLike,
  map: AxisMap | undefined,
): ConstitutionRelation[] {
  if (subject.level === "asset" || subject.level === "binding") return [];
  const relations = map?.relations ?? [];
  const isRelationSubject =
    subject.level === "relation" || subject.level === "projection";
  if (isRelationSubject) {
    const relation =
      relations.find((entry) => entry.name === subject.component) ??
      axisRelationFor(index, subject.component);
    if (!relation) return [];
    return relationTree(index, relation, subject, new Set()).children;
  }
  return relations.map((relation) =>
    relationTree(index, relation, subject, new Set()),
  );
}

/**
 * The relations a binding reads, each with its own provenance. The binding is
 * the meeting, so neither side is repeated as the subject.
 */
function bindingRelations(
  index: ViewerIndex,
  binding: IndexedBinding,
  subject: ConstitutionSubjectLike,
): ConstitutionRelation[] {
  return [...new Set(relationNamesFromRowSource(binding.binding.rows))]
    .map((name) => axisRelationFor(index, name))
    .filter((relation): relation is AxisRelation => Boolean(relation))
    .map((relation) => relationTree(index, relation, subject, new Set()));
}

function bindingDisplayName(binding: IndexedBinding): string {
  return (
    binding.binding.name ??
    binding.binding.debug_name ??
    `binding #${binding.index}`
  );
}

/**
 * A binding comes to be from the relations it reads. Its target record is one
 * level above and belongs to the binding's Contribution, not its Constitution.
 */
function bindingConstitution(
  index: ViewerIndex,
  subject: ConstitutionSubjectLike,
): ConstitutionModel {
  const binding = index.bindings.find(
    (candidate) => candidate.index === subject.bindingIndex,
  );
  const purpose = purposeFor(index, subject);
  if (!binding) {
    return { purpose, graph: [], relation: [], bindings: [] };
  }
  return {
    purpose,
    graph: [],
    relation: bindingRelations(index, binding, subject),
    bindings: [],
  };
}

function bindingSummaries(
  index: ViewerIndex,
  map: AxisMap | undefined,
): ConstitutionBinding[] {
  const bindings = map?.bindings ?? [];
  return bindings.map((binding) => ({
    index: binding.index,
    name: binding.debugName ?? `binding #${binding.index}`,
    component: binding.target,
    relations: binding.relations,
    purpose: binding.purpose,
    meaning: bindingMeaning(index, binding),
  }));
}

/**
 * Read how one subject comes to be.
 *
 * The purpose box is the subject. A record hangs its bindings, graph ancestry
 * and each binding's relation provenance below it; a relation hangs only the
 * declarations that produce it; a binding hangs its target record and the
 * relations it reads; an asset is the origin and has no constitution.
 */
export function constitutionModel(
  index: ViewerIndex,
  subject: ConstitutionSubjectLike,
): ConstitutionModel {
  if (subject.level === "binding") {
    return bindingConstitution(index, subject);
  }
  const axis = axisSubjectFor(subject);
  const map = axis ? buildAxisMap(index, axis) : undefined;
  const recordSubject =
    subject.level === "node" ||
    subject.level === "edge" ||
    subject.level === "abstract" ||
    subject.level === "property";
  const purpose: ConstitutionNode = {
    kind: subjectConcept(subject),
    name:
      subject.level === "property"
        ? `${subject.component}.${subject.property ?? ""}`
        : subject.component,
    label: "Purpose",
    meaning: subjectMeaning(index, subject),
    current: true,
  };
  if (!recordSubject) {
    return {
      purpose,
      graph: [],
      relation: relationTrees(index, subject, map),
      bindings: [],
    };
  }
  const graph = purposeLevels(index, subject)
    .slice(0, -1)
    .reverse()
    .map(purposeNode);
  return {
    purpose,
    graph,
    relation: relationTrees(index, subject, map),
    bindings: bindingSummaries(index, map),
  };
}

// ---------------------------------------------------------------------------
// Contribution and workflow boundaries
// ---------------------------------------------------------------------------

function purposeFor(
  index: ViewerIndex,
  subject: ConstitutionSubjectLike,
): ConstitutionNode {
  const step = subject.level === "step";
  const binding =
    subject.level === "binding"
      ? index.bindings.find(
          (candidate) => candidate.index === subject.bindingIndex,
        )
      : undefined;
  const name =
    subject.level === "property"
      ? `${subject.component}.${subject.property ?? ""}`
      : subject.name ??
        (binding
          ? bindingDisplayName(binding)
          : subject.level === "binding"
            ? `binding #${subject.bindingIndex ?? "?"}`
            : subject.component);
  return {
    kind: subjectConcept(subject),
    name,
    label: "Purpose",
    meaning: subjectMeaning(index, subject),
    current: true,
    ...(step
      ? {
          text: "Build step",
          component: subject.stepId?.[0] ?? subject.component,
          stepId: subject.stepId,
        }
      : {}),
  };
}

function contributionRecordNode(
  index: ViewerIndex,
  kind: "node" | "edge" | "abstract",
  name: string,
  detail?: string,
): ConstitutionNode {
  const declaration = index.topologyComponentsByName.get(name);
  const labels = declaration?.labels ?? [];
  const identity = detail ?? (labels.length ? labels.join(" · ") : undefined);
  return {
    kind,
    name,
    label: LABELS[kind],
    meaning:
      kind === "abstract"
        ? componentMeaning(index, "node", name)
        : componentMeaning(index, kind, name),
    detail: identity,
    open:
      kind === "abstract"
        ? { kind: "abstract", name }
        : { kind, name },
    text: undefined,
  };
}

function endpointsDetail(edge: {
  source?: readonly string[];
  target?: readonly string[];
}): string | undefined {
  const source = edge.source?.[2];
  const target = edge.target?.[2];
  return source && target ? `${source} → ${target}` : undefined;
}

function contributionBinding(
  index: ViewerIndex,
  binding: IndexedBinding,
): ConstitutionBinding {
  const meaning = attachedMeaning(
    binding.binding.meaning ?? binding.binding.semantics,
  );
  return {
    index: binding.index,
    name: bindingDisplayName(binding),
    component: binding.component,
    relations: [],
    purpose:
      binding.binding.semantics?.purpose?.text ??
      binding.binding.meaning?.purpose?.text,
    meaning,
  };
}

function identityDetail(binding: IndexedBinding): string | undefined {
  const identity = [
    ...new Set(
      collectFieldRefs(binding.binding.identity)
        .map((ref) => ref[ref.length - 1])
        .filter((name): name is string => Boolean(name)),
    ),
  ];
  return identity.length ? `identity ${identity.join(", ")}` : undefined;
}

const CONTRIBUTION_LIMIT = 10;

interface ContributionGroup {
  kind: PurposeLevelKind;
  title: string;
  note: string;
  frame: ConstitutionFrameId;
  collection?: { id: CollectionId };
  count: number;
}

function groupFor(kind: PurposeLevelKind): ContributionGroup | undefined {
  switch (kind) {
    case "asset":
      return { kind, title: "Assets", note: "assets behind this subject", frame: "relation", collection: { id: "assets" }, count: 0 };
    case "relation":
      return { kind, title: "Source relations", note: "source relations that read this subject", frame: "relation", collection: { id: "sourceRelations" }, count: 0 };
    case "projection":
      return { kind, title: "Derived relations", note: "derived relations that scan this subject", frame: "relation", collection: { id: "derivedRelations" }, count: 0 };
    case "binding":
      return { kind, title: "Bindings", note: "bindings that read this subject directly", frame: "fulfilment", collection: { id: "bindings" }, count: 0 };
    case "node":
      return { kind, title: "Nodes", note: "records directly under this subject", frame: "graph", collection: { id: "nodes" }, count: 0 };
    case "edge":
      return { kind, title: "Edges", note: "edges incident on this subject", frame: "graph", collection: { id: "edges" }, count: 0 };
    case "abstract":
      return { kind, title: "Abstract", note: "child categories directly under this subject", frame: "graph", collection: { id: "abstract" }, count: 0 };
    case "step":
      return { kind, title: "Steps", note: "steps that read this step", frame: "workflow", count: 0 };
    default:
      return undefined;
  }
}

/**
 * A large contribution set is read at layer resolution: one linked box per kind
 * instead of an unreadable field of boxes. A small set keeps every participant.
 */
function collapseContribution(model: ConstitutionModel): void {
  const total =
    model.graph.length +
    model.relation.length +
    model.bindings.length +
    (model.workflow?.length ?? 0);
  if (total <= CONTRIBUTION_LIMIT) return;

  const groups = new Map<PurposeLevelKind, ContributionGroup>();
  const add = (kind: PurposeLevelKind) => {
    const group = groups.get(kind) ?? groupFor(kind);
    if (!group) return;
    group.count += 1;
    groups.set(kind, group);
  };
  model.graph.forEach((node) => add(node.kind));
  model.relation.forEach((relation) => add(relation.node.kind));
  model.bindings.forEach(() => add("binding"));
  (model.workflow ?? []).forEach((node) => add(node.kind));

  const boxes: ConstitutionNode[] = [...groups.values()].map((group) => ({
    kind: group.kind,
    name: group.title,
    label: "Collection",
    meaning: EMPTY_MEANING,
    detail: `${group.count}`,
    text: group.note,
    collection: group.collection,
    frame: group.frame,
  }));
  model.graph = boxes;
  model.relation = [];
  model.bindings = [];
  model.workflow = [];
  model.note = undefined;
}

function abstractContributionNodes(
  index: ViewerIndex,
  name: string,
): ConstitutionNode[] {
  const nodes: ConstitutionNode[] = [];
  for (const child of index.topologyNodes) {
    if (child.parent?.[2] !== name) continue;
    nodes.push(
      contributionRecordNode(
        index,
        child.abstract ? "abstract" : "node",
        child.name,
      ),
    );
  }
  for (const child of index.topologyEdges) {
    if (child.parent?.[2] !== name) continue;
    nodes.push(
      contributionRecordNode(index, "edge", child.name, endpointsDetail(child)),
    );
  }
  return nodes;
}

function stepNode(index: ViewerIndex, id: [string, string]): ConstitutionNode {
  const step = index.stepsById.get(stepKey(id));
  return {
    kind: "step",
    name: id[1],
    label: "Step",
    meaning: EMPTY_MEANING,
    component: id[0],
    stepId: id,
    detail: step?.instruction.kind?.join(":") ?? undefined,
    text: "Build step",
    frame: "workflow",
  };
}

/**
 * One step's boundary: the steps that produce it (dependency) or the steps that
 * read it (contribution). A workflow box carries no design meaning.
 */
export function stepBoundaryModel(
  index: ViewerIndex,
  subject: ConstitutionSubjectLike,
  direction: "dependency" | "contribution",
): ConstitutionModel {
  const purpose = purposeFor(index, subject);
  const key = subject.stepId ? stepKey(subject.stepId) : undefined;
  const seen = new Set<string>();
  const workflow: ConstitutionNode[] = [];
  if (key) {
    const connections =
      direction === "dependency"
        ? index.incomingByStepId.get(key) ?? []
        : index.outgoingByStepId.get(key) ?? [];
    for (const connection of connections) {
      const id =
        direction === "dependency"
          ? connection.outputStepId
          : connection.inputStepId;
      const idKey = stepKey(id);
      if (seen.has(idKey)) continue;
      seen.add(idKey);
      workflow.push(stepNode(index, id));
    }
  }
  return {
    direction,
    purpose,
    graph: [],
    relation: [],
    bindings: [],
    workflow,
    note:
      direction === "dependency"
        ? "No step produces what this step reads."
        : "No step reads what this step produces.",
  };
}

/**
 * The immediate contribution of one participant: exactly one level above.
 *
 * An asset contributes its source relations; a relation contributes the derived
 * relations that scan it and the bindings that read it directly; a binding
 * contributes the record it writes; a node contributes its incident edges; a
 * property contributes its owning record; an abstract participant contributes
 * its immediate children; a step contributes its downstream steps.
 */
export function contributionModel(
  index: ViewerIndex,
  subject: ConstitutionSubjectLike,
): ConstitutionModel {
  const purpose = purposeFor(index, subject);
  const model: ConstitutionModel = {
    direction: "contribution",
    purpose,
    graph: [],
    relation: [],
    bindings: [],
    note: "No contribution is declared.",
  };

  switch (subject.level) {
    case "asset": {
      for (const relation of index.relations) {
        if (resolveAssetName(index, relation.name) !== subject.component) continue;
        const axis = axisRelationFor(index, relation.name);
        if (axis) {
          model.relation.push({
            node: relationNode(index, axis, false),
            children: [],
          });
        }
      }
      model.note = "No source relation reads this asset.";
      break;
    }
    case "relation":
    case "projection": {
      for (const projection of index.projections) {
        if (projection.name === subject.component) continue;
        if (
          !relationNamesFromRowSource(projection.row_source).includes(
            subject.component,
          )
        ) {
          continue;
        }
        const axis = axisRelationFor(index, projection.name);
        if (axis) {
          model.relation.push({
            node: relationNode(index, axis, false),
            children: [],
          });
        }
      }
      for (const binding of index.bindings) {
        if (
          !relationNamesFromRowSource(binding.binding.rows).includes(
            subject.component,
          )
        ) {
          continue;
        }
        model.bindings.push(contributionBinding(index, binding));
      }
      model.note = "No derived relation or binding reads this relation.";
      break;
    }
    case "binding": {
      const binding = index.bindings.find(
        (candidate) => candidate.index === subject.bindingIndex,
      );
      if (binding) {
        model.graph.push(
          contributionRecordNode(
            index,
            binding.kind,
            binding.component,
            identityDetail(binding),
          ),
        );
      }
      model.note = "This binding writes no record.";
      break;
    }
    case "node": {
      for (const edge of index.topologyEdges) {
        if (edge.abstract) continue;
        if (
          edge.source?.[2] !== subject.component &&
          edge.target?.[2] !== subject.component
        ) {
          continue;
        }
        model.graph.push(
          contributionRecordNode(index, "edge", edge.name, endpointsDetail(edge)),
        );
      }
      model.note = "No edge touches this node.";
      break;
    }
    case "edge":
      model.note = "An edge has no dependant: its endpoints are dependencies.";
      break;
    case "property": {
      const ownerKind = index.topologyNodesByName.has(subject.component)
        ? ("node" as const)
        : ("edge" as const);
      model.graph.push(contributionRecordNode(index, ownerKind, subject.component));
      model.note = "No record owns this property.";
      break;
    }
    case "abstract": {
      model.graph.push(...abstractContributionNodes(index, subject.component));
      model.note =
        "No child category, node or edge sits directly under this category.";
      break;
    }
    case "step":
      return stepBoundaryModel(index, subject, "contribution");
  }

  collapseContribution(model);
  return model;
}
