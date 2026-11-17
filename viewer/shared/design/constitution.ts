/**
 * The constitution of one subject: its purpose, the graph axis that asserts it
 * and the relation axis that fulfils it.
 *
 * The current subject's purpose is the root. The graph branch holds its
 * ancestry below, from the immediate parent down to the graph purpose; the
 * relation branch holds the provenance that supplies it, from the relation
 * down to the asset. The fulfilment box sits on the right,
 * above the separator and inset above the relation axis. A level keeps its own
 * meaning, so the two branches show derivation and supply, never inherited
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
} from "./meaning";

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
  /** Relation-axis levels, ordered from the relation toward the asset. */
  relation: ConstitutionNode[];
  binding?: ConstitutionBinding;
  /** The subject the full axis map reads. */
  axis?: AxisSubject;
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
  detail?: string,
): ConstitutionNode {
  const kind = relation.kind === "source" ? "relation" : "projection";
  return {
    kind,
    name: relation.name,
    label: LABELS[kind],
    meaning: relationMeaning(index, relation.name),
    current,
    ...(detail ? { detail } : {}),
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

function relationLevels(
  index: ViewerIndex,
  subject: ConstitutionSubjectLike,
  map: AxisMap | undefined,
): ConstitutionNode[] {
  const relations = map?.relations ?? [];
  const isRelationSubject =
    subject.level === "relation" || subject.level === "projection";
  const primary = isRelationSubject
    ? (relations.find((relation) => relation.name === subject.component) ??
      axisRelationFor(index, subject.component))
    : relations[0];
  const nodes: ConstitutionNode[] = [];
  if (primary) {
    nodes.push(
      relationNode(
        index,
        primary,
        isRelationSubject && primary.name === subject.component,
        relations.length > 1 ? `+${relations.length - 1} relations` : undefined,
      ),
    );
    if (primary.kind === "derived") {
      const scanned = primary.scanned
        .map(
          (name) =>
            relations.find((relation) => relation.name === name) ??
            axisRelationFor(index, name),
        )
        .filter((relation): relation is AxisRelation => Boolean(relation));
      const field = scanned[0];
      if (field) {
        nodes.push(
          relationNode(
            index,
            field,
            false,
            scanned.length > 1 ? `+${scanned.length - 1} scanned` : undefined,
          ),
        );
      }
    }
  }
  const assetName =
    subject.level === "asset"
      ? subject.component
      : (primary?.asset ??
        (primary ? resolveAssetName(index, primary.name) : undefined));
  if (assetName) {
    nodes.push(assetNode(index, assetName, subject.level === "asset"));
  }
  return nodes;
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
  const relation = relationLevels(index, subject, map);
  const binding = bindingSummary(index, map);
  return {
    purpose,
    graph,
    relation,
    ...(binding ? { binding } : {}),
    ...(axis ? { axis } : {}),
  };
}
