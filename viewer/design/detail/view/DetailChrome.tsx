"use client";

import {
  createContext,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";

import type { ConceptKind } from "@/lib/concepts";
import { concepts } from "@/shared/ui/concepts";
import {
  DetailMark,
  sectionForTitle,
  type DetailSectionKind,
} from "./detailMarks";
import { TabBanner, type TabBannerFact } from "@/shared/ui/TabBanner";
import { Panel } from "@kbs/design";
import { cx } from "@kbs/design";
import styles from "../detail.module.css";

/** The page header's concept, so every section mark takes its colour. */
const DetailPageConceptContext = createContext<ConceptKind>("graph");

/** One constant duration for every card-to-card scroll, near or far. */
const CARD_SCROLL_DURATION = 180;

function scrollCardTo(
  deck: HTMLElement,
  id: string,
  title: string,
  frame: RefObject<number | null>,
  restore: RefObject<(() => void) | null>,
): void {
  if (frame.current !== null) cancelAnimationFrame(frame.current);
  restore.current?.();
  const target =
    document.getElementById(id) ??
    Array.from(
      deck.querySelectorAll<HTMLElement>("[data-detail-band]"),
    ).find((band) => band.dataset.detailTitle === title);
  if (!target) return;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const previousSnap = deck.style.scrollSnapType;
  const previousBehavior = deck.style.scrollBehavior;
  const restoreStyles = () => {
    deck.style.scrollSnapType = previousSnap;
    deck.style.scrollBehavior = previousBehavior;
    restore.current = null;
  };
  restore.current = restoreStyles;
  // Disable snap while the card moves; snap is restored on the exact target.
  deck.style.scrollSnapType = "none";
  deck.style.scrollBehavior = "auto";
  const from = deck.scrollLeft;
  const deckRect = deck.getBoundingClientRect();
  const targetRect = target.getBoundingClientRect();
  const max = Math.max(0, deck.scrollWidth - deck.clientWidth);
  const to = Math.max(
    0,
    Math.min(max, from + targetRect.left - deckRect.left),
  );
  if (reduce || Math.abs(to - from) < 1) {
    deck.scrollLeft = to;
    frame.current = null;
    restoreStyles();
    return;
  }
  const start = performance.now();
  const distance = to - from;
  const step = (now: number) => {
    const progress = Math.min(1, (now - start) / CARD_SCROLL_DURATION);
    const eased = 1 - Math.pow(1 - progress, 3);
    deck.scrollLeft = from + distance * eased;
    if (progress < 1) {
      frame.current = requestAnimationFrame(step);
    } else {
      deck.scrollLeft = to;
      frame.current = null;
      restoreStyles();
    }
  };
  frame.current = requestAnimationFrame(step);
}

interface DetailIndexSection {
  id: string;
  title: string;
  section: DetailSectionKind;
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
        section:
          (band.dataset.detailSection as DetailSectionKind | undefined) ??
          "items",
      }));
      setSections((current) =>
        current.length === next.length &&
        current.every(
          (section, index) =>
            section.id === next[index].id &&
            section.title === next[index].title &&
            section.section === next[index].section,
        )
          ? current
          : next,
      );
    };
    collect();
    const observer = new MutationObserver(collect);
    observer.observe(body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["id", "data-detail-title", "data-detail-section"],
    });
    return () => observer.disconnect();
  }, [bodyRef]);

  return sections;
}

function DetailIndex({
  sections,
  deckRef,
}: {
  sections: DetailIndexSection[];
  deckRef: RefObject<HTMLDivElement | null>;
}) {
  const scrollFrame = useRef<number | null>(null);
  const scrollRestore = useRef<(() => void) | null>(null);

  useEffect(() => {
    const deck = deckRef.current;
    if (!deck) return;
    const cancel = () => {
      if (scrollFrame.current !== null) {
        cancelAnimationFrame(scrollFrame.current);
        scrollFrame.current = null;
      }
      scrollRestore.current?.();
    };
    deck.addEventListener("wheel", cancel, { passive: true });
    deck.addEventListener("pointerdown", cancel);
    return () => {
      cancel();
      deck.removeEventListener("wheel", cancel);
      deck.removeEventListener("pointerdown", cancel);
    };
  }, [deckRef]);

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
                const deck = deckRef.current;
                if (deck) {
                  scrollCardTo(
                    deck,
                    section.id,
                    section.title,
                    scrollFrame,
                    scrollRestore,
                  );
                }
              }}
            >
              <DetailMark
                kind={section.section}
                color="currentColor"
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
    <DetailPageConceptContext.Provider value={concept}>
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
          <DetailIndex sections={sections} deckRef={bodyRef} />
          <div className={styles.deck} ref={bodyRef}>
            {children}
          </div>
        </div>
      </div>
    </DetailPageConceptContext.Provider>
  );
}

export interface DetailBandProps {
  /** Short structural title, for example `Meaning`. */
  title: string;
  /** The question the card answers, in the reader's language. */
  question?: string;
  /** Set only when the title is not one of the structural section titles. */
  section?: DetailSectionKind;
  className?: string;
  flush?: boolean;
  /** A body that owns its height, such as a fitted graph viewport. */
  fill?: boolean;
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
  section,
  className,
  flush = false,
  fill = false,
  testId,
  children,
}: DetailBandProps) {
  const uid = useId().replace(/:/g, "");
  const id = `detail-section-${uid}`;
  const pageConcept = useContext(DetailPageConceptContext);
  const mark = section ?? sectionForTitle(title);
  return (
    <Panel
      as="section"
      id={id}
      className={cx(styles.band, className)}
      aria-label={question ? `${title}: ${question}` : title}
      data-flat
      data-detail-band
      data-detail-title={title}
      data-detail-section={mark}
      data-testid={testId}
    >
      <header className={styles.bandHead}>
        <DetailMark
          kind={mark}
          color={concepts[pageConcept].color}
          className={styles.bandGlyph}
        />
        <h2 className={styles.bandTitle}>{title}</h2>
      </header>
      <div
        className={cx(
          flush ? styles.bandBodyFlush : styles.bandBody,
          fill && styles.bandBodyFill,
        )}
      >
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
