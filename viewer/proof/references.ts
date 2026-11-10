import type { ConceptReference } from "@/lib/concepts";
import { resolveAssetName } from "@/lib/indexes";
import type { ViewerIndex } from "@/lib/types";
import type { ProofModel } from "./model";
import { resolveExpressionSources } from "./sources";

export interface ProvenanceReferences {
  assets: ConceptReference[];
  tables: ConceptReference[];
  projections: ConceptReference[];
}

function sortedNames(values: Iterable<string>): string[] {
  return [...new Set(values)].sort((left, right) => left.localeCompare(right));
}

function assetReferences(names: Iterable<string>): ConceptReference[] {
  return sortedNames(names).map((name) => ({
    concept: "asset",
    name,
    target: { concept: "asset", name },
  }));
}

function ownedReferences(
  index: ViewerIndex,
  concept: "table" | "projection",
  names: Iterable<string>,
): ConceptReference[] {
  return sortedNames(names).map((name) => {
    const assetName = resolveAssetName(index, name);
    return {
      concept,
      name,
      target: assetName
        ? { concept: "asset" as const, name: assetName }
        : undefined,
    };
  });
}

/**
 * The resolved provenance behind a node, edge or property: the assets, tables
 * and projections its bindings read. Every reference names the asset document
 * that exposes it, so a caller can open it without re-resolving the model.
 */
export function provenanceReferences(
  index: ViewerIndex,
  model: ProofModel,
): ProvenanceReferences {
  const assets: string[] = [];
  const tables: string[] = [];
  const projections: string[] = [];

  if (model.level === "property") {
    for (const branch of model.branches) {
      assets.push(...branch.branch.assetNames);
      tables.push(...branch.branch.sourceRelations);
      for (const node of branch.nodes) {
        if (node.kind === "projection" && node.component) {
          projections.push(node.component);
        }
      }
    }
  } else if (model.level === "node" || model.level === "edge") {
    for (const property of model.component?.properties ?? []) {
      assets.push(...property.assets);
      tables.push(...property.sources);
      projections.push(...property.projections);
    }
    const kind = model.subject.kind;
    if (kind === "node" || kind === "edge") {
      for (const binding of index.bindings) {
        if (binding.kind !== kind || binding.component !== model.subject.component) {
          continue;
        }
        const resolved = resolveExpressionSources(index, [
          binding.binding.identity,
          binding.binding.source_identity,
          binding.binding.target_identity,
          ...Object.values(binding.binding.properties ?? {}),
        ]);
        assets.push(...resolved.assets);
        tables.push(...resolved.sources);
        projections.push(...resolved.projections);
      }
    }
  }

  return {
    assets: assetReferences(assets),
    tables: ownedReferences(index, "table", tables),
    projections: ownedReferences(index, "projection", projections),
  };
}
