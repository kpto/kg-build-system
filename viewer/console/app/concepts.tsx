import type { CSSProperties, ReactNode } from "react";

import { cx, theme } from "@kbs/design";

import styles from "./concepts.module.css";

export type ConsoleConcept =
  | "revision"
  | "evaluation_design"
  | "evaluation_run"
  | "result"
  | "finding"
  | "proposal"
  | "change_design";

export interface ConceptDefinition {
  label: string;
  color: string;
  mark: ReactNode;
}

/**
 * The console's concept catalogue. The grammar matches the design viewer:
 * a 20 px tight grid, one stroke, a mark, a divider and the instance name.
 * Colour is the second cue; the mark and label carry the meaning alone.
 */
export const CONCEPTS: Record<ConsoleConcept, ConceptDefinition> = {
  revision: {
    label: "Revision",
    color: theme.selection,
    mark: (
      <>
        <circle cx="12" cy="6" r="2.4" />
        <path d="M12 8.4v11" />
        <circle cx="12" cy="19.4" r="1.6" fill="currentColor" stroke="none" />
      </>
    ),
  },
  finding: {
    label: "Finding",
    color: theme.conceptProperty,
    mark: (
      <>
        <circle cx="10.5" cy="10.5" r="5.7" />
        <path d="m14.7 14.7 4.8 4.8" />
      </>
    ),
  },
  proposal: {
    label: "Proposal",
    color: theme.conceptBinding,
    mark: (
      <>
        <path d="M6 3.5h7.5L18 8v12.5H6z" />
        <path d="M13.5 3.5V8H18" />
        <path d="M9 12h6M9 15.5h6" />
      </>
    ),
  },
  change_design: {
    label: "Design",
    color: theme.conceptGraph,
    mark: (
      <>
        <path d="m5 19 3.5-1 10-10-2.5-2.5-10 10z" />
        <path d="m14.5 5.5 2.5 2.5" />
        <path d="M5 19h6" />
      </>
    ),
  },
  evaluation_design: {
    label: "Eval design",
    color: theme.conceptWorkflow,
    mark: (
      <>
        <rect x="5" y="4.5" width="14" height="16" rx="2" />
        <path d="M9 4.5V2.8h6v1.7" />
        <path d="M9 9.5h6M9 13h6M9 16.5h4" />
      </>
    ),
  },
  evaluation_run: {
    label: "Eval run",
    color: theme.conceptDerived,
    mark: (
      <>
        <circle cx="12" cy="12" r="8.5" />
        <path d="M10 8.5 16 12l-6 3.5z" fill="currentColor" stroke="none" />
      </>
    ),
  },
  result: {
    label: "Result",
    color: theme.conceptAsset,
    mark: <path d="M4 20V11M10 20V5M16 20v-6M22 20H2" />,
  },
};

const ALIASES: Record<string, ConsoleConcept> = {
  revision: "revision",
  evaluation_design: "evaluation_design",
  evaluation_run: "evaluation_run",
  result: "result",
  finding: "finding",
  proposal: "proposal",
  change_design: "change_design",
  design: "change_design",
};

/** Resolve a catalog kind to a console concept. */
export function conceptFor(kind: string): ConsoleConcept | null {
  return ALIASES[kind] ?? null;
}

/** Resolve an iteration event type to a console concept. */
export function conceptForEvent(type: string): ConsoleConcept | null {
  if (type.startsWith("design_")) return "change_design";
  if (type === "kg_edited") return "revision";
  return conceptFor(type);
}

/** The concept mark, sized by the caller's class or the default. */
export function ConceptMark({
  concept,
  className,
}: {
  concept: ConsoleConcept;
  className?: string;
}) {
  const definition = CONCEPTS[concept];
  return (
    <svg
      className={cx(styles.mark, className)}
      viewBox="2 2 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      style={{ color: definition.color }}
    >
      {definition.mark}
    </svg>
  );
}

/**
 * One concept reference: mark, divider and name, following the design viewer's
 * pill. A count sits after the name when the surface states one.
 */
export function ConceptPill({
  concept,
  label,
  count,
  active = false,
  size = "sm",
  className,
}: {
  concept: ConsoleConcept;
  label?: string;
  count?: number;
  active?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const definition = CONCEPTS[concept];
  return (
    <span
      className={cx(
        styles.pill,
        size === "md" && styles.md,
        size === "lg" && styles.lg,
        active && styles.active,
        className,
      )}
      style={{ "--concept-color": definition.color } as CSSProperties}
    >
      <ConceptMark concept={concept} />
      <span className={styles.divider} aria-hidden="true" />
      <span className={styles.name}>{label ?? definition.label}</span>
      {count !== undefined ? <span className={styles.count}>{count}</span> : null}
    </span>
  );
}
