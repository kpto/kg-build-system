"use client";

import { useMemo, type MouseEvent as ReactMouseEvent } from "react";

import type { StepId, ViewerIndex } from "@/lib/types";
import { stepKey } from "@/lib/indexes";
import { GraphCanvas } from "./GraphCanvas";
import { groupPalette, theme } from "@kbs/design";

/** The row shape a workflow DAG needs; the workflow model's row is one. */
export interface WorkflowDagStep {
  key: string;
  id: StepId;
  component: string;
  name: string;
  kind: string[] | undefined;
  kindKey: string;
  kindLabel: string;
  inputs: number;
  outputs: number;
  connections: number;
}

/** The component map a compositor scene needs; the workflow model's map is one. */
export interface WorkflowDagComponentNode {
  id: string;
  steps: number;
}

export interface WorkflowDagComponentEdge {
  id: string;
  source: string;
  target: string;
  count: number;
}

export interface WorkflowDagComponentMap {
  nodes: WorkflowDagComponentNode[];
  edges: WorkflowDagComponentEdge[];
}

const STEP_NODE_WIDTH = 220;
const STEP_NODE_HEIGHT = 72;
const STEP_HEADER_HEIGHT = 22;
const STEP_GAP_X = 46;
const STEP_LAYER_GAP_X = 76;
const STEP_GAP_Y = 24;
const STEP_MIN_ROWS = 6;
const STEP_MAX_ROWS = 28;
const STEP_MARGIN = 36;
const BOUNDARY_WIDTH = 150;
const BOUNDARY_HEIGHT = 72;
const VERTICAL_STEP_WIDTH = 180;
const VERTICAL_STEP_GAP_X = 32;

type WorkflowDagNodeKind = "component" | "step" | "in" | "out";

/**
 * One node in the workflow scene. A component, a step and a boundary node are
 * the same value; only the facts and the size differ.
 */
export interface WorkflowDagNode {
  id: string;
  kind: WorkflowDagNodeKind;
  label: string;
  detail: string;
  meta?: string;
  note?: string;
  tint: string;
  x: number;
  y: number;
  width: number;
  height: number;
  headerHeight: number;
  socketY: number;
  dataTestId: string;
  row?: WorkflowDagStep;
  component?: string;
  /** A step in a top-to-bottom DAG: sockets sit on the top and bottom edges. */
  vertical?: boolean;
}

/** One link in the workflow scene; the same renderer draws every link kind. */
export interface WorkflowDagEdge {
  id: string;
  source: string;
  target: string;
  path: string;
  dataTestId: string;
  boundary?: boolean;
  weight?: number;
  label?: string;
  labelX?: number;
  labelY?: number;
  sourceX?: number;
  sourceY?: number;
  targetX?: number;
  targetY?: number;
}

interface WorkflowDagStats {
  stepCount: number;
  internalEdges: number;
  boundaryCount: number;
}

export interface WorkflowDagScene {
  nodes: WorkflowDagNode[];
  edges: WorkflowDagEdge[];
  width: number;
  height: number;
  stats?: WorkflowDagStats;
}

const NODE_WIDTH = 208;
const NODE_HEIGHT = 78;
const HEADER_HEIGHT = 28;
const COLUMN_GAP = 68;
const ROW_GAP = 56;
const MARGIN = 36;
const SOCKET_Y = 50;

function dependencyLayers(
  ids: string[],
  edges: ReadonlyArray<{ source: string; target: string }>,
): Map<string, number> {
  const known = new Set(ids);
  const layer = new Map(ids.map((id) => [id, 0]));
  const outgoing = new Map<string, Set<string>>();
  for (const edge of edges) {
    if (edge.source === edge.target) continue;
    if (!known.has(edge.source) || !known.has(edge.target)) continue;
    const targets = outgoing.get(edge.source) ?? new Set<string>();
    targets.add(edge.target);
    outgoing.set(edge.source, targets);
  }
  // Longest-path layering. Cycles are capped to one column step per node.
  for (let pass = 0; pass < ids.length; pass += 1) {
    let changed = false;
    for (const [source, targets] of outgoing) {
      for (const target of targets) {
        const next = (layer.get(source) ?? 0) + 1;
        if (next < ids.length && next > (layer.get(target) ?? 0)) {
          layer.set(target, next);
          changed = true;
        }
      }
    }
    if (!changed) break;
  }
  return layer;
}

function componentLayers(
  ids: string[],
  edges: WorkflowDagComponentEdge[],
): Map<string, number> {
  return dependencyLayers(ids, edges);
}

/**
 * Group ids by dependency layer and order each layer by the barycentre of its
 * neighbours in the adjacent layer. The original order breaks ties, so the
 * result is deterministic and a repeated input never reshuffles settled nodes.
 */
