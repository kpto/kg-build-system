import { Position } from "@xyflow/react";

/**
 * Explicit geometry for nodes whose size is known before layout.
 *
 * React Flow normally measures node DOM and handle bounds with a
 * ResizeObserver. Supplying the same facts makes edges and fitView available on
 * first paint, including in environments where the observer has not fired yet.
 */
export function measuredNode(width: number, height: number) {
  return { width, height };
}

export function horizontalHandles(width: number, height: number) {
  return [
    {
      type: "target" as const,
      position: Position.Left,
      x: 0,
      y: height / 2,
      width: 1,
      height: 1,
    },
    {
      type: "source" as const,
      position: Position.Right,
      x: width,
      y: height / 2,
      width: 1,
      height: 1,
    },
  ];
}
