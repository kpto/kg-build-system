"use client";

import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type Edge,
  type EdgeProps,
} from "@xyflow/react";
import clsx from "clsx";

import type { LinkKind } from "./logic";
import { useTopologyCanvas } from "./canvasContext";

export interface LinkData extends Record<string, unknown> {
  kind: LinkKind;
  label: string;
  /** The IR ref a click selects (the relation component, or the child for hierarchy). */
  ref: string;
}

export type LinkEdge = Edge<LinkData, "link">;

// Green = a bindable relation, purple = an edge category (the shared abstract parent),
// grey dashed = the is-a hierarchy, which is metadata about the graph, never a fact in it.
const STROKE: Record<LinkKind, string> = {
  relation: "var(--color-relation)",
  category: "var(--color-edgekind)",
  hierarchy: "var(--color-category)",
};

const LABEL_TONE: Record<LinkKind, string> = {
  relation: "border-relation/50 bg-relation-soft text-relation",
  category: "border-edgekind/50 bg-raised text-edgekind",
  hierarchy: "border-edge bg-raised text-faint",
};

/**
 * One link on the canvas, drawn in the colour of what it is: a concrete edge is a green
 * labelled relation, an edge category a purple one, and a parent/mixin line a grey dashed
 * hierarchy link (with its own dash pattern so it cannot be mistaken for a relation).
 */
export function LinkEdgeComponent({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  markerEnd,
}: EdgeProps<LinkEdge>) {
  const { onSelectRef } = useTopologyCanvas();
  const [path, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    curvature: 0.28,
  });
  const kind = data?.kind ?? "relation";
  const hierarchy = kind === "hierarchy";

  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        markerEnd={markerEnd}
        style={{
          stroke: STROKE[kind],
          strokeWidth: kind === "relation" ? 2 : 1.5,
          strokeDasharray: hierarchy ? "2 6" : kind === "category" ? "7 4" : undefined,
          opacity: hierarchy ? 0.7 : 1,
        }}
        interactionWidth={20}
      />
      {data?.label && (
        <EdgeLabelRenderer>
          <button
            type="button"
            data-testid={`link-label-${id}`}
            onClick={() => data.ref && onSelectRef(data.ref)}
            className={clsx(
              "studio-chip pointer-events-auto absolute max-w-[10rem] truncate",
              LABEL_TONE[kind],
              hierarchy && "font-sans text-[10px] italic",
            )}
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            }}
            title={`${kind}: ${data.label}`}
          >
            {data.label}
          </button>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
