"use client";

import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { createPortal } from "react-dom";

import type { ConceptKind } from "@/lib/concepts";
import { concepts } from "@/shared/ui/concepts";
import { ConceptGlyph } from "@/shared/ui/ConceptMark";
import { GraphCanvas } from "@/shared/ui/GraphCanvas";
import { ConceptPill } from "./ConceptPill";
import { cx } from "@/shared/ui/theme";
import { DesignMeaning } from "@/shared/design/DesignMeaning";
import type { ConstitutionModel, ConstitutionNode } from "../model/constitution";
import {
  buildConstitutionScene,
  sceneNodeId,
  type ConstitutionScene,
} from "./constitutionScene";
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

function boxKey(node: ConstitutionNode): string {
  return sceneNodeId(node);
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
  const concept = pillConcept(node.kind);
  return (
    <div
      className={cx(
        styles.constitutionBox,
        root && styles.constitutionBoxRoot,
        fulfilment && styles.constitutionBoxFulfilment,
        node.current && styles.constitutionBoxCurrent,
      )}
      style={
        {
          "--constitution-concept": concepts[concept].color,
        } as CSSProperties
      }
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

/**
 * One renderer for the constitution scene. The scene is a DAG: every node is a
 * declaration box, every edge points from the supply to the consumer, and a
 * shared node is drawn once.
 */
function ConstitutionSceneView({
  scene,
  hoveredKey,
  hoverCardId,
  selectedId,
  onSelect,
  onHover,
  onLeave,
}: {
  scene: ConstitutionScene;
  hoveredKey?: string;
  hoverCardId: string;
  selectedId?: string;
  onSelect(id: string): void;
  onHover(node: ConstitutionNode, element: HTMLElement): void;
  onLeave(): void;
}) {
  const incident = useMemo(() => {
    if (!selectedId) return new Set<string>();
    return new Set(
      scene.edges
        .filter(
          (edge) => edge.source === selectedId || edge.target === selectedId,
        )
        .map((edge) => edge.id),
    );
  }, [scene.edges, selectedId]);

  return (
    <>
      <defs>
        <marker
          id="constitution-arrow"
          viewBox="0 0 8 8"
          refX="8"
          refY="4"
          markerWidth="8"
          markerHeight="8"
          orient="auto"
          markerUnits="userSpaceOnUse"
        >
          <path
            d="M 0 0 L 8 4 L 0 8"
            fill="none"
            stroke="var(--color-selection)"
            strokeWidth="1"
          />
        </marker>
      </defs>

      <g data-constitution-edges pointerEvents="none">
        {scene.edges.map((edge) => {
          const highlighted = incident.has(edge.id);
          return (
            <path
              key={edge.id}
              d={edge.path}
              fill="none"
              stroke={
                highlighted
                  ? "var(--color-selection-strong)"
                  : "var(--color-selection)"
              }
              strokeWidth={highlighted ? 1.6 : 1}
              opacity={selectedId && !highlighted ? 0.12 : 1}
              markerEnd="url(#constitution-arrow)"
              data-constitution-edge={edge.id}
              data-active={highlighted || undefined}
            />
          );
        })}
      </g>

      {scene.seam ? (
        <line
          className={styles.constitutionSceneSeam}
          x1={scene.seam.x}
          y1={scene.seam.y1}
          x2={scene.seam.x}
          y2={scene.seam.y2}
        />
      ) : null}

      <g data-constitution-nodes>
        {scene.nodes.map((node) => (
          <foreignObject
            key={node.id}
            x={node.x}
            y={node.y}
            width={node.width}
            height={node.height}
            opacity={selectedId && node.id !== selectedId ? 0.28 : 1}
          >
            <div
              className={styles.constitutionSceneNode}
              onClick={(event) => {
                event.stopPropagation();
                onSelect(node.id);
              }}
            >
              <Box
                node={node.node}
                root={node.axis === "purpose"}
                fulfilment={node.axis === "fulfilment"}
                hoverable={node.hoverable}
                text={node.text}
                hovered={hoveredKey === boxKey(node.node)}
                hoverCardId={hoverCardId}
                onHover={onHover}
                onLeave={onLeave}
              />
            </div>
          </foreignObject>
        ))}
      </g>

      <g pointerEvents="none">
        {scene.labels.map((label) => (
          <text
            key={label.text}
            className={styles.constitutionSceneLabel}
            x={label.x}
            y={label.y}
            textAnchor="middle"
          >
            {label.text}
          </text>
        ))}
        {scene.notes.map((note) => (
          <text
            key={note.text}
            className={styles.constitutionSceneNote}
            x={note.x}
            y={note.y}
            textAnchor="middle"
          >
            {note.text}
          </text>
        ))}
      </g>
    </>
  );
}

/**
 * The subject as a constitution DAG: purpose, the fulfilment that answers it,
 * the graph ancestry and the relation provenance. Every edge points up from the
 * supply to the consumer; shared declarations are one node. Hovering or
 * focusing a node reveals its full meaning in a portal; selecting a node dims
 * the rest and keeps its incident edges.
 */
export function Constitution({ model }: ConstitutionProps) {
  const [hovered, setHovered] = useState<HoveredBox | null>(null);
  const [selectedId, setSelectedId] = useState<string>();
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

  const scene = useMemo(() => buildConstitutionScene(model), [model]);
  const fitKey = useMemo(
    () =>
      [
        ...scene.nodes.map((node) => node.id),
        ...scene.edges.map((edge) => edge.id),
      ].join("|"),
    [scene],
  );

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
      <GraphCanvas
        width={scene.width}
        height={scene.height}
        className={styles.constitutionCanvas}
        testId="constitution-graph"
        ariaLabel="Constitution graph"
        fitKey={fitKey}
        onBackgroundClick={() => setSelectedId(undefined)}
      >
        <ConstitutionSceneView
          scene={scene}
          hoveredKey={hoveredKey}
          hoverCardId={hoverCardId}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onHover={openHover}
          onLeave={scheduleClose}
        />
      </GraphCanvas>

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
