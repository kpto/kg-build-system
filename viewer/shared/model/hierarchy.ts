/**
 * Framework-agnostic hierarchy models.
 *
 * These types know nothing about React, JSX, the DOM or a particular view.
 * A view binds to them; a ViewModel exposes them. Icons are tokens, not
 * components.
 */

export type IconToken =
  | "map"
  | "explore"
  | "review"
  | "workflow"
  | "blueprint"
  | "lineage"
  | "outliner"
  | "navigator"
  | "properties"
  | "audit"
  | "fit"
  | "read"
  | "copy"
  | "search"
  | "import"
  | "zoom"
  | "focus"
  | "reset"
  | "collapse"
  | "expand"
  | "trace"
  | "branch"
  | "layers"
  | "braces"
  | "asset"
  | "binding"
  | "field"
  | "code"
  | "info"
  | "question"
  | "warning"
  | "check"
  | "open";

export type Tone =
  | "neutral"
  | "accent"
  | "selection"
  | "critical"
  | "high"
  | "medium"
  | "low"
  | "info";

/** One action a view can call. The command itself is framework-agnostic. */
export interface ActionModel {
  id: string;
  label: string;
  icon?: IconToken;
  disabled?: boolean;
  /** Accessible description / tooltip. */
  title?: string;
  run: () => void;
}

/** One value: evidence for the row or section that owns it. */
export interface FieldModel {
  id: string;
  label: string;
  value: string;
  title?: string;
  tone?: Tone;
  copy?: boolean;
}

/** One subject. */
export interface RowModel {
  id: string;
  label: string;
  meta?: string;
  title?: string;
  tone?: Tone;
  selected?: boolean;
  active?: boolean;
  dimmed?: boolean;
  fields?: FieldModel[];
  actions?: ActionModel[];
}

/** One question inside a panel. */
export interface SectionModel {
  id: string;
  title: string;
  question: string;
  count?: string;
  rows?: RowModel[];
  fields?: FieldModel[];
  actions?: ActionModel[];
}

/** A rail is an index or switch over sections, depending on the panel. */
export interface RailModel {
  id: string;
  label: string;
  question: string;
  icon: IconToken;
  sections: SectionModel[];
}

/** A panel's question, header data and body model. */
export interface PanelModel {
  id: string;
  title: string;
  meta?: string;
  question: string;
  icon: IconToken;
  actions?: ActionModel[];
  sections?: SectionModel[];
  rails?: RailModel[];
}
