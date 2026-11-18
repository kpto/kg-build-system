import type { ConceptKind } from "@/lib/concepts";

/**
 * The virtual collections the Explorer exposes.
 *
 * A collection is not a declared subject: it is one layer of the design read as
 * a group. Its document carries the layer DAG below it, the one layer above it,
 * its items and its coverage. A participant document carries the participant's
 * own meaning and dependency.
 */
export type CollectionId =
  | "assets"
  | "sourceRelations"
  | "derivedRelations"
  | "bindings"
  | "nodes"
  | "abstract"
  | "edges"
  | "workflow";

export interface CollectionDefinition {
  /** Plural title used by the Explorer header and the document banner. */
  title: string;
  concept: ConceptKind;
  kicker: string;
}

export const COLLECTIONS: Record<CollectionId, CollectionDefinition> = {
  assets: { title: "Assets", concept: "asset", kicker: "Collection" },
  sourceRelations: {
    title: "Source relations",
    concept: "table",
    kicker: "Collection",
  },
  derivedRelations: {
    title: "Derived relations",
    concept: "projection",
    kicker: "Collection",
  },
  bindings: { title: "Bindings", concept: "binding", kicker: "Collection" },
  nodes: { title: "Nodes", concept: "node", kicker: "Collection" },
  abstract: {
    title: "Abstract",
    concept: "abstract",
    kicker: "Collection",
  },
  edges: { title: "Edges", concept: "edge", kicker: "Collection" },
  workflow: {
    title: "Workflow",
    concept: "workflow",
    kicker: "Collection",
  },
};

export function collectionTitle(
  collection: CollectionId,
  component?: string,
): string {
  if (collection === "workflow" && component) return component;
  return COLLECTIONS[collection].title;
}

export function collectionConcept(collection: CollectionId): ConceptKind {
  return COLLECTIONS[collection].concept;
}
