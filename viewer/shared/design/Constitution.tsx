"use client";

import { Fragment, useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { ConceptGlyph } from "@/shared/ui/ConceptMark";
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
  onOpen,
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
  onOpen?(target: ConstitutionTarget): void;
}) {
  const purpose = node.meaning.purpose;
  const body = text ?? purpose ?? "No purpose is stated.";
  const open = node.open && !node.current ? node.open : undefined;
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
      <div className={styles.constitutionStack}>
        {nodes.length ? (
          nodes.map((node) => (
            <Fragment key={boxKey(node)}>
              <Arrow />
              <Box
                node={node}
                hovered={hoveredKey === boxKey(node)}
                hoverCardId={hoverCardId}
                onHover={onHover}
                onLeave={onLeave}
                onOpen={onOpen}
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
 * The subject as a constitution: purpose and fulfilment are the two top boxes,
 * on opposite sides of the separator, with a horizontal link from fulfilment to
 * purpose. The graph and relation axes sit below; the graph purpose closes the
 * graph chain at the bottom. Hovering or focusing a box reveals its full
 * meaning in a portal, because the band clips overflow.
 */
export function Constitution({ model, onOpen }: ConstitutionProps) {
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
        detail:
          binding.count === 1
            ? [
                binding.identity.length
                  ? `${binding.identity.length} ${
                      binding.identity.length === 1
                        ? "identity field"
                        : "identity fields"
                    }`
                  : "",
                binding.properties ? plural(binding.properties, "property") : "",
              ]
                .filter(Boolean)
                .join(" · ") || undefined
            : undefined,
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
        <Box
          node={model.purpose}
          root
          hovered={hoveredKey === boxKey(model.purpose)}
          hoverCardId={hoverCardId}
          onHover={openHover}
          onLeave={scheduleClose}
          onOpen={onOpen}
        />
        <div className={styles.constitutionSeam} aria-hidden>
          <span className={styles.constitutionSeamLine} />
        </div>
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
            onOpen={onOpen}
          />
        </div>
        <div className={styles.constitutionExchange} aria-hidden>
          <svg viewBox="0 0 82 20" preserveAspectRatio="none">
            <path d="M80 10 H4 M4 10 L14 4 M4 10 L14 16" />
          </svg>
        </div>
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
                onOpen={onOpen}
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
                      onOpen={onOpen}
                    />
                  </div>
                ))}
              </div>
            ) : null}
          </div>
          <span className={styles.constitutionBranchLabel}>Relation</span>
        </div>
      </div>

      <p className={styles.constitutionNote}>
        The graph asserts the purpose; the relation supplies the rows; the
        fulfilment states their meeting.
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
