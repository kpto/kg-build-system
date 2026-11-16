"use client";

import { useState, type ReactNode } from "react";
import { ChevronRight } from "lucide-react";

import type { ConceptKind } from "@/lib/concepts";
import { ConceptGlyph, ConceptMark } from "@/shared/ui/ConceptMark";
import styles from "../detail.module.css";

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
 * outline, surface and header cannot drift between node, edge, table,
 * projection or step documents. The body holds content only.
 */
export function DetailBand({
  title,
  question,
  meta,
  concept,
  className,
  flush = false,
  defaultOpen = true,
  testId,
  children,
}: DetailBandProps) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section
      className={`${styles.band} ${className ?? ""}`}
      data-open={open}
      data-testid={testId}
    >
      <button
        type="button"
        className={styles.bandHead}
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <ChevronRight aria-hidden className={styles.bandChevron} />
        {concept ? (
          <ConceptGlyph concept={concept} className={styles.bandGlyph} />
        ) : null}
        <span className={styles.bandTitle}>{title}</span>
        {question ? <span className={styles.bandQuestion}>{question}</span> : null}
        {meta !== undefined ? (
          <span className={styles.bandMeta}>{meta}</span>
        ) : null}
      </button>
      {open ? (
        <div className={flush ? styles.bandBodyFlush : styles.bandBody}>
          {children}
        </div>
      ) : null}
    </section>
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
  onActivate?(): void;
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
      {rows.map((row) =>
        row.onActivate ? (
          <button
            key={row.key}
            type="button"
            className={styles.memberRow}
            style={{ gridTemplateColumns: template }}
            onClick={row.onActivate}
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
          </button>
        ) : (
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
        ),
      )}
    </div>
  );
}
