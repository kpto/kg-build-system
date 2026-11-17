import type { ConceptTarget } from "@/lib/concepts";
import type { ViewerIndex } from "@/lib/types";
import type { SubjectSelection } from "./types";

/** Where a concept pill navigates: a working surface or a subject document. */
export type ConceptDestination =
  | { kind: "graph" }
  | { kind: "workflow" }
  | { kind: "subject"; selection: SubjectSelection };

function ownerKind(
  target: ConceptTarget,
  index?: ViewerIndex,
): "node" | "edge" | undefined {
  if (target.ownerConcept === "node" || target.ownerConcept === "edge") {
    return target.ownerConcept;
  }
  if (!target.component || !index) return undefined;
  if (index.topologyNodesByName.has(target.component)) return "node";
  if (index.topologyEdgesByName.has(target.component)) return "edge";
  return undefined;
}

function findPropertyOwner(
  index: ViewerIndex,
  name: string,
): { component: string; kind: "node" | "edge" } | undefined {
  const owners = new Map<string, { component: string; kind: "node" | "edge" }>();
  for (const entries of index.propertyIndex.values()) {
    for (const entry of entries) {
      if (entry.property !== name) continue;
      if (entry.kind !== "node" && entry.kind !== "edge") continue;
      owners.set(`${entry.kind}:${entry.component}`, {
        component: entry.component,
        kind: entry.kind,
      });
    }
  }
  return owners.size === 1 ? [...owners.values()][0] : undefined;
}

function findFieldOwner(
  index: ViewerIndex,
  name: string,
): { component: string; ownerConcept: "table" | "projection" } | undefined {
  const owners = new Map<
    string,
    { component: string; ownerConcept: "table" | "projection" }
  >();
  for (const field of index.fieldsByKey.values()) {
    if (field.field.name !== name) continue;
    if (field.ownerKind === "relation") {
      owners.set(`table:${field.ownerName}`, {
        component: field.ownerName,
        ownerConcept: "table",
      });
    } else if (field.ownerKind === "projection") {
      owners.set(`projection:${field.ownerName}`, {
        component: field.ownerName,
        ownerConcept: "projection",
      });
    }
  }
  return owners.size === 1 ? [...owners.values()][0] : undefined;
}

function propertyParts(
  target: ConceptTarget,
): { component: string; property: string } | undefined {
  if (target.component && target.property) {
    return { component: target.component, property: target.property };
  }
  const cut = target.name.lastIndexOf(".");
  if (cut <= 0 || cut === target.name.length - 1) return undefined;
  return {
    component: target.component ?? target.name.slice(0, cut),
    property: target.property ?? target.name.slice(cut + 1),
  };
}

/** Turn a concept target into the document selection that opens it. */
export function selectionForConceptTarget(
  target: ConceptTarget,
  index?: ViewerIndex,
): SubjectSelection | undefined {
  switch (target.concept) {
    case "asset":
      return {
        kind: "asset",
        level: "asset",
        component: target.name,
      };
    case "node":
      return { kind: "node", level: "node", component: target.name };
    case "edge":
      return { kind: "edge", level: "edge", component: target.name };
    case "abstract":
      return { kind: "node", level: "abstract", component: target.name };
    case "table":
      return { kind: "relation", name: target.name, component: target.name };
    case "projection":
      return { kind: "projection", name: target.name, component: target.name };
    case "step":
      return {
        kind: "step",
        name: target.name,
        ...(target.component ? { component: target.component } : {}),
        ...(target.stepId ? { stepId: target.stepId } : {}),
      };
    case "property": {
      const parts = propertyParts(target);
      const kind = ownerKind(target, index);
      if (parts && kind) {
        return {
          kind,
          level: "property",
          name: target.name,
          component: parts.component,
          property: parts.property,
        };
      }
      const owner = index ? findPropertyOwner(index, target.name) : undefined;
      if (!owner) return undefined;
      return {
        kind: owner.kind,
        level: "property",
        name: target.name,
        component: owner.component,
        property: target.name,
      };
    }
    case "field": {
      if (target.component && target.ownerConcept) {
        return selectionForConceptTarget(
          { concept: target.ownerConcept, name: target.component },
          index,
        );
      }
      const owner = index ? findFieldOwner(index, target.name) : undefined;
      if (!owner) return undefined;
      return selectionForConceptTarget(
        { concept: owner.ownerConcept, name: owner.component },
        index,
      );
    }
    case "binding": {
      if (target.bindingIndex !== undefined) {
        return {
          kind: "binding",
          name: target.name,
          ...(target.component ? { component: target.component } : {}),
          bindingIndex: target.bindingIndex,
        };
      }
      if (!target.component || !target.ownerConcept) return undefined;
      return selectionForConceptTarget(
        {
          concept: target.ownerConcept,
          name: target.component,
        },
        index,
      );
    }
    case "graph":
    case "workflow":
    case "semantics":
      return undefined;
  }
}

/**
 * Resolve a pill's target to the destination the workbench should show. The
 * pill owns this decision; a caller never passes a navigation callback.
 */
export function destinationForConceptTarget(
  index: ViewerIndex,
  target: ConceptTarget,
): ConceptDestination | undefined {
  if (target.concept === "graph") return { kind: "graph" };
  if (target.concept === "workflow") return { kind: "workflow" };
  const selection = selectionForConceptTarget(target, index);
  return selection ? { kind: "subject", selection } : undefined;
}
