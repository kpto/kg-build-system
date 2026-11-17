/**
 * The constitution of one subject: its purpose, the graph axis that asserts it
 * and the relation axis that fulfils it.
 *
 * The current subject's purpose is the root. The graph branch holds its
 * ancestry below, from the immediate parent down to the graph purpose; the
 * relation branch holds every relation the bindings read, each derived relation
 * with all its scanned relations and each source relation with its asset. The
 * fulfilment box sits one row lower on the right, linked to the purpose; the
 * graph tree hangs from the purpose and the relation tree from the fulfilment.
 * A level keeps its own meaning, so the two branches show derivation and
 * supply, never inherited text.
 */

import {
  axisRelationFor,
  buildAxisMap,
  type AxisBinding,
  type AxisMap,
  type AxisRelation,
  type AxisSubject,
} from "@/lib/axis";
import { resolveAssetName } from "@/lib/indexes";
import type { ViewerIndex } from "@/lib/types";

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

/** The fulfilment box: what meets the two axes, summarised. */
export interface ConstitutionBinding {
  count: number;
  identity: string[];
  properties: number;
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
  binding?: ConstitutionBinding;
}

export interface ConstitutionSubjectLike {
  level: string;
  kind?: string;
  component: string;
  property?: string;
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
    default:
      return graphMeaning(index);
  }
}

function graphPurposeNode(index: ViewerIndex): ConstitutionNode {
  return {
    kind: "graph",
    name: index.graphDeclaration?.name ?? "graph",
    label: "Graph",
    meaning: graphMeaning(index),
  };
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

function recordNode(
  index: ViewerIndex,
  record: NonNullable<AxisMap["records"][number]>,
): ConstitutionNode {
  return {
    kind: record.kind,
    name: record.name,
    label: LABELS[record.kind],
    meaning: componentMeaning(index, record.kind, record.name),
    open: { kind: record.kind, name: record.name },
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

function recordLevels(
  index: ViewerIndex,
  subject: ConstitutionSubjectLike,
  map: AxisMap | undefined,
): ConstitutionNode[] {
  const records = map?.records ?? [];
  if (!records.length) return [];
  const first = recordNode(index, records[0]);
  if (records.length > 1) first.detail = `+${records.length - 1} records`;
  return [first];
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

/** Every relation the bindings read, each rooted with its own provenance. */
function relationTrees(
  index: ViewerIndex,
  subject: ConstitutionSubjectLike,
  map: AxisMap | undefined,
): ConstitutionRelation[] {
  const relations = map?.relations ?? [];
  const isRelationSubject =
    subject.level === "relation" || subject.level === "projection";
  const roots = isRelationSubject
    ? [
        relations.find((relation) => relation.name === subject.component) ??
          axisRelationFor(index, subject.component),
      ].filter((relation): relation is AxisRelation => Boolean(relation))
    : relations;
  return roots.map((relation) => relationTree(index, relation, subject, new Set()));
}

function bindingSummary(
  index: ViewerIndex,
  map: AxisMap | undefined,
): ConstitutionBinding | undefined {
  const bindings = map?.bindings ?? [];
  if (!bindings.length) return undefined;
  const identity = [
    ...new Set(bindings.flatMap((binding) => binding.identityFields)),
  ].slice(0, 3);
  const properties = bindings.reduce(
    (total, binding) => total + binding.propertyCount,
    0,
  );
  const only = bindings.length === 1 ? bindings[0] : undefined;
  return {
    count: bindings.length,
    identity,
    properties,
    ...(only?.purpose ? { purpose: only.purpose } : {}),
    meaning: only
      ? bindingMeaning(index, only)
      : {
          limitations: [],
          claims: [],
          frames: [],
        },
  };
}

/**
 * Read the constitution for one subject.
 *
 * The root is the current subject's purpose. The graph branch lists its
 * ancestry below, from the immediate parent down to the graph purpose; a
 * relation or asset subject lists the records it fulfils instead. Both cases
 * carry the relation tree and its fulfilment box, so the two axes are read
 * together rather than in separate cards.
 */
export function constitutionModel(
  index: ViewerIndex,
  subject: ConstitutionSubjectLike,
): ConstitutionModel {
  const axis = axisSubjectFor(subject);
  const map = axis ? buildAxisMap(index, axis) : undefined;
  const recordSubject =
    subject.level === "node" ||
    subject.level === "edge" ||
    subject.level === "abstract" ||
    subject.level === "property";
  const purpose: ConstitutionNode = {
    kind: "graph",
    name:
      subject.level === "property"
        ? `${subject.component}.${subject.property ?? ""}`
        : subject.component,
    label: LABELS.graph,
    meaning: subjectMeaning(index, subject),
    current: true,
  };
  const graph = recordSubject
    ? purposeLevels(index, subject)
        .slice(0, -1)
        .reverse()
        .map(purposeNode)
    : [...recordLevels(index, subject, map), graphPurposeNode(index)];
  const relation = relationTrees(index, subject, map);
  const binding = bindingSummary(index, map);
  return {
    purpose,
    graph,
    relation,
    ...(binding ? { binding } : {}),
  };
}
