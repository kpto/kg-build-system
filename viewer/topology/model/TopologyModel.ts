import type {
  ActionModel,
  FieldModel,
  IconToken,
  RowModel,
} from "@/shared/model/hierarchy";
import type { AuditSubject } from "@/lib/reviewTypes";
import type {
  AnnotationContext,
  AnnotationDTO,
  EntityKind,
  MetaGraphIndex,
} from "@/lib/types";
import type { PropertyBadgeModel } from "./propertyBadges";

export interface TopologyNodeModel {
  id: string;
  name: string;
  group: string;
  abstract: boolean;
  degree: number;
}

export interface TopologyLinkModel {
  id: string;
  edgeName: string;
  source: string;
  target: string;
}

export interface TopologyGroupModel {
  id: string;
  name: string;
  count: number;
}

export interface TopologyStats {
  nodes: number;
  links: number;
  nodeTypes: number;
  edgeTypes: number;
}

export interface TopologySelection {
  kind: EntityKind;
  name: string;
}

export interface TopologySelectionCommands {
  selectNode: (name: string) => void;
  selectEdge: (name: string) => void;
  clear: () => void;
}

export interface TopologyPropertyModel {
  id: string;
  name: string;
  typeLabel: string;
  title?: string;
  badges: PropertyBadgeModel[];
}

export interface TopologyNeighbourModel {
  id: string;
  name: string;
  edge: string;
  direction: "in" | "out";
}

export interface TopologySelectionModel {
  kind: EntityKind;
  name: string;
  group: string;
  abstract?: boolean;
  description?: string;
  labels: string[];
  annotations: AnnotationDTO[];
  properties: TopologyPropertyModel[];
  neighbours: TopologyNeighbourModel[];
  reviewCount: number;
  relationship?: { source: string; target: string };
  linkCount: number;
  propertyCount: number;
  annotationCount: number;
}

export interface TopologyNavigatorRow extends RowModel {
  kind: "selection" | "group" | "property" | "neighbour";
  entityKind?: EntityKind;
  edge?: string;
  direction?: "in" | "out";
  abstract?: boolean;
  badges?: PropertyBadgeModel[];
}

export interface TopologyNavigatorSection {
  id: "selection" | "groups" | "properties" | "neighbours";
  title: string;
  question: string;
  count?: string;
  rows: TopologyNavigatorRow[];
  fields?: FieldModel[];
  actions?: ActionModel[];
  annotations?: { annotations: AnnotationDTO[]; context: AnnotationContext };
  description?: string;
  chips?: string[];
  empty?: string;
  notice?: string;
  reviewCount?: number;
}

export interface TopologyNavigatorModel extends Array<TopologyNavigatorSection> {
  id: "navigator";
  title: "Navigator";
  meta: string;
  sections: TopologyNavigatorSection[];
}

export interface TopologyCanvasModel {
  /** Changes only when the graph changes, never when selection changes. */
  graphKey: string;
  nodes: TopologyNodeModel[];
  links: TopologyLinkModel[];
  groups: TopologyGroupModel[];
  selected?: TopologySelection;
  defaultSelection?: TopologySelection;
  busiest?: TopologySelection;
  focusedCount: number;
  reviewCount: number;
  selection: TopologySelectionCommands;
}

export interface TopologyModel {
  id: "topology";
  title: "Orientation";
  icon: IconToken;
  meta: string;
  hint: string;
  stats: TopologyStats;
  canvas: TopologyCanvasModel;
  navigator: TopologyNavigatorModel;
  /** Navigator data for a map-local selection. */
  navigatorFor: (selection: TopologySelection | undefined) => TopologyNavigatorModel;
  metaGraph: MetaGraphIndex;
}

export type TopologyAuditSubject = AuditSubject;
