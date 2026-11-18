"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";
import { createPortal } from "react-dom";

import type { ConceptKind, ConceptTarget } from "@/lib/concepts";
import { meaningCount, type DesignMeaningValue } from "@/shared/design/meaning";
import { DesignMeaning } from "@/shared/design/DesignMeaning";
import { ConceptGlyph } from "./ConceptMark";
import { concepts } from "./concepts";

import styles from "./conceptPreview.module.css";

export interface ConceptPreviewFact {
  label: string;
  value: string;
}

/**
 * One concept instance as a preview. The model is resolved from the design,
 * not from the document: a pill can preview an instance before opening it, and
 * the same card serves every concept.
 */
export interface ConceptPreviewModel {
  concept: ConceptKind;
  name: string;
  /** The specific role, for example `Abstract node` or `Source relation`. */
  kind: string;
  /** The instance's immediate context: owner, container, source, target or
   * endpoints. Every preview states one. */
  subtitle: string;
  facts: ConceptPreviewFact[];
  meaning?: DesignMeaningValue;
}

export interface ConceptPreviewProviderValue {
  preview(target: ConceptTarget): ConceptPreviewModel | undefined;
}

const ConceptPreviewContext =
  createContext<ConceptPreviewProviderValue | null>(null);

export function ConceptPreviewProvider({
  value,
  children,
}: {
  value: ConceptPreviewProviderValue;
  children: ReactNode;
}) {
  return (
    <ConceptPreviewContext.Provider value={value}>
      {children}
    </ConceptPreviewContext.Provider>
  );
}

/** One preview at a time: opening a pill's preview dismisses the previous one. */
let activePreviewDismiss: (() => void) | null = null;

const CARD_WIDTH = 380;
const CARD_MAX_HEIGHT = 420;
const CARD_MARGIN = 12;
const CLOSE_DELAY = 140;

/**
 * The one hover/focus preview used by pills.
 *
 * The card answers one question — what is this instance? — before the reader
 * commits to opening it. It is grouped into identity, facts and meaning so the
 * preview can be scanned rather than read as a wall of text.
 */
export function useConceptPreview(target: ConceptTarget) {
  const provider = useContext(ConceptPreviewContext);
  const [state, setState] = useState<{
    model: ConceptPreviewModel;
    rect: DOMRect;
  } | null>(null);
  const closeTimer = useRef<number | null>(null);
  const cardRef = useRef<HTMLElement | null>(null);
  const id = `concept-preview-${useId().replace(/:/g, "")}`;

  const cancelClose = useCallback(() => {
    if (closeTimer.current !== null) {
      window.clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  }, []);

  const dismiss = useCallback(() => {
    cancelClose();
    setState(null);
  }, [cancelClose]);

  const scheduleClose = useCallback(() => {
    cancelClose();
    closeTimer.current = window.setTimeout(() => setState(null), CLOSE_DELAY);
  }, [cancelClose]);

  useEffect(() => {
    return () => cancelClose();
  }, [cancelClose]);

  useEffect(() => {
    if (!state) return;
    activePreviewDismiss = dismiss;
    return () => {
      if (activePreviewDismiss === dismiss) activePreviewDismiss = null;
    };
  }, [dismiss, state]);

  useEffect(() => {
    if (!state) return;
    // A scroll inside the card is the reader reading the preview. Only a
    // scroll outside it dismisses the card.
    const outside = (event: Event) => {
      if (cardRef.current?.contains(event.target as Node)) return;
      dismiss();
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") dismiss();
    };
    window.addEventListener("scroll", outside, true);
    window.addEventListener("resize", dismiss);
    document.addEventListener("pointerdown", outside, true);
    window.addEventListener("keydown", escape);
    return () => {
      window.removeEventListener("scroll", outside, true);
      window.removeEventListener("resize", dismiss);
      document.removeEventListener("pointerdown", outside, true);
      window.removeEventListener("keydown", escape);
    };
  }, [dismiss, state]);

  const open = (element: HTMLElement) => {
    if (!provider) return;
    const model = provider.preview(target);
    if (!model) return;
    activePreviewDismiss?.();
    cancelClose();
    setState({ model, rect: element.getBoundingClientRect() });
  };

  const popup =
    state && typeof window !== "undefined" ? (
      <ConceptPreviewCard
        id={id}
        model={state.model}
        rect={state.rect}
        cardRef={cardRef}
        onEnter={cancelClose}
        onLeave={scheduleClose}
      />
    ) : null;

  return {
    open,
    cancelClose,
    scheduleClose,
    dismiss,
    describedBy: state ? id : undefined,
    popup,
  };
}

function ConceptPreviewCard({
  id,
  model,
  rect,
  cardRef,
  onEnter,
  onLeave,
}: {
  id: string;
  model: ConceptPreviewModel;
  rect: DOMRect;
  cardRef: RefObject<HTMLElement | null>;
  onEnter(): void;
  onLeave(): void;
}) {
  const width = Math.min(CARD_WIDTH, window.innerWidth - CARD_MARGIN * 2);
  const left = Math.min(
    Math.max(CARD_MARGIN, rect.left),
    Math.max(CARD_MARGIN, window.innerWidth - width - CARD_MARGIN),
  );
  const below = rect.bottom + 8 + CARD_MAX_HEIGHT <= window.innerHeight;
  const top = below
    ? rect.bottom + 8
    : Math.max(CARD_MARGIN, rect.top - CARD_MAX_HEIGHT - 8);

  return createPortal(
    <aside
      ref={cardRef}
      id={id}
      role="tooltip"
      aria-label={`${model.kind} ${model.name} preview`}
      className={styles.card}
      style={{ left, top, width }}
      data-testid="concept-preview"
      data-concept={model.concept}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
    >
      <header className={styles.identity}>
        <ConceptGlyph concept={model.concept} className={styles.mark} />
        <p className={styles.name}>{model.name}</p>
      </header>
      {model.kind !== concepts[model.concept].label ? (
        <p className={styles.role}>{model.kind}</p>
      ) : null}
      <p className={styles.subtitle}>{model.subtitle}</p>

      {model.facts.length ? (
        <dl className={styles.facts}>
          {model.facts.map((fact) => (
            <div className={styles.fact} key={fact.label}>
              <dt>{fact.label}</dt>
              <dd title={fact.value}>{fact.value}</dd>
            </div>
          ))}
        </dl>
      ) : null}

      {model.meaning && meaningCount(model.meaning) > 0 ? (
        <div className={styles.meaning}>
          <DesignMeaning
            compact
            claims={model.meaning.claims}
            limitations={model.meaning.limitations}
            purpose={model.meaning.purpose}
            frames={model.meaning.frames}
          />
        </div>
      ) : null}
    </aside>,
    document.body,
  );
}
