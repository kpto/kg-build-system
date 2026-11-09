import type { InspectorSelection } from "@/shared/types/selection";
import type { AuditSubject } from "@/lib/reviewTypes";
import type { LineageGraph, ViewerIndex } from "@/lib/types";

/**
 * The diagnosis domains read the selected subject from the campaign selection.
 * The campaign owns the selection; a domain model never keeps a second copy of
 * it.
 */
export function subjectFromSelection(
  selection: InspectorSelection | null,
  index?: ViewerIndex,
): AuditSubject | undefined {
  if (!selection) return undefined;
  switch (selection.kind) {
    case "property":
      return {
        kind: "property",
        name: selection.selection.component,
        component: selection.selection.component,
        property: selection.selection.property,
        entityKind: selection.selection.kind,
      };
    case "topology":
      return {
        kind: selection.entityKind,
        name: selection.name,
        component: selection.name,
      };
    case "step":
      return {
        kind: "step",
        name: `${selection.step.id[0]}/${selection.step.id[1]}`,
        component: selection.step.id[0],
        stepId: selection.step.id,
      };
    case "binding":
      return {
        kind: "binding",
        name: selection.binding.component,
        component: selection.binding.component,
        bindingIndex: selection.binding.index,
      };
    case "asset":
      return {
        kind: "asset",
        name: selection.name,
        component: selection.name,
      };
    case "data":
      return {
        kind: selection.entityType === "projection" ? "projection" : "relation",
        name: selection.name,
        component: selection.name,
      };
    case "field": {
      const location = index?.fieldsByKey.get(selection.fieldKey);
      if (!location) return undefined;
      return {
        kind: location.ownerKind === "projection" ? "projection" : "relation",
        name: location.ownerName,
        component: location.ownerName,
      };
    }
    case "lineage-node": {
      const node = selection.node;
      if (node.stepId) {
        return {
          kind: "step",
          name: `${node.stepId[0]}/${node.stepId[1]}`,
          component: node.stepId[0],
          stepId: node.stepId,
        };
      }
      if (node.component && node.property) {
        return {
          kind: "property",
          name: node.component,
          component: node.component,
          property: node.property,
        };
      }
      return undefined;
    }
  }
}

/** The lineage graph a selection carries, if it carries one. */
export function lineageFromSelection(
  selection: InspectorSelection | null,
): LineageGraph | null {
  if (!selection) return null;
  if (selection.kind === "property" || selection.kind === "lineage-node") {
    return selection.lineage;
  }
  return null;
}

/** The focused node id of a lineage selection. */
export function lineageNodeIdFromSelection(
  selection: InspectorSelection | null,
): string | undefined {
  return selection?.kind === "lineage-node" ? selection.node.id : undefined;
}