function layeredOrder(
  ids: string[],
  edges: ReadonlyArray<{ source: string; target: string }>,
  layer: Map<string, number>,
): string[][] {
  const known = new Set(ids);
  const original = new Map(ids.map((id, index) => [id, index]));
  const predecessors = new Map<string, Set<string>>();
  const successors = new Map<string, Set<string>>();
  for (const edge of edges) {
    if (edge.source === edge.target) continue;
    if (!known.has(edge.source) || !known.has(edge.target)) continue;
    const sources = predecessors.get(edge.target) ?? new Set<string>();
    sources.add(edge.source);
    predecessors.set(edge.target, sources);
    const targets = successors.get(edge.source) ?? new Set<string>();
    targets.add(edge.target);
    successors.set(edge.source, targets);
  }

  const columns = new Map<number, string[]>();
  for (const id of ids) {
    const index = layer.get(id) ?? 0;
    const column = columns.get(index) ?? [];
    column.push(id);
    columns.set(index, column);
  }
  const layerIds = [...columns.keys()].sort((left, right) => left - right);
  for (const column of columns.values()) {
    column.sort(
      (left, right) =>
        (original.get(left) ?? 0) - (original.get(right) ?? 0),
    );
  }

  const position = new Map<string, number>();
  for (const layerId of layerIds) {
    (columns.get(layerId) ?? []).forEach((id, index) => position.set(id, index));
  }

  const order = (
    column: string[],
    neighbours: Map<string, Set<string>>,
  ) => {
    const score = new Map<string, number>();
    for (const id of column) {
      const values = [...(neighbours.get(id) ?? [])]
        .map((neighbour) => position.get(neighbour))
        .filter((value): value is number => value !== undefined);
      if (values.length) {
        score.set(
          id,
          values.reduce((total, value) => total + value, 0) / values.length,
        );
      }
    }
    column.sort((left, right) => {
      const leftScore = score.get(left);
      const rightScore = score.get(right);
      if (leftScore !== undefined && rightScore !== undefined) {
        if (leftScore !== rightScore) return leftScore - rightScore;
      } else if (leftScore !== undefined) {
        return -1;
      } else if (rightScore !== undefined) {
        return 1;
      }
      return (original.get(left) ?? 0) - (original.get(right) ?? 0);
    });
  };

  // Alternate direction so both predecessor and successor barycentres settle.
  for (let pass = 0; pass < 4; pass += 1) {
    const forward = pass % 2 === 0;
    const passLayers = forward
      ? layerIds.slice(1)
      : [...layerIds.slice(0, -1)].reverse();
    for (const layerId of passLayers) {
      const column = columns.get(layerId);
      if (!column) continue;
      order(column, forward ? predecessors : successors);
      column.forEach((id, index) => position.set(id, index));
    }
  }

  return layerIds.map((layerId) => columns.get(layerId) ?? []);
}

