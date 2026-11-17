import type { CSSProperties, ReactNode } from "react";

import type { ConceptKind } from "@/lib/concepts";
import { cx, theme } from "./theme";
import styles from "./conceptMark.module.css";

export interface ConceptDefinition {
  label: string;
  color: string;
  mark: ReactNode;
}

/**
 * The canonical mark and representative colour for each design concept.
 *
 * Every surface that shows a concept reads this catalogue: a banner, a tab, a
 * reference chip, the expression outline and a membership row. One grammar
 * draws every mark — a 24 px grid, a 1.6 px stroke, round joins and one
 * optional element that fills at 24% when the concept is active. Colour is a
 * second cue; the silhouette and the label carry the distinction alone.
 */
export const concepts: Record<ConceptKind, ConceptDefinition> = {
  graph: {
    label: "Graph",
    color: theme.conceptGraph,
    mark: (
      <>
        <g className={styles.fill}>
          <circle cx="12" cy="5" r="2.1" />
          <circle cx="5" cy="18" r="2.1" />
          <circle cx="19" cy="18" r="2.1" />
        </g>
        <path d="M10.4 6.8 6.1 16.2M13.6 6.8l4.3 9.4M7.1 18h9.8" />
      </>
    ),
  },
  abstract: {
    label: "Abstract category",
    color: theme.conceptAbstract,
    mark: (
      <>
        <rect x="4" y="4" width="16" height="16" rx="3" />
        <rect
          className={styles.fill}
          x="8.5"
          y="8.5"
          width="7"
          height="7"
          rx="1.5"
        />
      </>
    ),
  },
  node: {
    label: "Node",
    color: theme.conceptNode,
    mark: (
      <>
        <circle cx="12" cy="12" r="7" />
        <circle className={styles.fill} cx="12" cy="12" r="2.4" />
      </>
    ),
  },
  edge: {
    label: "Edge",
    color: theme.conceptEdge,
    mark: (
      <>
        <circle className={styles.fill} cx="5" cy="17" r="2.1" />
        <circle className={styles.fill} cx="19" cy="7" r="2.1" />
        <path d="M6.7 15.7C9.5 10.5 14 7.3 17.4 7.1" />
      </>
    ),
  },
  property: {
    label: "Property",
    color: theme.conceptProperty,
    mark: (
      <>
        <circle className={styles.fill} cx="12" cy="8" r="3" />
        <path d="M12 11v8M9.5 16.5h5" />
      </>
    ),
  },
  asset: {
    label: "Asset",
    color: theme.conceptAsset,
    mark: (
      <>
        <ellipse
          className={styles.fill}
          cx="12"
          cy="6.5"
          rx="6.5"
          ry="2.5"
        />
        <path d="M5.5 6.5v11c0 1.4 2.9 2.5 6.5 2.5s6.5-1.1 6.5-2.5v-11" />
        <path d="M5.5 11.5h13" />
      </>
    ),
  },
  table: {
    label: "Source relation",
    color: theme.conceptSource,
    mark: (
      <>
        <rect x="4.5" y="5.5" width="15" height="10" rx="1.5" />
        <path d="M9.5 5.5v10M14.5 5.5v10M4.5 10.5h15" />
        <path d="M12 22v-6M9.5 18.5 12 16l2.5 2.5" />
        <path className={styles.plain} d="M4.5 5.5h15v5h-15z" />
      </>
    ),
  },
  projection: {
    label: "Derived relation",
    color: theme.conceptDerived,
    mark: (
      <>
        <rect x="7" y="3" width="10" height="7" rx="1.5" />
        <path d="M7 6.5h10M12 3v7" />
        <rect x="2" y="16" width="7" height="5" rx="1.2" />
        <path d="M2 18.5h7" />
        <rect x="15" y="16" width="7" height="5" rx="1.2" />
        <path d="M15 18.5h7" />
        <path d="M5.5 16C5.5 12 8 10.5 10 10M18.5 16C18.5 12 16 10.5 14 10" />
        <path className={styles.plain} d="M7 3h10v3.5H7z" />
      </>
    ),
  },
  field: {
    label: "Field",
    color: theme.conceptField,
    mark: (
      <>
        <path d="M9 4 7 20M17 4l-2 16M4.5 9h15M4 15h15" />
        <circle className={styles.fill} cx="19" cy="19" r="1.6" />
      </>
    ),
  },
  binding: {
    label: "Binding",
    color: theme.conceptBinding,
    mark: (
      <>
        <circle className={styles.fill} cx="12" cy="12" r="4" />
        <path d="M2 12h6M16 12h6" />
      </>
    ),
  },
  workflow: {
    label: "Workflow",
    color: theme.conceptWorkflow,
    mark: (
      <>
        <rect x="3" y="3" width="7" height="6" rx="1.5" />
        <rect x="14" y="3" width="7" height="6" rx="1.5" />
        <rect
          className={styles.fill}
          x="8.5"
          y="15"
          width="7"
          height="6"
          rx="1.5"
        />
        <path d="M6.5 9v3.5L12 15M17.5 9v3.5L12 15" />
      </>
    ),
  },
  step: {
    label: "Step",
    color: theme.conceptStep,
    mark: (
      <>
        <rect x="3.5" y="4.5" width="17" height="15" rx="2" />
        <path d="M7.5 9.5 11 12l-3.5 2.5M12.5 15h4" />
        <circle className={styles.fill} cx="17.5" cy="7.5" r="1.2" />
      </>
    ),
  },
  semantics: {
    label: "Meaning",
    color: theme.conceptMeaning,
    mark: (
      <>
        <circle className={styles.fill} cx="12" cy="10" r="6" />
        <path d="M9.5 15.5 8 22l4-2 4 2-1.5-6.5" />
        <path d="M9.3 10l1.8 1.8 3.6-3.6" />
      </>
    ),
  },
};

/**
 * Draw one concept's mark from the catalogue. `active` fills the mark's one
 * filled element at 24%, so a current or selected concept reads at a glance
 * without changing its silhouette.
 */
export function LayerMark({
  concept,
  className,
  active = false,
  style,
}: {
  concept: ConceptKind;
  className?: string;
  active?: boolean;
  style?: CSSProperties;
}) {
  return (
    <svg
      aria-hidden
      className={cx(styles.mark, className)}
      style={style}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      focusable="false"
      data-concept={concept}
      data-active={active || undefined}
    >
      {concepts[concept].mark}
    </svg>
  );
}

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
