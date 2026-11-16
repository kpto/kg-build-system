/**
 * The two axes of a graph, read for one subject.
 *
 * A graph is an argument on two axes: the records the graph asserts (nodes and
 * edges) and the relations the domain supplies (source and derived relations).
 * A binding is the fulfilment that meets them: one relation's rows, at one
 * grain and identity, become the record's values.
 *
 * This module is a read model over the snapshot. It never invents a contract:
 * every fact it returns is read from a declaration, a binding or a row source.
 * When the snapshot omits a meaning or a contract, the map shows the absence.
 */

import { collectFieldRefs, logicalTypeName } from "@/lib/expressions";
import {
  findComponentPropertyBindings,
  relationNamesFromRowSource,
  resolveAssetName,
} from "@/lib/indexes";
import type {
  RelationDTO,
  ProjectionDTO,
  ViewerIndex,
} from "@/lib/types";
import { meaningText, recordSummary } from "@/lib/summary";

export type AxisSubjectKind =
  | "asset"
  | "relation"
  | "projection"
  | "node"
  | "edge"
  | "property"
  | "abstract";

export interface AxisSubject {
  kind: AxisSubjectKind;
  component: string;
  property?: string;
}

export interface AxisRecord {
  kind: "node" | "edge";
  name: string;
  labels: string[];
  abstract: boolean;
  description?: string;
  properties: Array<{ name: string; type: string }>;
  meaningCount: number;
}

export interface AxisRelation {
  kind: "source" | "derived";
  name: string;
  asset?: string;
  description?: string;
  columns: Array<{ name: string; type: string }>;
  /** Relations a derived relation scans; empty for a source relation. */
  scanned: string[];
  meaningCount: number;
}

export interface AxisBinding {
  index: number;
  targetKind: "node" | "edge";
  target: string;
  /** Relations the binding's row source reads. */
  relations: string[];
  identityFields: string[];
  propertyCount: number;
  rowSourceKind?: string;
  debugName?: string;
  purpose?: string;
  limitations: string[];
  meaningCount: number;
}

export interface AxisMap {
  subject: AxisSubject;
  graphPurpose?: string;
  records: AxisRecord[];
  bindings: AxisBinding[];
  relations: AxisRelation[];
}

function meaningCount(
  semantics:
    | { purpose?: unknown; claims?: unknown[]; frames?: unknown[] }
    | undefined,
): number {
  if (!semantics) return 0;
  return (
    (semantics.purpose ? 1 : 0) +
    (semantics.claims?.length ?? 0) +
    (semantics.frames?.length ?? 0)
  );
}

function relationModel(
  index: ViewerIndex,
  name: string,
): AxisRelation | undefined {
  const source = index.relationByName.get(name);
  if (source) return sourceRelationModel(index, source);
  const derived = index.projectionByName.get(name);
  if (derived) return derivedRelationModel(index, derived);
  return undefined;
}

function sourceRelationModel(
  index: ViewerIndex,
  relation: RelationDTO,
): AxisRelation {
  return {
    kind: "source",
    name: relation.name,
    asset: resolveAssetName(index, relation.name),
    description: recordSummary(relation),
    columns: (relation.columns ?? []).map((column) => ({
      name: column.name,
      type: logicalTypeName(column.logical_type),
    })),
    scanned: [],
    meaningCount: meaningCount(relation.meaning ?? relation.semantics),
  };
}

function derivedRelationModel(
  index: ViewerIndex,
  relation: ProjectionDTO,
): AxisRelation {
  return {
    kind: "derived",
    name: relation.name,
    asset: resolveAssetName(index, relation.name),
    description: recordSummary(relation),
    columns: (relation.columns ?? []).map((column) => ({
      name: column.name,
      type: logicalTypeName(column.logical_type),
    })),
    scanned: relationNamesFromRowSource(relation.row_source),
    meaningCount: meaningCount(relation.meaning ?? relation.semantics),
  };
}

function recordFor(
  index: ViewerIndex,
  kind: "node" | "edge",
  name: string,
): AxisRecord | undefined {
  const entity =
    kind === "node"
      ? index.topologyNodesByName.get(name)
      : index.topologyEdgesByName.get(name);
  if (!entity) return undefined;
  return {
    kind,
    name: entity.name,
    labels: entity.labels ?? [],
    abstract: Boolean(entity.abstract),
    description: meaningText(entity.meaning ?? entity.semantics) ?? entity.description,
    properties: (entity.properties ?? []).map((property) => ({
      name: property.name,
      type: logicalTypeName(property.logical_type),
    })),
    meaningCount: meaningCount(entity.meaning ?? entity.semantics),
  };
}

function bindingModel(
  index: ViewerIndex,
  binding: (typeof index.bindings)[number],
): AxisBinding {
  const identityFields = collectFieldRefs(binding.binding.identity).map(
    (ref) => ref[ref.length - 1] ?? "",
  );
  return {
    index: binding.index,
    targetKind: binding.kind,
    target: binding.component,
    relations: relationNamesFromRowSource(binding.binding.rows),
    identityFields: [...new Set(identityFields)].filter(Boolean),
    propertyCount: Object.keys(binding.binding.properties ?? {}).length,
    rowSourceKind: binding.binding.rows?.kind,
    debugName: binding.binding.name,
    purpose:
      binding.binding.semantics?.purpose?.text ??
      binding.binding.semantics?.frames?.[0]?.text,
    limitations:
      binding.binding.semantics?.purpose?.limitations?.map(
        (limitation) => limitation.text,
      ) ?? [],
    meaningCount: meaningCount(binding.binding.semantics),
  };
}

