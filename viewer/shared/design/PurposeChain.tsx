"use client";

import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ArrowDown } from "lucide-react";

import { cx } from "@/shared/ui/theme";
import { DesignMeaning } from "./DesignMeaning";
import type { PurposeLevel } from "./meaning";
import styles from "./design.module.css";

export interface PurposeChainProps {
  levels: PurposeLevel[];
  onOpen?(level: PurposeLevel): void;
  emptyText?: string;
}

/** The root is the broad premise; each narrower purpose is 14% shorter. */
const WIDTH_STEP = 14;
const CARD_WIDTH = 420;
const CARD_MAX_HEIGHT = 360;

interface HoveredLevel {
  level: PurposeLevel;
  rect: DOMRect;
}

/**
 * The record-axis purpose chain: labels on the left, a tapering purpose box on
 * the right.
 *
 * A label navigates to that level's document. The box is not a control: hovering
 * or focusing it reveals the level's full meaning — purpose, exclusions and
 * claims — in a portal, because the band clips its own overflow. Each box states
 * only the purpose and clamps it, so the chain stays compact.
 */
export function PurposeChain({
  levels,
  onOpen,
  emptyText = "Meaning omitted.",
}: PurposeChainProps) {
  const [hovered, setHovered] = useState<HoveredLevel | null>(null);
  const closeTimer = useRef<number | null>(null);
  const cardRef = useRef<HTMLElement | null>(null);
  const hoverCardId = useId();

  const cancelClose = () => {
    if (closeTimer.current !== null) {
      window.clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  };

  const scheduleClose = () => {
    cancelClose();
    closeTimer.current = window.setTimeout(() => setHovered(null), 140);
  };

  useEffect(() => cancelClose, []);

  useEffect(() => {
    if (!hovered) return;
    const close = () => setHovered(null);
    const outside = (event: Event) => {
      if (cardRef.current?.contains(event.target as Node)) return;
      close();
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    window.addEventListener("scroll", close, true);
    window.addEventListener("resize", close);
    document.addEventListener("pointerdown", outside, true);
    window.addEventListener("keydown", escape);
    return () => {
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("resize", close);
      document.removeEventListener("pointerdown", outside, true);
      window.removeEventListener("keydown", escape);
    };
  }, [hovered]);

  if (!levels.length) {
    return <p className={styles.purposeEmpty}>{emptyText}</p>;
  }

  const openHover = (level: PurposeLevel, element: HTMLElement) => {
    cancelClose();
    setHovered({ level, rect: element.getBoundingClientRect() });
  };

  const hoveredLeft = hovered
    ? Math.min(
        Math.max(12, hovered.rect.left),
        Math.max(12, window.innerWidth - CARD_WIDTH - 12),
      )
    : 0;
  const hoveredTop = hovered
    ? hovered.rect.bottom + 8 + CARD_MAX_HEIGHT > window.innerHeight
      ? Math.max(12, hovered.rect.top - CARD_MAX_HEIGHT - 8)
      : hovered.rect.bottom + 8
    : 0;

  return (
    <div className={styles.purposeChain} aria-label="Purpose hierarchy">
      <div className={styles.purposeLevels}>
        {levels.map((level, index) => {
          const current = Boolean(level.current);
          const navigable =
            !current && level.kind !== "graph" && Boolean(onOpen);
          const purpose = level.meaning.purpose;
          const text = purpose ?? "No purpose is stated.";
          const width = 100 - index * WIDTH_STEP;
          const meta = (
            <>
              <span className={styles.purposeKind}>{level.label}</span>
              <span className={styles.purposeName}>{level.name}</span>
              {current ? (
                <span className={styles.purposeTag} data-current>
                  current
                </span>
              ) : index === 0 ? (
                <span className={styles.purposeTag}>root</span>
              ) : null}
            </>
          );
          return (
            <div
              className={styles.purposeLevel}
              key={`${level.kind}:${level.name}`}
            >
              {index > 0 ? (
                <div className={styles.purposeConnectorRow} aria-hidden>
                  <span />
                  <div
                    className={styles.purposeConnectorCell}
                    style={{ width: `${width}%` }}
                  >
                    <span className={styles.purposeConnectorLine} />
                    <ArrowDown size={13} strokeWidth={1.8} />
                  </div>
                </div>
              ) : null}
              <div
                className={styles.purposeRow}
                data-current={current || undefined}
              >
                {navigable ? (
                  <button
                    type="button"
                    className={styles.purposeMeta}
                    onClick={() => onOpen?.(level)}
                    title={`Open ${level.name}`}
                  >
                    {meta}
                  </button>
                ) : (
                  <div className={styles.purposeMeta}>{meta}</div>
                )}
                <div
                  className={styles.purposeBox}
                  style={{ width: `${width}%` }}
                  tabIndex={0}
                  onMouseEnter={(event) => openHover(level, event.currentTarget)}
                  onMouseLeave={scheduleClose}
                  onFocus={(event) => openHover(level, event.currentTarget)}
                  onBlur={scheduleClose}
                  aria-label={`${level.label} ${level.name}: full meaning`}
                  aria-describedby={
                    hovered?.level.kind === level.kind &&
                    hovered.level.name === level.name
                      ? hoverCardId
                      : undefined
                  }
                >
                  <span
                    className={cx(
                      styles.purposeText,
                      !purpose && styles.purposeMissing,
                    )}
                  >
                    {text}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <p className={styles.purposeNote}>
        Each local purpose is read under the one above and narrows it; every
        level keeps its own text, so the chain shows derivation, not copied
        meaning.
      </p>
      {hovered
        ? createPortal(
            <aside
              ref={cardRef}
              className={styles.purposeHover}
              style={{
                left: hoveredLeft,
                top: hoveredTop,
                width: CARD_WIDTH,
              }}
              id={hoverCardId}
              role="tooltip"
              onMouseEnter={cancelClose}
              onMouseLeave={scheduleClose}
            >
              <header className={styles.purposeHoverHead}>
                <span>{hovered.level.label}</span>
                <strong>{hovered.level.name}</strong>
                <span>full meaning</span>
              </header>
              <DesignMeaning
                claims={hovered.level.meaning.claims}
                limitations={hovered.level.meaning.limitations}
                purpose={hovered.level.meaning.purpose}
                frames={hovered.level.meaning.frames}
                emptyText="Meaning omitted at this level."
              />
            </aside>,
            document.body,
          )
        : null}
    </div>
  );
}
