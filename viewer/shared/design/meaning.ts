import type {
  SemanticText,
  SemanticsDTO,
  SemanticsFrameDTO,
  ViewerIndex,
} from "@/lib/types";

/**
 * Meaning as the viewer reads it: the purpose of the graph or the claims,
 * frames and limitations attached to one design subject.
 *
 * This is a read model only. It never infers that meaning propagates from one
 * subject to another.
 */
export interface DesignMeaningValue {
  purpose?: string;
  claims: SemanticText[];
  frames: SemanticsFrameDTO[];
}

export function emptyDesignMeaning(): DesignMeaningValue {
  return { claims: [], frames: [] };
}

/** Read the meaning attached to a node, edge, property, asset or binding. */
export function attachedMeaning(
  semantics: SemanticsDTO | undefined,
): DesignMeaningValue {
  return {
    claims: semantics?.claims ?? [],
    frames: semantics?.frames ?? [],
  };
}

/** Read the graph declaration's purpose, claims and frames. */
export function graphMeaning(index: ViewerIndex): DesignMeaningValue {
  const semantics = index.graphSemantics;
  return {
    ...(semantics?.purpose?.text ? { purpose: semantics.purpose.text } : {}),
    claims: semantics?.claims ?? [],
    frames: semantics?.purpose?.frames ?? [],
  };
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
    meaning.frames.length +
    meaning.frames.reduce(
      (total, frame) => total + (frame.limitations?.length ?? 0),
      0,
    )
  );
}

export function meaningLimitations(
  meaning: DesignMeaningValue,
): SemanticText[] {
  return meaning.frames.flatMap((frame) => frame.limitations ?? []);
}
