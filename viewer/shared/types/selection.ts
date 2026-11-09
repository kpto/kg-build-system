import type {
  EntityKind,
  IndexedBinding,
  LineageGraph,
  LineageNode,
  PropertySelection,
  WorkflowStep,
} from "@/lib/types";

/**
 * The selected subject shared by navigation, diagnosis and evidence.
 *
 * This type is a cross-panel contract, so it lives in `shared/types`, not in
 * the evidence panel. Navigation and diagnosis must not import evidence just to
 * name the selection.
 */
export type InspectorSelection =
  | { kind: "step"; step: WorkflowStep }
  | { kind: "binding"; binding: IndexedBinding }
  | { kind: "property"; selection: PropertySelection; lineage: LineageGraph }
  | { kind: "topology"; entityKind: EntityKind; name: string }
  | { kind: "data"; entityType: "relation" | "projection" | "struct"; name: string }
  | { kind: "asset"; name: string }
  | { kind: "field"; fieldKey: string }
  | { kind: "lineage-node"; node: LineageNode; lineage: LineageGraph };
