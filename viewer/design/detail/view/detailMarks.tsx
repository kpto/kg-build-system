import type { ReactNode } from "react";

import { cx } from "@/shared/ui/theme";
import styles from "@/shared/ui/conceptMark.module.css";

/**
 * The section marks of a detail document.
 *
 * A section mark is not a concept: it never becomes a pill, a tab or a
 * navigation target, and it never repeats the page header's concept mark. It
 * names the card's structural role instead. Every mark shares the concept
 * catalogue's grammar — a 24 px grid, a 1.6 px stroke, round joins and a
 * viewBox tight to the drawn content — so a page's marks read at one size even
 * when the card headers use different glyph boxes for different concepts.
 */
export const DETAIL_SECTION_KINDS = [
  "constitution",
  "meaning",
  "contribution",
  "members",
  "connections",
  "bindings",
  "branches",
  "expression",
  "buildSteps",
  "ports",
  "payload",
  "sources",
  "items",
  "coverage",
  "binding",
] as const;

export type DetailSectionKind = (typeof DETAIL_SECTION_KINDS)[number];

export interface DetailMarkDefinition {
  label: string;
  mark: ReactNode;
  /** The tight viewBox around the mark's drawn content, stroke included. */
  box: string;
}

/** Every section mark draws inside the same 18 px content square. */
export const DETAIL_MARK_BOX = "2.35 2.35 19.3 19.3";

/** The one section-logo rule for a structural card title. */
export const DETAIL_SECTION_BY_TITLE: Record<string, DetailSectionKind> = {
  Constitution: "constitution",
  Meaning: "meaning",
  Contribution: "contribution",
  Members: "members",
  Connections: "connections",
  Bindings: "bindings",
  Branches: "branches",
  Expression: "expression",
  "Build steps": "buildSteps",
  Ports: "ports",
  Payload: "payload",
  Sources: "sources",
  Items: "items",
  Coverage: "coverage",
  Binding: "binding",
};

/** Resolve a card title to its section mark; a non-structural title states its
 * section explicitly at the card. */
export function sectionForTitle(title: string): DetailSectionKind {
  return DETAIL_SECTION_BY_TITLE[title] ?? "items";
}

/**
 * One new silhouette per structural card role. The shapes are deliberately
 * different from the concept catalogue: a detail page may show a node header
 * and a Members or Connections card, and the two must not read as the same
 * kind.
 */