export function buildCompositorScene(
  map: WorkflowDagComponentMap,
  options: { direction?: "horizontal" | "vertical" } = {},
): WorkflowDagScene {
  const vertical = options.direction === "vertical";
  const ids = map.nodes.map((node) => node.id);
  const layer = componentLayers(ids, map.edges);
  const order = new Map(ids.map((id, index) => [id, index]));
  const columns = new Map<number, typeof map.nodes>();
  for (const node of map.nodes) {
    const index = layer.get(node.id) ?? 0;
    const column = columns.get(index) ?? [];
    column.push(node);
    columns.set(index, column);
  }
  for (const column of columns.values()) {
    column.sort((left, right) => (order.get(left.id) ?? 0) - (order.get(right.id) ?? 0));
  }

  const internal = new Map<string, number>();
  for (const edge of map.edges) {
    if (edge.source !== edge.target) continue;
    internal.set(edge.source, (internal.get(edge.source) ?? 0) + edge.count);
  }

  const layerIds = [...columns.keys()].sort((left, right) => left - right);
  const maxRows = Math.max(1, ...layerIds.map((id) => columns.get(id)?.length ?? 0));
  let width =
    MARGIN * 2 +
    layerIds.length * NODE_WIDTH +
    Math.max(0, layerIds.length - 1) * COLUMN_GAP;
  let height =
    MARGIN * 2 +
    maxRows * NODE_HEIGHT +
    Math.max(0, maxRows - 1) * ROW_GAP;
  const bodyHeight = maxRows * NODE_HEIGHT + Math.max(0, maxRows - 1) * ROW_GAP;

  const placed = new Map<
    string,
    {
      node: WorkflowDagComponentMap["nodes"][number];
      x: number;
      y: number;
      color: string;
      internal: number;
    }
  >();
  if (vertical) {
    const layerWidths = layerIds.map((layerId) => {
      const column = columns.get(layerId) ?? [];
      return (
        column.length * NODE_WIDTH +
        Math.max(0, column.length - 1) * COLUMN_GAP
      );
    });
    const maxWidth = Math.max(1, ...layerWidths);
    let cursorY = MARGIN;
    layerIds.forEach((layerId, layerIndex) => {
      const column = columns.get(layerId) ?? [];
      let cursorX = MARGIN + (maxWidth - (layerWidths[layerIndex] ?? 0)) / 2;
      column.forEach((node) => {
        placed.set(node.id, {
          node,
          x: cursorX,
          y: cursorY,
          color: groupPalette[(order.get(node.id) ?? 0) % groupPalette.length],
          internal: internal.get(node.id) ?? 0,
        });
        cursorX += NODE_WIDTH + COLUMN_GAP;
      });
      cursorY += NODE_HEIGHT + ROW_GAP;
    });
    width = maxWidth + MARGIN * 2;
    height = cursorY - ROW_GAP + MARGIN;
  } else {
    layerIds.forEach((layerId, columnIndex) => {
      const column = columns.get(layerId) ?? [];
      const columnHeight =
        column.length * NODE_HEIGHT +
        Math.max(0, column.length - 1) * ROW_GAP;
      const top = MARGIN + (bodyHeight - columnHeight) / 2;
      column.forEach((node, rowIndex) => {
        placed.set(node.id, {
          node,
          x: MARGIN + columnIndex * (NODE_WIDTH + COLUMN_GAP),
          y: top + rowIndex * (NODE_HEIGHT + ROW_GAP),
          color: groupPalette[(order.get(node.id) ?? 0) % groupPalette.length],
          internal: internal.get(node.id) ?? 0,
        });
      });
    });
  }

  const nodes: WorkflowDagNode[] = [...placed.values()].map(
    ({ node, x, y, color, internal: inner }) => ({
      id: node.id,
      kind: "component",
      label: node.id,
      detail: `${node.steps} steps`,
      tint: color,
      x,
      y,
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
      headerHeight: HEADER_HEIGHT,
      socketY: SOCKET_Y,
      dataTestId: "workflow-component-node",
      component: node.id,
      vertical: vertical || undefined,
    }),
  );

  const edges: WorkflowDagEdge[] = [];
  for (const edge of map.edges) {
    if (edge.source === edge.target) continue;
    const source = placed.get(edge.source);
    const target = placed.get(edge.target);
    if (!source || !target) continue;
    const sx = vertical ? source.x + NODE_WIDTH / 2 : source.x + NODE_WIDTH;
    const sy = vertical ? source.y + NODE_HEIGHT : source.y + SOCKET_Y;
    const tx = vertical ? target.x + NODE_WIDTH / 2 : target.x;
    const ty = vertical ? target.y : target.y + SOCKET_Y;
    const forward = tx >= sx;
    const dx = forward
      ? Math.max(56, (tx - sx) * 0.48)
      : 96;
    const dy = Math.max(40, Math.abs(ty - sy) * 0.5);
    const c1x = sx + dx;
    const c1y = sy;
    const c2x = tx - dx;
    const c2y = ty;
    edges.push({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      path: vertical
        ? `M ${sx} ${sy} C ${sx} ${sy + dy}, ${tx} ${ty - dy}, ${tx} ${ty}`
        : `M ${sx} ${sy} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${tx} ${ty}`,
      dataTestId: "workflow-component-edge",
      weight: edge.count,
      label: String(edge.count),
      labelX: 0.125 * sx + 0.375 * c1x + 0.375 * c2x + 0.125 * tx,
      labelY: 0.125 * sy + 0.375 * c1y + 0.375 * c2y + 0.125 * ty,
      sourceX: sx,
      sourceY: sy,
      targetX: tx,
      targetY: ty,
    });
  }

  return { nodes, edges, width, height };
}

