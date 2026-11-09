import type { Grouping } from "@/shared/model/campaign";
import type { ActionModel, IconToken } from "@/shared/model/hierarchy";
import type { EntityKind } from "@/lib/types";

/** The model slice the Outliner is browsing. */
export type NavigatorSlice = "workflow" | "blueprint" | "lineage";

/**
 * One row in the Outliner tree.
 *
 * The row kinds name the semantic subject, not the widget: a `group` is a
 * collection, a `step` is a workflow step, an `entity` is a topology subject
 * and a `property` is a property of that subject. The view chooses the
 * control (summary, button, label) from the kind.
 */
export type NavigatorRowKind =
  | "label"
  | "group"
  | "step"
  | "entity"
  | "property"
  | "asset"
  | "member"
  | "owner"
  | "field"
  | "binding";

export interface NavigatorRow {
  id: string;
  kind: NavigatorRowKind;
  label: string;
  meta?: string;
  title?: string;
  icon?: IconToken;
  /** Plain text detail for a member row. */
  detail?: string;
  /** Right-aligned type text for a field/property row. */
  typeLabel?: string;
  /** The topology entity kind for an entity or property row. */
  entityKind?: EntityKind;
  selected?: boolean;
  /** A campaign-collapsed workflow group. */
  collapsed?: boolean;
  /** The row's meta is its visible child count. */
  metaFromChildren?: boolean;
  /** This row contributes to the nearest section or label tally. */
  countsAs?: NavigatorRowKind;
  /** Count visible descendants of these kinds on this row. */
  tally?: NavigatorRowKind[];
  count?: number;
  total?: number;
  /** Lower-case search haystack. */
  search?: string;
  actions?: ActionModel[];
  children?: NavigatorRow[];
  /** A group opens when one of its descendants is selected. */
  openOnSelection?: boolean;
  /** A label stays present while filtering so its count remains readable. */
  fixed?: boolean;
  /** Message shown when a labelled collection has no visible children. */
  empty?: string;
}

export interface NavigatorSection {
  id: string;
  title: string;
  question: string;
  icon: IconToken;
  rows: NavigatorRow[];
  count: number;
  total: number;
  tally: NavigatorRowKind[];
  empty?: string;
}

export interface NavigatorModel {
  id: "outliner";
  title: "Outliner";
  icon: IconToken;
  meta: string;
  slice: NavigatorSlice;
  grouping: Grouping;
  groupingLabel: string;
  filterPlaceholder: string;
  filterLabel: string;
  filterTitle: string;
  clearFilterLabel: string;
  collapseAllLabel: string;
  expandAllLabel: string;
  sections: NavigatorSection[];
  activeCount: number;
  activeTotal: number;
  sourceCount: number;
  sourceTotal: number;
  showSourceModel: boolean;
  /** True when the active filter leaves nothing to inspect. */
  empty: boolean;
  noMatches?: { title: string; hint: string };
}
