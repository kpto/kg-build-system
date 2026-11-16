import type { SemanticText, SemanticsDTO, ViewerIndex } from "@/lib/types";

/**
 * Meaning as the viewer reads it: the purpose of the graph or of one design
 * subject, the limitations that bound that purpose, and the contextless claims.
 *
 * This is a read model only. It never infers that meaning propagates from one
 * subject to another.
 */
export interface DesignMeaningFrame {
  text: string;
  limitations?: SemanticText[];
}

export interface DesignMeaningValue {
  purpose?: string;
  limitations: SemanticText[];
  claims: SemanticText[];
  /** A reading from an older snapshot, rendered beside the current units. */
  frames?: DesignMeaningFrame[];
}

export function emptyDesignMeaning(): DesignMeaningValue {
  return { limitations: [], claims: [], frames: [] };
}

/** Read the meaning attached to a node, edge, property, asset or binding. */
export function attachedMeaning(
  semantics: SemanticsDTO | undefined,
): DesignMeaningValue {
  const frames = (semantics?.frames ?? []).map((frame) => ({
    text: frame.text,
    limitations: frame.limitations ?? [],
  }));
  return {
    ...(semantics?.purpose?.text ? { purpose: semantics.purpose.text } : {}),
    limitations: semantics?.purpose?.limitations ?? [],
    claims: semantics?.claims ?? [],
    frames,
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
    (meaning.purpose ? 1 : 0) +
    (meaning.frames?.length ?? 0)
  );
}

export function meaningLimitations(
  meaning: DesignMeaningValue,
): SemanticText[] {
  return meaning.limitations;
}

// ---------------------------------------------------------------------------
// The purpose hierarchy
// ---------------------------------------------------------------------------

export type PurposeLevelKind =
  | "graph"
  | "abstract"
  | "node"
  | "edge"
  | "property"
  | "asset"
  | "relation"
  | "projection"
  | "binding"
  | "step";

/** One level of the record-axis purpose chain and its full meaning. */
export interface PurposeLevel {
  kind: PurposeLevelKind;
  name: string;
  label: string;
  meaning: DesignMeaningValue;
  current?: boolean;
}

export interface PurposeSubjectLike {
  level: string;
  kind?: string;
  component: string;
  property?: string;
}

const PURPOSE_LABELS: Record<PurposeLevelKind, string> = {
  graph: "Graph",
  abstract: "Category",
  node: "Node",
  edge: "Edge",
  property: "Property",
  asset: "Asset",
  relation: "Source relation",
  projection: "Derived relation",
  binding: "Binding",
  step: "Step",
};

interface PurposeEntry {
  name: string;
  parent?: string[];
  abstract?: boolean;
}

function appendPurposeComponent(
  index: ViewerIndex,
  kind: "node" | "edge",
  name: string,
  levels: PurposeLevel[],
  current = true,
): void {
  const entries: ReadonlyMap<string, PurposeEntry> =
    kind === "edge" ? index.topologyEdgesByName : index.topologyNodesByName;
  const ancestors: PurposeEntry[] = [];
  const seen = new Set<string>();
  let entry = entries.get(name);
  while (entry && !seen.has(entry.name)) {
    seen.add(entry.name);
    const parentName = entry.parent?.[2];
    const parent = parentName ? entries.get(parentName) : undefined;
    if (!parent) break;
    ancestors.unshift(parent);
    entry = parent;
  }
  for (const ancestor of ancestors) {
    const abstract = Boolean(ancestor.abstract);
    levels.push({
      kind: kind === "node" && abstract ? "abstract" : kind,
      name: ancestor.name,
      label: PURPOSE_LABELS[
        kind === "node" && abstract ? "abstract" : kind
      ],
      meaning: componentMeaning(index, kind, ancestor.name),
    });
  }
  const entity = entries.get(name);
  const abstract = Boolean(entity?.abstract);
  levels.push({
    kind: kind === "node" && abstract ? "abstract" : kind,
    name,
    label: PURPOSE_LABELS[kind === "node" && abstract ? "abstract" : kind],
    meaning: componentMeaning(index, kind, name),
    current,
  });
}

/** The graph purpose, its categories, the component and the property. */
export function purposeLevels(
  index: ViewerIndex,
  subject: PurposeSubjectLike,
): PurposeLevel[] {
  if (
    subject.level !== "node" &&
    subject.level !== "edge" &&
    subject.level !== "abstract" &&
    subject.level !== "property"
  ) {
    return [];
  }
  const levels: PurposeLevel[] = [];
  const root = graphMeaning(index);
  if (root.purpose) {
    levels.push({
      kind: "graph",
      name: index.graphDeclaration?.name ?? "graph",
      label: PURPOSE_LABELS.graph,
      meaning: root,
    });
  }
  if (subject.level === "property") {
    const kind = subject.kind === "edge" ? "edge" : "node";
    appendPurposeComponent(index, kind, subject.component, levels, false);
    levels.push({
      kind: "property",
      name: subject.property ?? subject.component,
      label: PURPOSE_LABELS.property,
      meaning: propertyMeaning(
        index,
        kind,
        subject.component,
        subject.property ?? "",
      ),
      current: true,
    });
    return levels;
  }
  appendPurposeComponent(
    index,
    subject.level === "edge" ? "edge" : "node",
    subject.component,
    levels,
  );
  return levels;
}

/** One purpose level for a subject that sits outside the record-axis chain. */
export function singlePurposeLevel(
  kind: PurposeLevelKind,
  name: string,
  meaning: DesignMeaningValue,
): PurposeLevel {
  return {
    kind,
    name,
    label: PURPOSE_LABELS[kind],
    meaning,
    current: true,
  };
}