export function buildAxisMap(
  index: ViewerIndex,
  subject: AxisSubject,
): AxisMap | undefined {
  const graphPurpose = index.graphDeclaration?.semantics?.purpose?.text;
  const recordNames: Array<{ kind: "node" | "edge"; name: string }> = [];
  let bindings: AxisBinding[] = [];

  const bindingsFor = (kind: "node" | "edge", name: string) =>
    index.bindings
      .filter((binding) => binding.kind === kind && binding.component === name)
      .map((binding) => bindingModel(index, binding));

  switch (subject.kind) {
    case "node":
    case "edge": {
      recordNames.push({ kind: subject.kind, name: subject.component });
      bindings = bindingsFor(subject.kind, subject.component);
      break;
    }
    case "abstract": {
      const parents = new Map(
        index.topologyNodes.map((node) => [node.name, node.parent?.[2]]),
      );
      const descends = (name: string): boolean => {
        let current = parents.get(name);
        for (let depth = 0; current && depth < 64; depth += 1) {
          if (current === subject.component) return true;
          current = parents.get(current);
        }
        return false;
      };
      const descendants = index.topologyNodes
        .filter((node) => !node.abstract && descends(node.name))
        .slice(0, 96);
      for (const node of descendants) {
        recordNames.push({ kind: "node", name: node.name });
        bindings.push(...bindingsFor("node", node.name));
      }
      break;
    }
    case "property": {
      const kind = index.topologyNodesByName.has(subject.component)
        ? "node"
        : "edge";
      const entries = findComponentPropertyBindings(
        index,
        kind,
        subject.component,
        subject.property ?? "",
      );
      const seen = new Set<number>();
      bindings = entries
        .filter((entry) => {
          if (seen.has(entry.binding.index)) return false;
          seen.add(entry.binding.index);
          return true;
        })
        .map((entry) => bindingModel(index, entry.binding));
      recordNames.push({ kind, name: subject.component });
      break;
    }
    case "relation":
    case "projection": {
      const relation = relationModel(index, subject.component);
      bindings = index.bindings
        .filter((binding) =>
          relationNamesFromRowSource(binding.binding.rows).includes(
            subject.component,
          ),
        )
        .map((binding) => bindingModel(index, binding));
      if (!relation) return undefined;
      for (const binding of bindings) {
        recordNames.push({
          kind: binding.targetKind,
          name: binding.target,
        });
      }
      break;
    }
    case "asset": {
      const relationNames = [
        ...index.relations
          .filter(
            (relation) =>
              resolveAssetName(index, relation.name) === subject.component,
          )
          .map((relation) => relation.name),
        ...index.projections
          .filter(
            (relation) =>
              resolveAssetName(index, relation.name) === subject.component,
          )
          .map((relation) => relation.name),
      ];
      const relationSet = new Set(relationNames);
      bindings = index.bindings
        .filter((binding) =>
          relationNamesFromRowSource(binding.binding.rows).some((name) =>
            relationSet.has(name),
          ),
        )
        .map((binding) => bindingModel(index, binding));
      for (const binding of bindings) {
        recordNames.push({
          kind: binding.targetKind,
          name: binding.target,
        });
      }
      break;
    }
    default:
      return undefined;
  }

  const records = recordNames
    .map((record) => recordFor(index, record.kind, record.name))
    .filter((record): record is AxisRecord => Boolean(record));

  const relationNames = new Set<string>();
  for (const binding of bindings) {
    for (const name of binding.relations) relationNames.add(name);
  }
  if (subject.kind === "relation" || subject.kind === "projection") {
    relationNames.add(subject.component);
  }
  const relations = [...relationNames]
    .map((name) => relationModel(index, name))
    .filter((relation): relation is AxisRelation => Boolean(relation))
    .sort((left, right) => left.name.localeCompare(right.name));

  return {
    subject,
    graphPurpose,
    records: records.sort((left, right) => left.name.localeCompare(right.name)),
    bindings: bindings.sort((left, right) => left.index - right.index),
    relations,
  };
}

/** The relations a binding reads, for a compact map row. */
export function bindingRelations(binding: AxisBinding): string {
  return binding.relations.length ? binding.relations.join(", ") : "no row source";
}

/** A stable key for one fulfilment. */
export function fulfilmentKey(binding: AxisBinding): string {
  return `${binding.index}:${binding.targetKind}:${binding.target}`;
}

/** Keep the map honest about relation names the snapshot does not publish. */
export function unresolvedRelations(map: AxisMap): string[] {
  const known = new Set(map.relations.map((relation) => relation.name));
  return [
    ...new Set(map.bindings.flatMap((binding) => binding.relations)),
  ].filter((name) => !known.has(name));
}
