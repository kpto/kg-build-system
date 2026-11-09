/**
 * Coverage matrix over topology properties.
 *
 * A row is one topology property; a column is a source relation reachable from
 * that property's bindings. The matrix answers which source actually feeds a
 * property and how much of that property is traced versus literal.
 */

import type { CoverageMatrix } from "./reviewTypes";
import type {
  EntityKind,
  Ref,
  StepId,
  TopologyProperty,
  ViewerIndex,
} from "./types";
import {
  findComponentPropertyBindings,
  relationNamesFromRowSource,
} from "./indexes";
import { collectFieldRefs, fieldRefKey, walkExpression } from "./expressions";

interface TopologyPropertyEntry {
  kind: EntityKind;
  component: string;
  property: TopologyProperty;
}

function topologyProperties(index: ViewerIndex): TopologyPropertyEntry[] {
  const result: TopologyPropertyEntry[] = [];
  for (const node of index.blueprint.graph?.nodes ?? []) {
    for (const property of node.properties ?? []) {
      result.push({ kind: "node", component: node.name, property });
    }
  }
  for (const edge of index.blueprint.graph?.edges ?? []) {
    for (const property of edge.properties ?? []) {
      result.push({ kind: "edge", component: edge.name, property });
    }
  }
  return result;
}

/**
 * Resolve the relation names a field ref belongs to.
 *
 * A field owned by a projection is traced through that projection's row source
 * to the underlying relation, because the matrix columns name sources, not
 * intermediate projections.
 */
function sourceRelationsForField(index: ViewerIndex, ref: Ref): string[] {
  const key = fieldRefKey(ref);
  const location = index.fieldsByKey.get(key);
  const owner =
    location?.ownerName ??
    (typeof ref[2] === "string" ? ref[2].split(".")[0] : "");
  if (!owner) return [];

  const projection = index.projectionByName.get(owner);
  if (projection) {
    const names = relationNamesFromRowSource(projection.row_source);
    if (names.length) return [...new Set(names)].sort();
    return [owner];
  }

  return [owner];
}

function stepSortKey(step: StepId): string {
  return step.join("\u0000");
}

function sortSteps(steps: Iterable<StepId>): StepId[] {
  const byKey = new Map<string, StepId>();
  for (const step of steps) {
    const key = stepSortKey(step);
    if (!byKey.has(key)) byKey.set(key, [step[0], step[1]]);
  }
  return [...byKey.values()].sort((left, right) =>
    stepSortKey(left).localeCompare(stepSortKey(right)),
  );
}

export function buildCoverage(index: ViewerIndex): CoverageMatrix {
  const rows: CoverageMatrix["rows"] = [];
  const allSources = new Set<string>();

  for (const item of topologyProperties(index)) {
    const bindings = findComponentPropertyBindings(
      index,
      item.kind,
      item.component,
      item.property.name,
    );
    const cells = new Map<
      string,
      { fields: Set<string>; literals: number; bindings: Set<number> }
    >();
    const tracedFields = new Set<string>();
    const steps: StepId[] = [];
    let literals = 0;

    for (const entry of bindings) {
      if (entry.binding.step) steps.push(entry.binding.step.id);
      const expression = entry.expression;
      if (!expression) continue;

      const fieldRefs = collectFieldRefs(expression);
      const entrySources = new Set<string>();
      const fieldsBySource = new Map<string, string[]>();
      for (const fieldRef of fieldRefs) {
        const key = fieldRefKey(fieldRef);
        if (key) tracedFields.add(key);
        for (const source of sourceRelationsForField(index, fieldRef)) {
          entrySources.add(source);
          allSources.add(source);
          const list = fieldsBySource.get(source) ?? [];
          if (key) list.push(key);
          fieldsBySource.set(source, list);
        }
      }

      let entryLiterals = 0;
      walkExpression(expression, (node) => {
        if (node.kind === "literal") entryLiterals += 1;
      });
      literals += entryLiterals;

      for (const source of entrySources) {
        const cell = cells.get(source) ?? {
          fields: new Set<string>(),
          literals: 0,
          bindings: new Set<number>(),
        };
        for (const key of fieldsBySource.get(source) ?? []) {
          if (key) cell.fields.add(key);
        }
        cell.literals += entryLiterals;
        cell.bindings.add(entry.binding.index);
        cells.set(source, cell);
      }
    }

    const sourceRelations = [...cells.keys()].sort();
    rows.push({
      component: item.component,
      kind: item.kind,
      property: item.property.name,
      cells: sourceRelations.map((source) => {
        const cell = cells.get(source);
        return {
          source,
          fields: cell?.fields.size ?? 0,
          literals: cell?.literals ?? 0,
          bindings: cell?.bindings.size ?? 0,
        };
      }),
      tracedFields: tracedFields.size,
      literals,
      sourceRelations,
      steps: sortSteps(steps),
    });
  }

  rows.sort((left, right) => {
    const kind = left.kind.localeCompare(right.kind);
    if (kind) return kind;
    const component = left.component.localeCompare(right.component);
    if (component) return component;
    return left.property.localeCompare(right.property);
  });

  return {
    rows,
    sources: [...allSources].sort(),
  };
}
