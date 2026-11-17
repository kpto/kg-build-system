"use client";

import { useState, type ReactNode } from "react";
import { ChevronRight } from "lucide-react";

import type { ConceptKind } from "@/lib/concepts";
import { ConceptGlyph, ConceptMark } from "@/shared/ui/ConceptMark";
import { Panel, PanelHeaderButton } from "@/shared/ui/Primitives";
import { cx } from "@/shared/ui/theme";
import styles from "../detail.module.css";

/** The one logo rule for a section title; a view overrides it only when the
 * document kind, not the title, supplies the right mark. */
const SECTION_CONCEPT: Record<string, ConceptKind> = {
  Overview: "node",
  Meaning: "semantics",
  Fulfilment: "semantics",
  Sources: "asset",
  "Build steps": "workflow",
  Expression: "graph",
  Members: "field",
  Fields: "field",
  Connections: "edge",
  Bindings: "edge",
  Branches: "edge",
  Ports: "step",
  Payload: "step",
};

export interface DetailLicense {
  value: ReactNode;
  source?: string;
  title?: string;
}

export interface DetailDocumentProps {
  concept: ConceptKind;
  kicker: string;
  title: string;
  subtitle?: ReactNode;
  banner?: ReactNode;
  license?: DetailLicense;
  testId?: string;
  children: ReactNode;
}

/**
 * The shared chrome of a detail document: sticky top bar, title block and one
 * body of full-width bands. Every kind uses this surface; a kind adds bands,
 * not chrome.
 */
export function DetailDocument({
  concept,
  kicker,
  title,
  subtitle,
  banner,
  license,
  testId,
  children,
}: DetailDocumentProps) {
  return (
    <div className={styles.root} data-testid={testId} data-concept={concept}>
      <header className={styles.topbar}>
        <div className={styles.headMain}>
          <ConceptMark concept={concept} className={styles.logo} />
          <div className={styles.titleBlock}>
            <p className={styles.kicker}>{kicker}</p>
            <h1 className={styles.title}>{title}</h1>
            {subtitle ? <p className={styles.subtitle}>{subtitle}</p> : null}
          </div>
        </div>
        {license || banner ? (
          <div className={styles.bannerExtra}>
            {license ? (
              <span
                className={styles.bannerLicense}
                title={license.title}
                data-testid="detail-license"
              >
                <span className={styles.bannerLabel}>license</span>
                <span
                  className={styles.bannerLicenseValue}
                  data-testid="detail-effective-license"
                  data-license-source={license.source}
                >
                  {license.value}
                </span>
              </span>
            ) : null}
            {banner}
          </div>
        ) : null}
      </header>
      <div className={styles.body}>{children}</div>
    </div>
  );
}

export interface DetailBandProps {
  /** Short structural title, for example `Meaning`. */
  title: string;
  /** The question the band answers, in the reader's language. */
  question?: string;
  meta?: ReactNode;
  concept?: ConceptKind;
  className?: string;
  flush?: boolean;
  /** A card's place in the reader order: primary opens, secondary starts closed. */
  priority?: "primary" | "secondary";
  defaultOpen?: boolean;
  testId?: string;
  children: ReactNode;
}

/**
 * One section of a detail document.
 *
 * The header is structural and shared by every kind: a micro title, the
 * question the section answers, and one count. This component is the one card
 * frame: every section in every detail view renders through it, so the card
 * outline, surface and header cannot drift between node, edge, source
 * relation, derived relation or step documents. The body holds content only.
 */
export function DetailBand({
  title,
  question,
  meta,
  concept,
  className,
  flush = false,
  priority = "primary",
  defaultOpen,
  testId,
  children,
}: DetailBandProps) {
  const [open, setOpen] = useState(defaultOpen ?? priority === "primary");
  return (
    <Panel
      as="section"
      className={cx(styles.band, className)}
      data-open={open}
      data-priority={priority}
      data-testid={testId}
    >
      <PanelHeaderButton
        className={styles.bandHead}
        aria-expanded={open}
        aria-label={question ? `${title}: ${question}` : undefined}
        title={question ? `${title}: ${question}` : title}
        onClick={() => setOpen((value) => !value)}
      >
        <ChevronRight aria-hidden className={styles.bandChevron} />
        <ConceptGlyph
          concept={concept ?? SECTION_CONCEPT[title] ?? "semantics"}
          className={styles.bandGlyph}
        />
        <span className={styles.bandTitle}>{title}</span>
        {!open && meta !== undefined ? (
          <span className={styles.bandMeta}>{meta}</span>
        ) : null}
      </PanelHeaderButton>
      {open ? (
        <div className={flush ? styles.bandBodyFlush : styles.bandBody}>
          {children}
        </div>
      ) : null}
    </Panel>
  );
}

export function DetailEmptyState({ children }: { children: ReactNode }) {
  return <p className={styles.inlineEmpty}>{children}</p>;
}

export interface DetailFact {
  label: string;
  value: ReactNode;
  title?: string;
  mono?: boolean;
  /** State that a value is absent instead of dressing it as a value. */
  absent?: boolean;
  /** Allow a long definition or identity to wrap instead of truncating. */
  wrap?: boolean;
  onOpen?(): void;
}

/** One fact grid for every identity strip. */
export function FactGrid({ facts }: { facts: DetailFact[] }) {
  return (
    <dl className={styles.facts}>
      {facts.map((fact) => (
        <div className={styles.fact} key={fact.label}>
          <dt className={styles.factLabel}>{fact.label}</dt>
          <dd
            className={styles.factValue}
            data-honest={fact.absent ? "absent" : undefined}
            data-wrap={fact.wrap ? "true" : undefined}
            title={fact.title ?? (typeof fact.value === "string" ? fact.value : undefined)}
          >
            {fact.onOpen ? (
              <button type="button" onClick={fact.onOpen}>
                {fact.value}
              </button>
            ) : (
              fact.value
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export interface MemberRow {
  key: string;
  cells: ReactNode[];
  title?: string;
  /** Preserve the stable test id a row had before the unified table. */
  testId?: string;
}

/** One table grammar for properties, columns, fields and openings. */
export function MemberTable({
  columns,
  rows,
  empty,
  template,
  testId,
}: {
  columns: string[];
  rows: MemberRow[];
  empty: string;
  /** CSS grid-template-columns shared by the head and every row. */
  template: string;
  testId?: string;
}) {
  if (!rows.length) {
    return <p className={styles.inlineEmpty}>{empty}</p>;
  }
  return (
    <div className={styles.memberTable} data-testid={testId}>
      <div
        className={styles.memberHead}
        style={{ gridTemplateColumns: template }}
        aria-hidden
      >
        {columns.map((column) => (
          <span key={column}>{column}</span>
        ))}
      </div>
      {rows.map((row) => (
        <div
          key={row.key}
          className={styles.memberRow}
          style={{ gridTemplateColumns: template }}
          title={row.title}
          data-testid={row.testId}
        >
          {row.cells.map((cell, index) => (
            <span
              key={index}
              className={styles.memberCell}
              data-mono={index === 0 || undefined}
              data-muted={index > 0 || undefined}
            >
              {cell}
            </span>
          ))}
        </div>
      ))}
    </div>
  );
}
