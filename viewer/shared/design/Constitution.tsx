"use client";

import { Fragment, useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ArrowUp } from "lucide-react";

import { cx } from "@/shared/ui/theme";
import { DesignMeaning } from "./DesignMeaning";
import type {
  ConstitutionModel,
  ConstitutionNode,
  ConstitutionTarget,
} from "./constitution";
import styles from "./design.module.css";

export interface ConstitutionProps {
  model: ConstitutionModel;
  onOpen?(target: ConstitutionTarget): void;
  fullMapOpen?: boolean;
  onToggleFullMap?(): void;
}

const CARD_WIDTH = 440;
const CARD_MAX_HEIGHT = 380;

interface HoveredBox {
  node: ConstitutionNode;
  rect: DOMRect;
}

function plural(count: number, noun: string): string {
  if (count === 1) return `${count} ${noun}`;
  return `${count} ${noun.endsWith("y") ? `${noun.slice(0, -1)}ies` : `${noun}s`}`;
}

function Box({
  node,
  root = false,
  hovered,
  hoverCardId,
  onHover,
  onLeave,
  onOpen,
}: {
  node: ConstitutionNode;
  root?: boolean;
  hovered: boolean;
  hoverCardId: string;
  onHover(node: ConstitutionNode, element: HTMLElement): void;
  onLeave(): void;
  onOpen?(target: ConstitutionTarget): void;
}) {
  const purpose = node.meaning.purpose;
  const open = node.open && !node.current ? node.open : undefined;
  return (
    <div
      className={cx(
        styles.constitutionBox,
        root && styles.constitutionBoxRoot,
        node.current && styles.constitutionBoxCurrent,
      )}
      data-root={root || undefined}
      data-current={node.current || undefined}
      tabIndex={0}
      onMouseEnter={(event) => onHover(node, event.currentTarget)}
      onMouseLeave={onLeave}
      onFocus={(event) => onHover(node, event.currentTarget)}
      onBlur={onLeave}
      aria-label={`${node.label} ${node.name}: full meaning`}
      aria-describedby={hovered ? hoverCardId : undefined}
    >
      <div className={styles.constitutionMeta}>
        <span className={styles.constitutionKind}>{node.label}</span>
        {open && onOpen ? (
          <button
            type="button"
            className={styles.constitutionName}
            onClick={() => onOpen(open)}
            title={`Open ${node.name}`}
          >
            {node.name}
          </button>
        ) : (
          <span className={styles.constitutionName}>{node.name}</span>
        )}
        {node.current ? (
          <span className={styles.constitutionTag} data-current>
            current
          </span>
        ) : node.detail ? (
          <span className={styles.constitutionTag}>{node.detail}</span>
        ) : null}
      </div>
      <span
        className={cx(
          styles.constitutionText,
          !purpose && styles.constitutionMissing,
        )}
      >
        {purpose ?? "No purpose is stated."}
      </span>
    </div>
  );
}

function Branch({
  side,
  label,
  nodes,
  empty,
  hoveredKey,
  hoverCardId,
  onHover,
  onLeave,
  onOpen,
}: {
  side: "graph" | "relation";
  label: string;
  nodes: ConstitutionNode[];
  empty: string;
  hoveredKey?: string;
  hoverCardId: string;
  onHover(node: ConstitutionNode, element: HTMLElement): void;
  onLeave(): void;
  onOpen?(target: ConstitutionTarget): void;
}) {
  return (
    <div className={styles.constitutionBranch} data-side={side}>
      <span className={styles.constitutionBranchLabel}>{label}</span>
      <div className={styles.constitutionStack}>
        {nodes.length ? (
          nodes.map((node) => {
            const key = `${node.kind}:${node.name}`;
            return (
              <Fragment key={key}>
                <span className={styles.constitutionArrow} aria-hidden>
                  <ArrowUp size={13} strokeWidth={1.8} />
                </span>
                <Box
                  node={node}
                  hovered={hoveredKey === key}
                  hoverCardId={hoverCardId}
                  onHover={onHover}
                  onLeave={onLeave}
                  onOpen={onOpen}
                />
              </Fragment>
            );
          })
        ) : (
          <p className={styles.constitutionEmpty}>{empty}</p>
        )}
      </div>
    </div>
  );
}

