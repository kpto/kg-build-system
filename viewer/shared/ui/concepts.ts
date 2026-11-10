import {
  BadgeCheck,
  Boxes,
  CircleDot,
  Columns3,
  Database,
  GitBranch,
  Hash,
  Layers,
  Network,
  Table2,
  Waypoints,
  Workflow,
  type LucideIcon,
} from "lucide-react";

import type { ConceptKind } from "@/lib/concepts";
import { theme } from "./theme";

export interface ConceptDefinition {
  label: string;
  icon: LucideIcon;
  color: string;
}

/** The canonical logo and representative colour for each design concept. */
export const concepts: Record<ConceptKind, ConceptDefinition> = {
  graph: { label: "Graph", icon: Waypoints, color: theme.group9 },
  workflow: { label: "Workflow", icon: Workflow, color: theme.selection },
  node: { label: "Node", icon: Network, color: theme.target },
  edge: { label: "Edge", icon: GitBranch, color: theme.binding },
  property: { label: "Property", icon: CircleDot, color: theme.transform },
  asset: { label: "Asset", icon: Database, color: theme.asset },
  table: { label: "Table", icon: Table2, color: theme.source },
  projection: { label: "Projection", icon: Columns3, color: theme.post },
  abstract: { label: "Abstract category", icon: Layers, color: theme.group8 },
  step: { label: "Step", icon: Boxes, color: theme.group10 },
  semantics: { label: "Semantics", icon: BadgeCheck, color: theme.accent },
  field: { label: "Field", icon: Hash, color: theme.group7 },
};

/**
 * Map a workbench selection kind to its canonical concept. A document kind
 * and a subject kind use the same vocabulary; only the label differs.
 */
export function conceptForSelection(
  kind?: string,
  level?: string,
): ConceptKind {
  if (level === "abstract") return "abstract";
  switch (kind) {
    case "graph":
    case "workflow":
    case "node":
    case "edge":
    case "property":
    case "asset":
    case "step":
      return kind;
    case "relation":
      return "table";
    case "projection":
      return "projection";
    case "field":
      return "property";
    default:
      return "node";
  }
}