export function buildStepScene(
  index: ViewerIndex,
  component: string,
  rows: WorkflowDagStep[],
  tintFor: (component: string) => string,
  options: {
    boundaries?: boolean;
    direction?: "horizontal" | "vertical";
  } = {},
): WorkflowDagScene {
  const visible = new Map(rows.map((row) => [row.key, row]));
  const vertical = options.direction === "vertical";
  const useBoundaries = (options.boundaries ?? true) && !vertical;
  const internal: Array<{ id: string; sourceKey: string; targetKey: string }> = [];
  const incoming = new Map<string, number>();
  const outgoing = new Map<string, number>();
  const leftTargets = new Map<string, Set<string>>();
  const rightSources = new Map<string, Set<string>>();

  for (const connection of index.connections) {
    const sourceKey = stepKey(connection.outputStepId);
    const targetKey = stepKey(connection.inputStepId);
    const sourceIn = visible.has(sourceKey);
    const targetIn = visible.has(targetKey);
    if (sourceIn && targetIn) {
      internal.push({ id: connection.id, sourceKey, targetKey });
      continue;
    }
    if (sourceIn) {
      if (!useBoundaries) continue;
      const targetComponent = connection.inputStepId[0];
      if (targetComponent === component) continue;
      outgoing.set(targetComponent, (outgoing.get(targetComponent) ?? 0) + 1);
      const sources = rightSources.get(targetComponent) ?? new Set<string>();
      sources.add(sourceKey);
      rightSources.set(targetComponent, sources);
    } else if (targetIn) {
      if (!useBoundaries) continue;
      const sourceComponent = connection.outputStepId[0];
      if (sourceComponent === component) continue;
      incoming.set(sourceComponent, (incoming.get(sourceComponent) ?? 0) + 1);
      const targets = leftTargets.get(sourceComponent) ?? new Set<string>();
      targets.add(targetKey);
      leftTargets.set(sourceComponent, targets);
    }
  }

  const count = rows.length;
  const leftEntries = [...incoming.entries()].sort(([a], [b]) => a.localeCompare(b));
  const rightEntries = [...outgoing.entries()].sort(([a], [b]) => a.localeCompare(b));
  const stepIds = rows.map((row) => row.key);
  const internalLinks = internal.map((edge) => ({
    source: edge.sourceKey,
    target: edge.targetKey,
  }));
  const layers = dependencyLayers(stepIds, internalLinks);
  const columns = layeredOrder(stepIds, internalLinks, layers);
  const maxLayerSize = columns.length
    ? Math.max(...columns.map((column) => column.length))
    : 0;
  // A dependency layer may contain hundreds of parallel steps. Keep the layer
  // order, but wrap a large layer into a block of sub-columns so the graph
  // stays compact. Within a block the flat order is row-major, so a step and
  // its neighbour share a row across layer blocks.
  const rowsPerBlock = Math.min(
    STEP_MAX_ROWS,
    Math.max(STEP_MIN_ROWS, Math.ceil(Math.sqrt(Math.max(count, 1)))),
  );
  const visibleRows = Math.min(rowsPerBlock, Math.max(1, maxLayerSize));
  const blocks = columns.map((column) => {
    const blockColumns = Math.max(1, Math.ceil(column.length / visibleRows));
    return {
      column,
      blockColumns,
      width:
        blockColumns * STEP_NODE_WIDTH +
        Math.max(0, blockColumns - 1) * STEP_GAP_X,
    };
  });
  const gridWidth =
    blocks.reduce((total, block) => total + block.width, 0) +
    Math.max(0, blocks.length - 1) * STEP_LAYER_GAP_X;
  const gridHeight =
    maxLayerSize === 0
      ? 0
      : visibleRows * STEP_NODE_HEIGHT +
        Math.max(0, visibleRows - 1) * STEP_GAP_Y;
  const leftWidth = leftEntries.length ? BOUNDARY_WIDTH : 0;
  const rightWidth = rightEntries.length ? BOUNDARY_WIDTH : 0;
  const gridX = STEP_MARGIN + (leftEntries.length ? leftWidth + 42 : 0);
  const gridY = STEP_MARGIN;
  const rightX = gridX + gridWidth + (rightEntries.length ? 42 : 0);
  let canvasWidth =
    gridX +
    gridWidth +
    (rightEntries.length ? 42 + rightWidth : 0) +
    STEP_MARGIN;

  const nodes: WorkflowDagNode[] = [];
  const nodeByKey = new Map<string, WorkflowDagNode>();
  const rowByKey = new Map(rows.map((row) => [row.key, row]));

  let canvasHeight = STEP_MARGIN + gridHeight;

  if (vertical) {
    // A subset reads top to bottom: one dependency layer per row, parallel
    // steps side by side, and only the steps themselves.
    const layerWidths = columns.map(
      (column) =>
        column.length * VERTICAL_STEP_WIDTH +
        Math.max(0, column.length - 1) * VERTICAL_STEP_GAP_X,
    );
    const maxWidth = Math.max(1, ...layerWidths);
    let cursorY = STEP_MARGIN;
    columns.forEach((column, layerIndex) => {
      let cursorX =
        STEP_MARGIN + (maxWidth - (layerWidths[layerIndex] ?? 0)) / 2;
      column.forEach((key) => {
        const row = rowByKey.get(key);
        if (!row) return;
        const node: WorkflowDagNode = {
          id: row.key,
          kind: "step",
          label: row.name,
          detail: row.kindLabel,
          meta: `${row.inputs} in · ${row.outputs} out`,
          tint: tintFor(row.component),
          x: cursorX,
          y: cursorY,
          width: VERTICAL_STEP_WIDTH,
          height: STEP_NODE_HEIGHT,
          headerHeight: STEP_HEADER_HEIGHT,
          socketY: STEP_NODE_HEIGHT / 2,
          dataTestId: "workflow-step-node",
          row,
          component: row.component,
          vertical: true,
        };
        nodes.push(node);
        nodeByKey.set(node.id, node);
        cursorX += VERTICAL_STEP_WIDTH + VERTICAL_STEP_GAP_X;
      });
      cursorY += STEP_NODE_HEIGHT + STEP_GAP_Y;
    });
    canvasWidth = maxWidth + STEP_MARGIN * 2;
    canvasHeight = cursorY - STEP_GAP_Y + STEP_MARGIN;
  } else {
    // One block per dependency layer. Parallel steps share the block and wrap
    // into sub-columns; rows align across blocks so a chain reads left to right.
    let cursorX = gridX;
    blocks.forEach(({ column, blockColumns }) => {
      column.forEach((key, index) => {
        const row = rowByKey.get(key);
        if (!row) return;
        const subColumn = Math.floor(index / visibleRows);
        const rowIndex = index % visibleRows;
        const node: WorkflowDagNode = {
          id: row.key,
          kind: "step",
          label: row.name,
          detail: row.kindLabel,
          meta: `${row.inputs} in · ${row.outputs} out`,
          tint: tintFor(row.component),
          x: cursorX + subColumn * (STEP_NODE_WIDTH + STEP_GAP_X),
          y: gridY + rowIndex * (STEP_NODE_HEIGHT + STEP_GAP_Y),
          width: STEP_NODE_WIDTH,
          height: STEP_NODE_HEIGHT,
          headerHeight: STEP_HEADER_HEIGHT,
          socketY: STEP_NODE_HEIGHT / 2,
          dataTestId: "workflow-step-node",
          row,
          component: row.component,
        };
        nodes.push(node);
        nodeByKey.set(node.id, node);
      });
      cursorX +=
        blockColumns * STEP_NODE_WIDTH +
        Math.max(0, blockColumns - 1) * STEP_GAP_X +
        STEP_LAYER_GAP_X;
    });
  }

  const stepCenterY = (keys: Iterable<string>): number => {
    const values = [...keys]
      .map((key) => nodeByKey.get(key))
      .filter((node): node is WorkflowDagNode => Boolean(node))
      .map((node) => node.y + node.height / 2);
    return values.length
      ? values.reduce((total, value) => total + value, 0) / values.length
      : gridY + gridHeight / 2;
  };

  const placeBoundaryStack = (
    entries: Array<[string, number]>,
    keys: Map<string, Set<string>>,
  ) => {
    let previousBottom = -Infinity;
    return entries
      .map(([name, links]) => ({
        name,
        links,
        desired: stepCenterY(keys.get(name) ?? []) - BOUNDARY_HEIGHT / 2,
      }))
      .sort((left, right) => left.desired - right.desired)
      .map((entry) => {
        const y = Math.max(
          STEP_MARGIN,
          entry.desired,
          previousBottom + 22,
        );
        previousBottom = y + BOUNDARY_HEIGHT;
        return { ...entry, y };
      });
  };

  const leftPlacements = placeBoundaryStack(leftEntries, leftTargets);
  const rightPlacements = placeBoundaryStack(rightEntries, rightSources);

  leftPlacements.forEach(({ name, links, y }) => {
    const node: WorkflowDagNode = {
      id: `boundary:in:${name}`,
      kind: "in",
      label: name,
      detail: `${links} link${links === 1 ? "" : "s"}`,
      meta: "incoming boundary",
      tint: tintFor(name),
      x: STEP_MARGIN,
      y,
      width: BOUNDARY_WIDTH,
      height: BOUNDARY_HEIGHT,
      headerHeight: STEP_HEADER_HEIGHT,
      socketY: BOUNDARY_HEIGHT / 2,
      dataTestId: "workflow-boundary-node",
      component: name,
    };
    nodes.push(node);
    nodeByKey.set(node.id, node);
  });

  rightPlacements.forEach(({ name, links, y }) => {
    const node: WorkflowDagNode = {
      id: `boundary:out:${name}`,
      kind: "out",
      label: name,
      detail: `${links} link${links === 1 ? "" : "s"}`,
      meta: "outgoing boundary",
      tint: tintFor(name),
      x: rightX,
      y,
      width: BOUNDARY_WIDTH,
      height: BOUNDARY_HEIGHT,
      headerHeight: STEP_HEADER_HEIGHT,
      socketY: BOUNDARY_HEIGHT / 2,
      dataTestId: "workflow-boundary-node",
      component: name,
    };
    nodes.push(node);
    nodeByKey.set(node.id, node);
  });

  canvasHeight =
    Math.max(
      canvasHeight,
      ...leftPlacements.map((entry) => entry.y + BOUNDARY_HEIGHT),
      ...rightPlacements.map((entry) => entry.y + BOUNDARY_HEIGHT),
    ) + (vertical ? 0 : STEP_MARGIN);

  const edges: WorkflowDagEdge[] = [];
  const pushEdge = (sourceKey: string, targetKey: string, id: string, boundary: boolean) => {
    const source = nodeByKey.get(sourceKey);
    const target = nodeByKey.get(targetKey);
    if (!source || !target) return;
    const sx = vertical ? source.x + source.width / 2 : source.x + source.width;
    const sy = vertical ? source.y + source.height : source.y + source.socketY;
    const tx = vertical ? target.x + target.width / 2 : target.x;
    const ty = vertical ? target.y : target.y + target.socketY;
    const dx = Math.max(48, Math.abs(tx - sx) * 0.5);
    const dy = Math.max(32, Math.abs(ty - sy) * 0.5);
    edges.push({
      id,
      source: sourceKey,
      target: targetKey,
      path: vertical
        ? `M ${sx} ${sy} C ${sx} ${sy + dy}, ${tx} ${ty - dy}, ${tx} ${ty}`
        : `M ${sx} ${sy} C ${sx + dx} ${sy}, ${tx - dx} ${ty}, ${tx} ${ty}`,
      dataTestId: "workflow-step-edge",
      boundary,
      sourceX: sx,
      sourceY: sy,
      targetX: tx,
      targetY: ty,
    });
  };

  for (const edge of internal) {
    pushEdge(edge.sourceKey, edge.targetKey, edge.id, false);
  }
  for (const connection of index.connections) {
    if (!useBoundaries) continue;
    const sourceKey = stepKey(connection.outputStepId);
    const targetKey = stepKey(connection.inputStepId);
    const sourceIn = visible.has(sourceKey);
    const targetIn = visible.has(targetKey);
    if (sourceIn && targetIn) continue;
    if (sourceIn && connection.inputStepId[0] !== component) {
      pushEdge(
        sourceKey,
        `boundary:out:${connection.inputStepId[0]}`,
        `boundary:${connection.id}`,
        true,
      );
    } else if (targetIn && connection.outputStepId[0] !== component) {
      pushEdge(
        `boundary:in:${connection.outputStepId[0]}`,
        targetKey,
        `boundary:${connection.id}`,
        true,
      );
    }
  }

  return {
    nodes,
    edges,
    width: canvasWidth,
    height: canvasHeight,
    stats: {
      stepCount: count,
      internalEdges: internal.length,
      boundaryCount: leftEntries.length + rightEntries.length,
    },
  };
}

