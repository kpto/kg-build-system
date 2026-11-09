import type {
  ActionModel,
  FieldModel,
  IconToken,
  RowModel,
} from "@/shared/model/hierarchy";
import type { InspectorSelection } from "@/shared/types/selection";
import type {
  AnnotationContext,
  AnnotationDTO,
  MetaGraphIndex,
} from "@/lib/types";

export type PropertiesRailId =
  | "definition"
  | "production"
  | "emission"
  | "dependencies"
  | "context";

export interface PropertiesRail {
  id: PropertiesRailId;
  label: string;
  question: string;
  icon: IconToken;
}

export interface PropertiesAnnotation {
  annotations: AnnotationDTO[];
  context: AnnotationContext;
}

export interface PropertiesField extends FieldModel {
  /** The view may offer a copy control for this value. */
  copy?: boolean;
  /** Identifiers and paths render in mono; prose renders in sans. */
  mono?: boolean;
}

export type PropertiesBlock =
  | { kind: "field"; field: PropertiesField }
  | { kind: "row"; row: PropertiesRow }
  | { kind: "pills"; values: string[]; empty?: string }
  | { kind: "code"; label: string; text: string }
  | { kind: "text"; text: string; mono?: boolean; breakAll?: boolean }
  | { kind: "empty"; text: string };

export interface PropertiesRow extends RowModel {
  kind?: "property" | "field" | "connection" | "branch" | "target" | "data-field";
  blocks?: PropertiesBlock[];
  direction?: "in" | "out";
  annotations?: PropertiesAnnotation;
}

export interface PropertiesSection {
  id: string;
  title: string;
  question: string;
  count?: string;
  blocks: PropertiesBlock[];
  annotations?: PropertiesAnnotation;
}

export interface PropertiesEmptyState {
  title: string;
  hint: string;
  actionLabel: string;
}

/**
 * The Properties panel model.
 *
 * A rail is a question, not a bucket of section titles; `sectionsFor` holds the
 * already-filtered sections for each rail. The active rail is view state, so it
 * is deliberately absent here.
 */
export interface PropertiesModel {
  id: "properties";
  title: "Properties";
  icon: IconToken;
  empty: boolean;
  kind?: InspectorSelection["kind"];
  kindLabel?: string;
  subjectTitle?: string;
  emptyState?: PropertiesEmptyState;
  rails: PropertiesRail[];
  sectionsFor: Record<PropertiesRailId, PropertiesSection[]>;
  metaGraph: MetaGraphIndex;
}

export type PropertiesAction = ActionModel;
