import { resolveAssetName } from "@/lib/indexes";
import type { ConceptReference } from "@/lib/concepts";
import type { ViewerIndex } from "@/lib/types";
import type { ProofModel } from "./model";

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
    assetName: name,
  }));
}

function ownedReferences(
  index: ViewerIndex,
  concept: "table" | "projection",
  names: Iterable<string>,
): ConceptReference[] {
  return sortedNames(names).map((name) => ({
    concept,
    name,
    assetName: resolveAssetName(index, name),
  }));
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
  }

  return {
    assets: assetReferences(assets),
    tables: ownedReferences(index, "table", tables),
    projections: ownedReferences(index, "projection", projections),
  };
}
