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
  | "abstractNode"
  | "abstractEdge"
  | "step"
  | "semantics"
  | "field"
  | "binding";

/** One named reference to a concept, with the asset document that owns it. */
/** The document a concept reference opens. */
export interface ConceptTarget {
  concept: ConceptKind;
  name: string;
  /** The virtual collection this target opens, when it is a layer box. */
  collection?: string;
  /** The owner when a property, field or binding is not unique by name. */
  component?: string;
  /** The property name when the concept is a property. */
  property?: string;
  /** The owner's layer, so a field or binding can open the owner's document. */
  ownerConcept?: ConceptKind;
  /** The step identity, when a step name is not unique across components. */
  stepId?: [string, string];
  /** The binding identity, when a binding name is not unique by component. */
  bindingIndex?: number;
}

export interface ConceptReference {
  concept: ConceptKind;
  name: string;
  target?: ConceptTarget;
}
