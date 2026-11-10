/**
 * Canonical design concepts and references.
 *
 * The kind of a subject, a document, a tab, a provenance node and a reference
 * is one vocabulary. A visual layer adds an icon and colour to a concept; the
 * model layer resolves a reference to the document that can open it.
 */

export type ConceptKind =
  | "graph"
  | "workflow"
  | "node"
  | "edge"
  | "property"
  | "asset"
  | "table"
  | "projection"
  | "abstract"
  | "step"
  | "semantics"
  | "field";

/** One named reference to a concept, with the asset document that owns it. */
/** The document a concept reference opens. */
export interface ConceptTarget {
  concept: ConceptKind;
  name: string;
}

export interface ConceptReference {
  concept: ConceptKind;
  name: string;
  target?: ConceptTarget;
}
