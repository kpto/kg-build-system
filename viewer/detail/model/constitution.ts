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
import { relationNamesFromRowSource } from "@/lib/indexes";
import type { IndexedBinding, ViewerIndex } from "@/lib/types";

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
  /** The one purpose the subject is read under. */
  purpose: ConstitutionNode;
  /** Record-axis levels, ordered from the root toward the subject. */
  graph: ConstitutionNode[];
  /** Every relation a binding reads, each with its full provenance. */
  relation: ConstitutionRelation[];
  /** One node per binding; together they are the record's fulfilment. */
  bindings: ConstitutionBinding[];
}

export interface ConstitutionSubjectLike {
  level: string;
  kind?: string;
  component: string;
  property?: string;
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
    default:
      return graphMeaning(index);
  }
}

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
 * A binding comes to be at the meeting of a record and a relation: the target
 * record (its purpose and identity only) and the relations it reads. The
 * record's graph ancestry belongs to the record's own constitution.
 */
function bindingConstitution(
  index: ViewerIndex,
  subject: ConstitutionSubjectLike,
): ConstitutionModel {
  const binding = index.bindings.find(
    (candidate) => candidate.index === subject.bindingIndex,
  );
  const purpose: ConstitutionNode = {
    kind: "binding",
    name: binding ? bindingDisplayName(binding) : `binding #${subject.bindingIndex ?? "?"}`,
    label: "Purpose",
    meaning: subjectMeaning(index, subject),
    current: true,
  };
  if (!binding) return { purpose, graph: [], relation: [], bindings: [] };

  const identity = [
    ...new Set(
      collectFieldRefs(binding.binding.identity)
        .map((ref) => ref[ref.length - 1])
        .filter((name): name is string => Boolean(name)),
    ),
  ];
  const target: ConstitutionNode = {
    kind: binding.kind,
    name: binding.component,
    label: LABELS[binding.kind],
    meaning: componentMeaning(index, binding.kind, binding.component),
    detail: identity.length
      ? `identity ${identity.join(", ")}`
      : "identity not declared",
    open: { kind: binding.kind, name: binding.component },
  };

  return {
    purpose,
    graph: [target],
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