function truncateLabel(value: string, max: number): string {
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
}

function stepDisplayName(value: string): string {
  const dot = value.indexOf(".");
  return dot >= 0 ? value.slice(dot + 1) : value;
}

/**
 * Collapse a step subset to its workflow components. Large subsets remain a
 * readable DAG: each node states how many of the involved steps it owns, and
 * each edge counts the step connections between two components.
 */
export function buildStepComponentScene(
  index: ViewerIndex,
  rows: WorkflowDagStep[],
): WorkflowDagScene {
  const visible = new Map(rows.map((row) => [row.key, row]));
  const counts = new Map<string, number>();
  for (const row of rows) {
    counts.set(row.component, (counts.get(row.component) ?? 0) + 1);
  }
  const edges = new Map<string, WorkflowDagComponentEdge>();
  for (const connection of index.connections) {
    const source = visible.get(stepKey(connection.outputStepId));
    const target = visible.get(stepKey(connection.inputStepId));
    if (!source || !target || source.component === target.component) continue;
    const id = `component:${source.component}:${target.component}`;
    const existing = edges.get(id);
    if (existing) existing.count += 1;
    else {
      edges.set(id, {
        id,
        source: source.component,
        target: target.component,
        count: 1,
      });
    }
  }
  return buildCompositorScene(
    {
      nodes: [...counts.entries()].map(([id, steps]) => ({ id, steps })),
      edges: [...edges.values()],
    },
  );
}

