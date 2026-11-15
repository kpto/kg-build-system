import type { SemanticText, SemanticsDTO, ViewerIndex } from "@/lib/types";

/**
 * Meaning as the viewer reads it: the purpose of the graph or of one design
 * subject, the limitations that bound that purpose, and the contextless claims.
 *
 * This is a read model only. It never infers that meaning propagates from one
 * subject to another.
 */
export interface DesignMeaningValue {
  purpose?: string;
  limitations: SemanticText[];
  claims: SemanticText[];
}

export function emptyDesignMeaning(): DesignMeaningValue {
  return { limitations: [], claims: [] };
}

/** Read the meaning attached to a node, edge, property, asset or binding. */
export function attachedMeaning(
  semantics: SemanticsDTO | undefined,
): DesignMeaningValue {
  return {
    ...(semantics?.purpose?.text ? { purpose: semantics.purpose.text } : {}),
    limitations: semantics?.purpose?.limitations ?? [],
    claims: semantics?.claims ?? [],
  };
}

/** Read the graph declaration's root purpose, limitations and claims. */
export function graphMeaning(index: ViewerIndex): DesignMeaningValue {
  return attachedMeaning(index.graphSemantics);
}

/** The attached meaning of a topology node or edge. */
export function componentMeaning(
  index: ViewerIndex,
  kind: "node" | "edge",
  name: string,
): DesignMeaningValue {
  const component =
    kind === "node"
      ? index.topologyNodesByName.get(name)
      : index.topologyEdgesByName.get(name);
  return attachedMeaning(component?.semantics);
}

/** The attached meaning of one property on a topology node or edge. */
export function propertyMeaning(
  index: ViewerIndex,
  kind: "node" | "edge",
  component: string,
  property: string,
): DesignMeaningValue {
  const entity =
    kind === "node"
      ? index.topologyNodesByName.get(component)
      : index.topologyEdgesByName.get(component);
  const declaration = entity?.properties?.find(
    (candidate) => candidate.name === property,
  );
  return attachedMeaning(declaration?.semantics);
}

export function meaningCount(meaning: DesignMeaningValue): number {
  return (
    meaning.claims.length +
    meaning.limitations.length +
    (meaning.purpose ? 1 : 0)
  );
}

export function meaningLimitations(
  meaning: DesignMeaningValue,
): SemanticText[] {
  return meaning.limitations;
}
