"use client";

import { useMemo, useState, type CSSProperties } from "react";

import type { ConceptKind } from "@/lib/concepts";
import { concepts } from "@/shared/ui/concepts";
import { GraphCanvas } from "@/shared/ui/GraphCanvas";
import { ConceptPill } from "./ConceptPill";
import { cx } from "@/shared/ui/theme";
import type { ConstitutionModel, ConstitutionNode } from "../model/constitution";
import {
  buildConstitutionScene,
  type ConstitutionScene,
} from "./constitutionScene";
import styles from "./constitution.module.css";

export interface ConstitutionProps {
  model: ConstitutionModel;
  /** The direction this DAG reads; used for the accessible name. */
  label?: string;
}

/** A constitution level names the same layers with one relation spelling. */
function pillConcept(kind: ConstitutionNode["kind"]): ConceptKind {
  if (kind === "relation") return "table";
  if (kind === "abstract") return "abstractNode";
  return kind;
}

function Box({
  node,
  root = false,
  binding = false,
  text,
  component,
  bindingIndex,
  stepId,
}: {
  node: ConstitutionNode;
  root?: boolean;
  binding?: boolean;
  text?: string;
  component?: string;
  bindingIndex?: number;
  stepId?: [string, string];
}) {
  const meaningPurpose = node.meaning.purpose;
  const body =
    node.text ?? text ?? meaningPurpose ?? "No purpose is stated.";
  const concept = node.abstract
    ? node.kind === "edge"
      ? "abstractEdge"
      : "abstractNode"
    : pillConcept(node.kind);
  return (
    <div
      className={cx(
        styles.constitutionBox,
        root && styles.constitutionBoxRoot,
        binding && styles.constitutionBoxBinding,
        node.current && styles.constitutionBoxCurrent,
      )}
      style={
        {
          "--constitution-concept": concepts[concept].color,
        } as CSSProperties
      }
      data-root={root || undefined}
      data-binding={binding || undefined}
      data-current={node.current || undefined}
    >
      <div className={styles.constitutionMeta}>
        <ConceptPill
          concept={concept}
          name={node.name}
          {...(node.collection ? { collection: node.collection.id } : {})}
          {...((node.component ?? component)
            ? { component: node.component ?? component }
            : {})}
          {...(node.stepId ?? stepId ? { stepId: node.stepId ?? stepId } : {})}
          {...((node.bindingIndex ?? bindingIndex) !== undefined
            ? { bindingIndex: node.bindingIndex ?? bindingIndex }
            : {})}
          size="lg"
          active={node.current}
        />
        {node.current ? (
          <span className={styles.constitutionTag} data-current>
            current
          </span>
        ) : !binding && node.detail ? (
          <span className={styles.constitutionTag}>{node.detail}</span>
        ) : null}
      </div>
      <span
        className={cx(
          styles.constitutionText,
          !meaningPurpose && !text && styles.constitutionMissing,
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
  selectedId,
  onSelect,
}: {
  scene: ConstitutionScene;
  selectedId?: string;
  onSelect(id: string): void;
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
      <g
        transform={`translate(${scene.offset.x} ${scene.offset.y})`}
      >
        <g data-constitution-frames pointerEvents="none">
          {scene.frames.map((frame) => (
            <rect
              key={frame.id}
              className={styles.constitutionFrame}
              data-axis={frame.id}
              x={frame.x}
              y={frame.y}
              width={frame.width}
              height={frame.height}
              rx={6}
            />
          ))}
        </g>

        <g data-constitution-edges pointerEvents="none">
          {scene.edges.map((edge) => {
            const highlighted = incident.has(edge.id);
            const stroke = highlighted
              ? "var(--color-selection-strong)"
              : "var(--color-selection)";
            return (
              <g
                key={edge.id}
                opacity={selectedId && !highlighted ? 0.12 : 1}
              >
                <path
                  d={edge.path}
                  fill="none"
                  stroke={stroke}
                  strokeWidth={highlighted ? 1.6 : 1}
                  data-constitution-edge={edge.id}
                  data-active={highlighted || undefined}
                />
                {edge.head ? (
                  <polygon
                    points="-10,-5 0,0 -10,5"
                    transform={`translate(${edge.head.x} ${edge.head.y}) rotate(${edge.head.angle})`}
                    fill={stroke}
                    data-constitution-head={edge.id}
                  />
                ) : null}
              </g>
            );
          })}
        </g>

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
                  root={node.axis === "subject"}
                  binding={node.axis === "binding" && !node.node.collection}
                  text={node.text}
                  component={node.component}
                  bindingIndex={node.bindingIndex}
                  stepId={node.stepId}
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
              textAnchor="start"
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
      </g>
    </>
  );
}

/**
 * The subject as one constitution DAG: the graph ancestry on the left, the
 * relation provenance on the right and the binding nodes between them in the
 * fulfilment frame. Every edge points up from the supply to the consumer;
 * shared declarations are one node. Selecting a node dims the rest and keeps
 * its incident edges; a node's pill carries the universal concept preview.
 */
export function Constitution({
  model,
  label = "Constitution",
}: ConstitutionProps) {
  const [selectedId, setSelectedId] = useState<string>();

  const scene = useMemo(() => buildConstitutionScene(model), [model]);
  const fitKey = useMemo(
    () =>
      [
        ...scene.nodes.map((node) => node.id),
        ...scene.edges.map((edge) => edge.id),
      ].join("|"),
    [scene],
  );

  return (
    <div className={styles.constitution} aria-label={label}>
      <GraphCanvas
        width={scene.width}
        height={scene.height}
        className={styles.constitutionCanvas}
        testId="constitution-graph"
        ariaLabel={`${label} graph`}
        minFitScale={0.4}
        fitKey={fitKey}
        onBackgroundClick={() => setSelectedId(undefined)}
      >
        <ConstitutionSceneView
          scene={scene}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />
      </GraphCanvas>
    </div>
  );
}