/**
 * One renderer for every workflow scene. Component nodes, step nodes and
 * boundary nodes share the same chrome; one selected id drives the same
 * incident-link highlight and dimming in both the component and step views.
 */
const DIM_NODE_OPACITY = 0.3;

export function WorkflowDagSceneView({
  scene,
  selectedId,
  activeIds,
  onSelect,
  onOpen,
  onContextMenu,
}: {
  scene: WorkflowDagScene;
  selectedId?: string;
  activeIds?: Set<string>;
  onSelect(node: WorkflowDagNode): void;
  onOpen?(node: WorkflowDagNode): void;
  onContextMenu?(
    node: WorkflowDagNode,
    event: ReactMouseEvent<SVGGElement>,
  ): void;
}) {
  const incident = useMemo(() => {
    if (!selectedId) return new Set<string>();
    return new Set(
      scene.edges
        .filter((edge) => edge.source === selectedId || edge.target === selectedId)
        .map((edge) => edge.id),
    );
  }, [scene.edges, selectedId]);

  const renderEdge = (edge: WorkflowDagEdge) => {
    const highlighted = incident.has(edge.id);
    const active =
      !activeIds ||
      (activeIds.has(edge.source) && activeIds.has(edge.target));
    const baseWidth = edge.boundary
      ? 0.7
      : edge.weight
        ? Math.min(2.6, 1 + Math.log2(edge.weight + 1) * 0.45)
        : 1;
    const opacity = highlighted
      ? 1
      : selectedId
        ? active
          ? 0.16
          : 0.05
        : active
          ? edge.boundary
            ? 0.32
            : 0.58
          : 0.1;
    return (
      <g
        key={edge.id}
        opacity={opacity}
        data-testid={edge.dataTestId}
        data-active={highlighted ? "true" : undefined}
        data-source={edge.source}
        data-target={edge.target}
        data-source-x={edge.sourceX}
        data-source-y={edge.sourceY}
        data-target-x={edge.targetX}
        data-target-y={edge.targetY}
      >
        <path
          d={edge.path}
          fill="none"
          stroke={highlighted ? theme.selection : theme.edge}
          strokeWidth={highlighted ? baseWidth + 0.7 : baseWidth}
          strokeLinecap="round"
        />
        {edge.label && edge.labelX !== undefined && edge.labelY !== undefined ? (
          <text
            x={edge.labelX}
            y={edge.labelY - 4}
            textAnchor="middle"
            fill={highlighted ? theme.selectionStrong : theme.faint}
            fontSize="var(--text-micro)"
            fontFamily="var(--font-mono)"
            stroke={theme.page}
            strokeWidth={3}
            paintOrder="stroke"
            pointerEvents="none"
          >
            {edge.label}
          </text>
        ) : null}
      </g>
    );
  };

  return (
    <>
      <g data-workflow-edges pointerEvents="none">
        {scene.edges.filter((edge) => !incident.has(edge.id)).map(renderEdge)}
      </g>
      <g data-workflow-nodes>
        {scene.nodes.map((node) => {
          const selected = node.id === selectedId;
          const active = !activeIds || activeIds.has(node.id);
          // Selection dims every other node in both the component and step
          // scenes; filters dim inactive nodes only when nothing is selected.
          const opacity = selected
            ? 1
            : selectedId || !active
              ? DIM_NODE_OPACITY
              : 1;
          const isStep = node.kind === "step";
          const isComponent = node.kind === "component";
          const title = isStep ? stepDisplayName(node.label) : node.label;
          const maxTitle = isComponent ? 30 : isStep ? 34 : 20;
          const detail = truncateLabel(node.detail, isComponent ? 30 : 36);
          return (
            <g
              key={node.id}
              transform={`translate(${node.x} ${node.y})`}
              className="cursor-pointer"
              opacity={opacity}
              style={{ transition: "opacity var(--motion-quick) var(--ease-instrument)" }}
              role="button"
              tabIndex={0}
              aria-pressed={selected}
              aria-label={`${isComponent ? "Component" : isStep ? "Step" : "Boundary"} ${node.label}, ${node.detail}`}
              onClick={(event) => {
                event.stopPropagation();
                onSelect(node);
              }}
              onDoubleClick={
                onOpen
                  ? (event) => {
                      event.stopPropagation();
                      onOpen(node);
                    }
                  : undefined
              }
              onContextMenu={
                onContextMenu
                  ? (event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      onContextMenu(node, event);
                    }
                  : undefined
              }
              onKeyDown={(event) => {
                if (event.key !== "Enter" && event.key !== " ") return;
                event.preventDefault();
                onSelect(node);
              }}
              data-testid={node.dataTestId}
              data-active={selected ? "true" : undefined}
              data-step-key={node.row ? node.id : undefined}
              data-component={node.component}
            >
              <title>{`${node.label} · ${node.detail}`}</title>
              <rect
                width={node.width}
                height={node.height}
                rx={6}
                fill={theme.panel}
                stroke={selected ? theme.selection : theme.lineStrong}
                strokeWidth={selected ? 1.8 : 1}
              />
              <path
                d={`M 0 6 Q 0 0 6 0 H ${node.width - 6} Q ${node.width} 0 ${node.width} 6 V ${node.headerHeight} H 0 Z`}
                fill={node.tint}
                fillOpacity={selected ? 0.62 : 0.34}
                stroke="none"
              />
              <text
                x={12}
                y={node.headerHeight - 8}
                fill={theme.text}
                fontSize={
                  isComponent ? "var(--text-body)" : "var(--text-caption)"
                }
                fontWeight={600}
                fontFamily="var(--font-mono)"
                pointerEvents="none"
              >
                {truncateLabel(title, maxTitle)}
              </text>
              <text
                x={12}
                y={node.headerHeight + 24}
                fill={theme.text}
                fontSize={
                  isComponent ? "var(--text-caption)" : "var(--text-micro)"
                }
                fontFamily="var(--font-mono)"
                pointerEvents="none"
              >
                {detail}
              </text>
              <text
                x={12}
                y={node.headerHeight + 46}
                fill={theme.faint}
                fontSize="var(--text-micro)"
                fontFamily="var(--font-mono)"
                pointerEvents="none"
              >
                {node.meta}
              </text>
              {node.note ? (
                <text
                  x={12}
                  y={node.headerHeight + 68}
                  fill={theme.faint}
                  fontSize="var(--text-micro)"
                  fontFamily="var(--font-mono)"
                  pointerEvents="none"
                >
                  {node.note}
                </text>
              ) : null}
              {node.vertical ? (
                <>
                  <circle
                    cx={node.width / 2}
                    cy={0}
                    r={5}
                    fill={theme.raised}
                    stroke={selected ? theme.selection : node.tint}
                    strokeWidth={1.4}
                    pointerEvents="none"
                  />
                  <circle
                    cx={node.width / 2}
                    cy={node.height}
                    r={5}
                    fill={theme.raised}
                    stroke={selected ? theme.selection : node.tint}
                    strokeWidth={1.4}
                    pointerEvents="none"
                  />
                </>
              ) : (
                <>
                  <circle
                    cx={0}
                    cy={node.socketY}
                    r={5}
                    fill={theme.raised}
                    stroke={selected ? theme.selection : node.tint}
                    strokeWidth={1.4}
                    pointerEvents="none"
                  />
                  <circle
                    cx={node.width}
                    cy={node.socketY}
                    r={5}
                    fill={theme.raised}
                    stroke={selected ? theme.selection : node.tint}
                    strokeWidth={1.4}
                    pointerEvents="none"
                  />
                </>
              )}
            </g>
          );
        })}
      </g>
      {incident.size ? (
        <g data-workflow-active-edges pointerEvents="none">
          {scene.edges.filter((edge) => incident.has(edge.id)).map(renderEdge)}
        </g>
      ) : null}
    </>
  );
}

