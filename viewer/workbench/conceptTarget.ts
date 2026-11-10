import type { ConceptTarget } from "@/lib/concepts";
import type { SubjectSelection } from "./types";

/** Turn a concept target into the document selection that opens it. */
export function selectionForConceptTarget(
  target: ConceptTarget,
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
      return { kind: "step", name: target.name };
    default:
      return undefined;
  }
}
