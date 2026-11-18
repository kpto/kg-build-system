"use client";

import {
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";

import type { ConceptKind } from "@/lib/concepts";
import { ConceptGlyph } from "@/shared/ui/ConceptMark";
import { TabBanner, type TabBannerFact } from "@/shared/ui/TabBanner";
import { Panel } from "@/shared/ui/Primitives";
import { cx } from "@/shared/ui/theme";
import styles from "../detail.module.css";

/** The one logo rule for a section title; a view overrides it only when the
 * document kind, not the title, supplies the right mark. */
const SECTION_CONCEPT: Record<string, ConceptKind> = {
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

interface DetailIndexSection {
  id: string;
  title: string;
  concept: ConceptKind;
}

/**
 * The index reads the rendered cards, not a second section list. A band is a
 * card, so the index cannot drift from the document: nested bands are skipped
 * and a card added by any kind appears without touching the index.
 */
function useDetailSections(bodyRef: RefObject<HTMLDivElement | null>) {
  const [sections, setSections] = useState<DetailIndexSection[]>([]);

  useEffect(() => {
    const body = bodyRef.current;
    if (!body) return;
    const collect = () => {
      const bands = Array.from(
        body.querySelectorAll<HTMLElement>("[data-detail-band]"),
      ).filter((band) => !band.parentElement?.closest("[data-detail-band]"));
      const next = bands.map((band) => ({
        id: band.id,
        title: band.dataset.detailTitle ?? "",
        concept:
          (band.dataset.detailConcept as ConceptKind | undefined) ?? "graph",
      }));
      setSections((current) =>
        current.length === next.length &&
        current.every(
          (section, index) =>
            section.id === next[index].id &&
            section.title === next[index].title,
        )
          ? current
          : next,
      );
    };
    collect();
    const observer = new MutationObserver(collect);
    observer.observe(body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [bodyRef]);

  return sections;
}

function DetailIndex({ sections }: { sections: DetailIndexSection[] }) {
  if (sections.length < 2) return null;
  return (
    <nav
      className={styles.index}
      aria-label="Sections in this document"
      data-testid="detail-index"
    >
      <ol className={styles.indexList}>
        {sections.map((section) => (
          <li key={section.id}>
            <a
              className={styles.indexLink}
              href={`#${section.id}`}
              onClick={(event) => {
                event.preventDefault();
                const reduce = window.matchMedia(
                  "(prefers-reduced-motion: reduce)",
                ).matches;
                document.getElementById(section.id)?.scrollIntoView({
                  behavior: reduce ? "auto" : "smooth",
                  block: "nearest",
                  inline: "start",
                });
              }}
            >
              <ConceptGlyph
                concept={section.concept}
                className={styles.indexMark}
              />
              <span className={styles.indexTitle}>{section.title}</span>
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}

export interface DetailDocumentProps {
  concept: ConceptKind;
  kicker: string;
  title: string;
  subtitle?: ReactNode;
  facts?: TabBannerFact[];
  testId?: string;
  children: ReactNode;
}

/**
 * The shared chrome of a detail document: one tab banner and one body of
 * static cards with an index rail. Every kind uses this surface; a kind adds
 * cards, not chrome.
 */
export function DetailDocument({
  concept,
  kicker,
  title,
  subtitle,
  facts,
  testId,
  children,
}: DetailDocumentProps) {
  const bodyRef = useRef<HTMLDivElement>(null);
  const sections = useDetailSections(bodyRef);
  return (
    <div
      className={styles.root}
      data-testid={testId}
      data-concept={concept}
      data-detail-document
    >
      <TabBanner
        concept={concept}
        kicker={kicker}
        title={title}
        subtitle={subtitle}
        facts={facts}
      />
      <div className={styles.body}>
        <DetailIndex sections={sections} />
        <div className={styles.deck} ref={bodyRef}>
          {children}
          <span className={styles.deckTail} aria-hidden />
        </div>
      </div>
    </div>
  );
}

export interface DetailBandProps {
  /** Short structural title, for example `Meaning`. */
  title: string;
  /** The question the card answers, in the reader's language. */
  question?: string;
  concept?: ConceptKind;
  className?: string;
  flush?: boolean;
  testId?: string;
  children: ReactNode;
}

/**
 * One card of a detail document.
 *
 * The cards are static: the body is always visible, and the index rail is the
 * only navigation. The header is structural and shared by every kind, so the
 * card outline, surface and header cannot drift between node, edge, source
 * relation, derived relation or step documents. The body holds content only.
 */
export function DetailBand({
  title,
  question,
  concept,
  className,
  flush = false,
  testId,
  children,
}: DetailBandProps) {
  const uid = useId().replace(/:/g, "");
  const id = `detail-section-${uid}`;
  const mark = concept ?? SECTION_CONCEPT[title] ?? "semantics";
  return (
    <Panel
      as="section"
      id={id}
      className={cx(styles.band, className)}
      aria-label={question ? `${title}: ${question}` : title}
      data-flat
      data-detail-band
      data-detail-title={title}
      data-detail-concept={mark}
      data-testid={testId}
    >
      <header className={styles.bandHead}>
        <ConceptGlyph concept={mark} className={styles.bandGlyph} />
        <h2 className={styles.bandTitle}>{title}</h2>
      </header>
      <div className={flush ? styles.bandBodyFlush : styles.bandBody}>
        {children}
      </div>
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