/**
 * The one workflow DAG primitive: a pan/zoom canvas, one selected node and one
 * open action. The Workflow document composes its own toolbar over the same
 * renderer; a detail card can mount this self-contained view.
 */
export function WorkflowDag({
  scene,
  selectedId,
  activeIds,
  onSelect,
  onOpen,
  onContextMenu,
  onBackgroundClick,
  className,
  testId,
  ariaLabel,
  minFitScale,
  fitKey,
}: {
  scene: WorkflowDagScene;
  selectedId?: string;
  activeIds?: Set<string>;
  onSelect?(node: WorkflowDagNode): void;
  onOpen?(node: WorkflowDagNode): void;
  onContextMenu?(
    node: WorkflowDagNode,
    event: ReactMouseEvent<SVGGElement>,
  ): void;
  onBackgroundClick?(): void;
  className?: string;
  testId?: string;
  ariaLabel?: string;
  minFitScale?: number;
  fitKey?: string;
}) {
  return (
    <GraphCanvas
      width={scene.width}
      height={scene.height}
      className={className}
      testId={testId}
      ariaLabel={ariaLabel}
      onBackgroundClick={onBackgroundClick}
      minFitScale={minFitScale}
      fitKey={fitKey}
    >
      <WorkflowDagSceneView
        scene={scene}
        selectedId={selectedId}
        activeIds={activeIds}
        onSelect={(node) => onSelect?.(node)}
        onOpen={onOpen}
        onContextMenu={onContextMenu}
      />
    </GraphCanvas>
  );
}