/**
 * The subject as a constitution: one purpose at the root, the graph and
 * relation axes descending from it, and the binding seam between them.
 *
 * The two branches are read as a tree, not as a Cartesian plot: each level
 * points up to the level it is accountable to, and the dashed centre states
 * that a binding is what lets one axis meet the other. Hovering or focusing a
 * box reveals its full meaning in a portal, because the band clips overflow.
 */
export function Constitution({
  model,
  onOpen,
  fullMapOpen = false,
  onToggleFullMap,
}: ConstitutionProps) {
  const [hovered, setHovered] = useState<HoveredBox | null>(null);
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

  const openHover = (node: ConstitutionNode, element: HTMLElement) => {
    cancelClose();
    setHovered({ node, rect: element.getBoundingClientRect() });
  };

  const hoveredKey = hovered
    ? `${hovered.node.kind}:${hovered.node.name}`
    : undefined;
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

  const binding = model.binding;

  return (
    <div className={styles.constitution} aria-label="Constitution">
      <div className={styles.constitutionRoot}>
        <Box
          node={model.purpose}
          root
          hovered={
            hoveredKey === `${model.purpose.kind}:${model.purpose.name}`
          }
          hoverCardId={hoverCardId}
          onHover={openHover}
          onLeave={scheduleClose}
          onOpen={onOpen}
        />
      </div>

      <div className={styles.constitutionBranches}>
        <Branch
          side="graph"
          label="Graph"
          nodes={model.graph}
          empty="No record is bound."
          hoveredKey={hoveredKey}
          hoverCardId={hoverCardId}
          onHover={openHover}
          onLeave={scheduleClose}
          onOpen={onOpen}
        />
        <div className={styles.constitutionSeam} aria-hidden>
          <span className={styles.constitutionSeamLine} />
        </div>
        <Branch
          side="relation"
          label="Relation"
          nodes={model.relation}
          empty="No relation is shown."
          hoveredKey={hoveredKey}
          hoverCardId={hoverCardId}
          onHover={openHover}
          onLeave={scheduleClose}
          onOpen={onOpen}
        />
      </div>

      <div
        className={styles.constitutionBinding}
        data-empty={binding ? undefined : true}
      >
        <span className={styles.constitutionBindingLabel}>Fulfilment</span>
        {binding ? (
          <>
            <span className={styles.constitutionBindingText}>
              {plural(binding.count, "binding")}
              {binding.identity.length
                ? ` · identity ${binding.identity.join(", ")}`
                : ""}
              {binding.count === 1 && binding.properties
                ? ` · ${plural(binding.properties, "property")}`
                : ""}
            </span>
            {onToggleFullMap ? (
              <button
                type="button"
                className={styles.constitutionMapToggle}
                aria-expanded={fullMapOpen}
                onClick={onToggleFullMap}
              >
                {fullMapOpen ? "Hide axis map" : "Full axis map"}
              </button>
            ) : null}
          </>
        ) : (
          <span className={styles.constitutionBindingText}>
            No binding meets these two axes.
          </span>
        )}
      </div>
      {binding?.purpose ? (
        <p className={styles.constitutionBindingPurpose}>{binding.purpose}</p>
      ) : null}
      <p className={styles.constitutionNote}>
        The graph asserts the purpose; the relation supplies the rows; the
        binding states their meeting.
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
                <span>{hovered.node.label}</span>
                <strong>{hovered.node.name}</strong>
                <span>full meaning</span>
              </header>
              <DesignMeaning
                claims={hovered.node.meaning.claims}
                limitations={hovered.node.meaning.limitations}
                purpose={hovered.node.meaning.purpose}
                frames={hovered.node.meaning.frames}
                emptyText="Meaning omitted at this level."
              />
            </aside>,
            document.body,
          )
        : null}
    </div>
  );
}
