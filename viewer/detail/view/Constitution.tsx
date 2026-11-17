"use client";

import { Fragment, useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";

import type { ConceptKind } from "@/lib/concepts";
import { ConceptGlyph } from "@/shared/ui/ConceptMark";
import { ConceptPill } from "./ConceptPill";
import { cx } from "@/shared/ui/theme";
import { DesignMeaning } from "@/shared/design/DesignMeaning";
import type { ConstitutionModel, ConstitutionNode } from "../model/constitution";
import styles from "./constitution.module.css";

export interface ConstitutionProps {
  model: ConstitutionModel;
}

const CARD_WIDTH = 440;
const CARD_MAX_HEIGHT = 380;

/** A constitution level names the same layers with one relation spelling. */
function pillConcept(kind: ConstitutionNode["kind"]): ConceptKind {
  return kind === "relation" ? "table" : kind;
}

interface HoveredBox {
  node: ConstitutionNode;
  rect: DOMRect;
}

function plural(count: number, noun: string): string {
  if (count === 1) return `${count} ${noun}`;
  return `${count} ${noun.endsWith("y") ? `${noun.slice(0, -1)}ies` : `${noun}s`}`;
}

function boxKey(node: ConstitutionNode): string {
  return `${node.kind}:${node.name}`;
}

function Box({
  node,
  root = false,
  fulfilment = false,
  hoverable = true,
  text,
  hovered,
  hoverCardId,
  onHover,
  onLeave,
}: {
  node: ConstitutionNode;
  root?: boolean;
  fulfilment?: boolean;
  hoverable?: boolean;
  text?: string;
  hovered: boolean;
  hoverCardId: string;
  onHover(node: ConstitutionNode, element: HTMLElement): void;
  onLeave(): void;
}) {
  const purpose = node.meaning.purpose;
  const body = text ?? purpose ?? "No purpose is stated.";
  return (
    <div
      className={cx(
        styles.constitutionBox,
        root && styles.constitutionBoxRoot,
        fulfilment && styles.constitutionBoxFulfilment,
        node.current && styles.constitutionBoxCurrent,
      )}
      data-root={root || undefined}
      data-fulfilment={fulfilment || undefined}
      data-current={node.current || undefined}
      tabIndex={hoverable ? 0 : undefined}
      onMouseEnter={
        hoverable
          ? (event) => onHover(node, event.currentTarget)
          : undefined
      }
      onMouseLeave={hoverable ? onLeave : undefined}
      onFocus={
        hoverable
          ? (event) => onHover(node, event.currentTarget)
          : undefined
      }
      onBlur={hoverable ? onLeave : undefined}
      aria-label={
        hoverable
          ? `${node.label} ${node.name}: full meaning`
          : undefined
      }
      aria-describedby={hoverable && hovered ? hoverCardId : undefined}
    >
      <div className={styles.constitutionMeta}>
        {fulfilment ? (
          <ConceptGlyph concept="binding" className={styles.constitutionMark} />
        ) : null}
        {root || fulfilment ? (
          <span className={styles.constitutionKind}>{node.label}</span>
        ) : null}
        {fulfilment ? (
          <span className={styles.constitutionName}>{node.name}</span>
        ) : (
          <ConceptPill
            concept={pillConcept(node.kind)}
            name={node.name}
            active={node.current}
          />
        )}
        {node.current ? (
          <span className={styles.constitutionTag} data-current>
            current
          </span>
        ) : !fulfilment && node.detail ? (
          <span className={styles.constitutionTag}>{node.detail}</span>
        ) : null}
      </div>
      <span
        className={cx(
          styles.constitutionText,
          !purpose && !text && styles.constitutionMissing,
        )}
      >
        {body}
      </span>
    </div>
  );
}

function Arrow({ height = 36 }: { height?: number }) {
  return (
    <svg
      className={styles.constitutionArrow}
      style={{ height }}
      viewBox={`0 0 14 ${height}`}
      preserveAspectRatio="none"
      aria-hidden
    >
      <path d={`M7 ${height} L7 1 M2 7 L7 1 L12 7`} />
    </svg>
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
}: {
  side: "graph" | "relation";
  label: string;
  nodes: ConstitutionNode[];
  empty: string;
  hoveredKey?: string;
  hoverCardId: string;
  onHover(node: ConstitutionNode, element: HTMLElement): void;
  onLeave(): void;
}) {
  return (
    <div className={styles.constitutionBranch} data-side={side}>
      <div className={styles.constitutionStack}>
        {nodes.length ? (
          nodes.map((node, index) => (
            <Fragment key={boxKey(node)}>
              {index ? <Arrow /> : null}
              <Box
                node={node}
                hovered={hoveredKey === boxKey(node)}
                hoverCardId={hoverCardId}
                onHover={onHover}
                onLeave={onLeave}
              />
            </Fragment>
          ))
        ) : (
          <p className={styles.constitutionEmpty}>{empty}</p>
        )}
      </div>
      <span className={styles.constitutionBranchLabel}>{label}</span>
    </div>
  );
}

/**
 * The subject as a constitution: purpose sits at the top left and fulfilment one
 * row below on the right, joined by an elbow that rises from fulfilment's top
 * edge into purpose's right edge. The graph and relation axes sit below, and
 * the separator begins below fulfilment. Hovering or focusing a box reveals its
 * full meaning in a portal, because the band clips overflow.
 */
export function Constitution({ model }: ConstitutionProps) {
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

  const hoveredKey = hovered ? boxKey(hovered.node) : undefined;

  const binding = model.binding;
  const bindingNode: ConstitutionNode | undefined = binding
    ? {
        kind: "binding",
        name: plural(binding.count, "binding"),
        label: "Fulfilment",
        meaning: binding.meaning,
      }
    : undefined;
  const bindingKey = bindingNode ? boxKey(bindingNode) : "binding:no binding";
  const bindingText = binding
    ? binding.count === 1
      ? (binding.purpose ?? "No purpose is stated.")
      : `${plural(binding.count, "binding")}${
          binding.identity.length
            ? ` · identity ${binding.identity.join(", ")}`
            : ""
        }`
    : "No binding meets these two axes.";
  const bindingHoverable = Boolean(
    binding &&
      binding.count === 1 &&
      (binding.meaning.purpose ||
        binding.meaning.claims.length ||
        binding.meaning.limitations.length ||
        (binding.meaning.frames?.length ?? 0)),
  );

  const [primaryRelation, ...childRelations] = model.relation;
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
    <div className={styles.constitution} aria-label="Constitution">
      <div className={styles.constitutionTop}>
        <div className={styles.constitutionPurpose}>
          <Box
            node={model.purpose}
            root
            hovered={hoveredKey === boxKey(model.purpose)}
            hoverCardId={hoverCardId}
            onHover={openHover}
            onLeave={scheduleClose}
          />
        </div>

        <span className={styles.constitutionSpan} aria-hidden>
          <svg className={styles.constitutionSpanHead} viewBox="0 0 14 8">
            <path d="M2 7 L7 1 L12 7" />
          </svg>
        </span>

        <div className={styles.constitutionFulfilmentTop}>
          <Box
            node={
              bindingNode ?? {
                kind: "binding",
                name: "no binding",
                label: "Fulfilment",
                meaning: { claims: [], limitations: [], frames: [] },
              }
            }
            fulfilment
            hoverable={bindingHoverable}
            text={bindingText}
            hovered={hoveredKey === bindingKey}
            hoverCardId={hoverCardId}
            onHover={openHover}
            onLeave={scheduleClose}
          />
        </div>

        <span className={styles.constitutionCurveCell} aria-hidden>
          <span className={styles.constitutionCurve}>
            <svg className={styles.constitutionCurveHead} viewBox="0 0 12 12">
              <path d="M10 2 L2 6 L10 10" />
            </svg>
          </span>
        </span>
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
        />

        <div className={styles.constitutionSeam} aria-hidden>
          <span className={styles.constitutionSeamLine} />
        </div>

        <div className={styles.constitutionBranch} data-side="relation">
          <div className={styles.constitutionStack}>
            <Arrow />
            {primaryRelation ? (
              <Box
                node={primaryRelation}
                hovered={hoveredKey === boxKey(primaryRelation)}
                hoverCardId={hoverCardId}
                onHover={openHover}
                onLeave={scheduleClose}
                    />
            ) : (
              <p className={styles.constitutionEmpty}>No relation is shown.</p>
            )}
            {childRelations.length ? (
              <div
                className={styles.constitutionChildren}
                data-count={childRelations.length}
              >
                {childRelations.map((node) => (
                  <div className={styles.constitutionChild} key={boxKey(node)}>
                    <Arrow />
                    <Box
                      node={node}
                      hovered={hoveredKey === boxKey(node)}
                      hoverCardId={hoverCardId}
                      onHover={openHover}
                      onLeave={scheduleClose}
                                />
                  </div>
                ))}
              </div>
            ) : null}
          </div>
          <span className={styles.constitutionBranchLabel}>Relation</span>
        </div>
      </div>

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