export const detailMarks: Record<DetailSectionKind, DetailMarkDefinition> = {
  constitution: {
    label: "Constitution",
    box: DETAIL_MARK_BOX,
    mark: (
      <>
        <rect x="4" y="3" width="16" height="5" rx="1.5" />
        <path d="M12 8v3M6 11h12M6 11v5M18 11v5" />
        <rect x="3" y="16" width="6" height="5" rx="1.5" />
        <rect x="15" y="16" width="6" height="5" rx="1.5" />
      </>
    ),
  },
  meaning: {
    label: "Meaning",
    box: DETAIL_MARK_BOX,
    mark: (
      <>
        <rect x="3" y="3" width="18" height="15" rx="3" />
        <path d="M7 18v3l4.5-3" />
        <path d="M7.5 7.5h9M7.5 10.5h6M7.5 13.5h9" />
      </>
    ),
  },
  contribution: {
    label: "Contribution",
    box: DETAIL_MARK_BOX,
    mark: (
      <>
        <path d="M3 21h6v-7h6V7h5" />
        <path d="M17 3.5 21 7l-4 3.5" />
      </>
    ),
  },
  members: {
    label: "Members",
    box: DETAIL_MARK_BOX,
    mark: (
      <>
        <circle cx="4.5" cy="4.5" r="1.5" />
        <circle cx="4.5" cy="12" r="1.5" />
        <circle cx="4.5" cy="19.5" r="1.5" />
        <path d="M9 4.5h12M9 12h12M9 19.5h12" />
      </>
    ),
  },
  connections: {
    label: "Connections",
    box: DETAIL_MARK_BOX,
    mark: (
      <>
        <circle cx="8.5" cy="8.5" r="5.5" />
        <circle cx="15.5" cy="15.5" r="5.5" />
      </>
    ),
  },
  bindings: {
    label: "Bindings",
    box: DETAIL_MARK_BOX,
    mark: (
      <>
        <path d="M9 3.5H6a3 3 0 0 0-3 3v11a3 3 0 0 0 3 3h3" />
        <path d="M15 3.5h3a3 3 0 0 1 3 3v11a3 3 0 0 1-3 3h-3" />
        <path d="M12 3.5v6M12 14.5v6" />
        <circle cx="12" cy="12" r="2.5" />
      </>
    ),
  },
  branches: {
    label: "Branches",
    box: DETAIL_MARK_BOX,
    mark: (
      <>
        <path d="M12 21v-8.5M12 12.5 5 4.5M12 12.5l7-8" />
        <circle cx="5" cy="4.5" r="1.5" />
        <circle cx="19" cy="4.5" r="1.5" />
      </>
    ),
  },
  expression: {
    label: "Expression",
    box: DETAIL_MARK_BOX,
    mark: (
      <>
        <path d="M10 3C6 3 6 5.5 6 7.5v1c0 1.5-1 2.5-3 3.5 2 1 3 2 3 3.5v1c0 2 0 4.5 4 4.5" />
        <path d="M14 3c4 0 4 2.5 4 4.5v1c0 1.5 1 2.5 3 3.5-2 1-3 2-3 3.5v1c0 2 0 4.5-4 4.5" />
        <circle cx="12" cy="12" r="1.8" />
      </>
    ),
  },
  buildSteps: {
    label: "Build steps",
    box: DETAIL_MARK_BOX,
    mark: (
      <>
        <rect x="3" y="15" width="6" height="6" rx="1.5" />
        <rect x="9" y="9" width="6" height="6" rx="1.5" />
        <rect x="15" y="3" width="6" height="6" rx="1.5" />
      </>
    ),
  },
  ports: {
    label: "Ports",
    box: DETAIL_MARK_BOX,
    mark: (
      <>
        <circle cx="11" cy="12" r="8.5" />
        <circle cx="11" cy="12" r="2.2" />
        <path d="M14 12h2" />
        <rect x="16" y="8.5" width="5" height="7" rx="1.5" />
      </>
    ),
  },
  payload: {
    label: "Payload",
    box: DETAIL_MARK_BOX,
    mark: (
      <>
        <path d="M12 3 21 8v8L12 21 3 16V8z" />
        <path d="M3 8l9 5 9-5M12 13v8" />
      </>
    ),
  },
  sources: {
    label: "Sources",
    box: DETAIL_MARK_BOX,
    mark: <path d="M3 3h18L14 12v6l-4 3V12z" />,
  },
  items: {
    label: "Items",
    box: DETAIL_MARK_BOX,
    mark: (
      <>
        <rect x="3" y="3" width="8" height="8" rx="2" />
        <rect x="13" y="3" width="8" height="8" rx="2" />
        <rect x="3" y="13" width="8" height="8" rx="2" />
        <rect x="13" y="13" width="8" height="8" rx="2" />
      </>
    ),
  },
  coverage: {
    label: "Coverage",
    box: DETAIL_MARK_BOX,
    mark: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 12l5-4" />
        <path d="M12 3v2M21 12h-2M12 21v-2M3 12h2" />
        <circle cx="12" cy="12" r="1.6" />
      </>
    ),
  },
  binding: {
    label: "Binding",
    box: DETAIL_MARK_BOX,
    mark: (
      <>
        <path d="M3 10V6a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3v4" />
        <path d="M3 14v4a3 3 0 0 0 3 3h12a3 3 0 0 0 3-3v-4" />
        <path d="M9 10v4M15 10v4" />
      </>
    ),
  },
};

/**
 * Draw one section mark in the page header's colour. The caller sets the box
 * size, exactly as it does for a concept glyph; the shared tight viewBox and
 * scaled stroke keep every section logo at one visual size.
 */
export function DetailMark({
  kind,
  color,
  className,
  active = false,
}: {
  kind: DetailSectionKind;
  color: string;
  className?: string;
  active?: boolean;
}) {
  const definition = detailMarks[kind];
  const box = definition.box.split(" ").map(Number);
  const boxMax = Math.max(box[2] ?? 24, box[3] ?? 24);
  const strokeWidth = (1.6 * boxMax) / 24;
  return (
    <svg
      aria-hidden
      className={cx(styles.mark, className)}
      style={{ color }}
      viewBox={definition.box}
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      focusable="false"
      data-detail-mark={kind}
      data-active={active || undefined}
    >
      {definition.mark}
    </svg>
  );
}
