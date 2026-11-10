import { collectFieldRefs, fieldRefKey } from "@/lib/expressions";
import { relationNamesFromRowSource, resolveAssetName } from "@/lib/indexes";
import type { Expression, Ref, ViewerIndex } from "@/lib/types";

/** The data sources read by one or more expressions. */
export interface ResolvedSources {
  sources: string[];
  assets: string[];
  projections: string[];
}

/**
 * Resolve field references to the tables, projections and assets that own
 * them. A field may belong to a projection; the projection's row source then
 * names the base tables.
 */
export function resolveFieldSources(
  index: ViewerIndex,
  fieldRefs: Ref[],
): ResolvedSources {
  const owners = fieldRefs
    .map((fieldRef) => index.fieldsByKey.get(fieldRefKey(fieldRef))?.ownerName)
    .filter((name): name is string => Boolean(name));
  const projections = [
    ...new Set(owners.filter((name) => index.projectionByName.has(name))),
  ];
  const sources = [
    ...new Set(
      owners.flatMap((name) => {
        const projection = index.projectionByName.get(name);
        const relations = projection
          ? [
              projection.row_source?.relation?.[2],
              ...relationNamesFromRowSource(projection.row_source),
            ].filter((candidate): candidate is string => Boolean(candidate))
          : [name];
        return relations;
      }),
    ),
  ];
  const assets = [
    ...new Set(
      [...owners, ...sources]
        .map((name) => resolveAssetName(index, name))
        .filter((name): name is string => Boolean(name)),
    ),
  ];
  return { sources, assets, projections };
}

/** Resolve every field read by a set of expressions. */
export function resolveExpressionSources(
  index: ViewerIndex,
  expressions: Array<Expression | undefined>,
): ResolvedSources {
  return resolveFieldSources(
    index,
    expressions.flatMap((expression) => collectFieldRefs(expression)),
  );
}
