"use client";

import { useMemo, type MouseEvent as ReactMouseEvent } from "react";

import type { ViewerIndex } from "@/lib/types";
import { stepKey } from "@/lib/indexes";
import {
  buildWorkflowComponentMap,
  type WorkflowStepRow,
} from "@/workflow/model/WorkflowViewModel";
import { groupPalette, theme } from "@/shared/ui/theme";

const STEP_NODE_WIDTH = 220;
const STEP_NODE_HEIGHT = 72;
const STEP_HEADER_HEIGHT = 22;
const STEP_GAP_X = 46;
const STEP_GAP_Y = 24;
const STEP_MARGIN = 36;
const BOUNDARY_WIDTH = 150;
const BOUNDARY_HEIGHT = 72;

type WorkflowGraphNodeKind = "component" | "step" | "in" | "out";

/**
 * One node in the workflow scene. A component, a step and a boundary node are
 * the same value; only the facts and the size differ.
 */
export interface WorkflowGraphNode {
  id: string;
  kind: WorkflowGraphNodeKind;
  label: string;
  detail: string;
  meta: string;
  note?: string;
  tint: string;
  x: number;
  y: number;
  width: number;
  height: number;
  headerHeight: number;
  socketY: number;
  dataTestId: string;
  row?: WorkflowStepRow;
  component?: string;
}

/** One link in the workflow scene; the same renderer draws every link kind. */
export interface WorkflowGraphEdge {
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

interface WorkflowGraphStats {
  stepCount: number;
  internalEdges: number;
  boundaryCount: number;
}

export interface WorkflowGraphScene {
  nodes: WorkflowGraphNode[];
  edges: WorkflowGraphEdge[];
  width: number;
  height: number;
  stats?: WorkflowGraphStats;
}

const NODE_WIDTH = 208;
const NODE_HEIGHT = 140;
const HEADER_HEIGHT = 28;
const COLUMN_GAP = 68;
const ROW_GAP = 56;
const MARGIN = 36;
const SOCKET_Y = 50;

function componentLayers(
  ids: string[],
  edges: ReturnType<typeof buildWorkflowComponentMap>["edges"],
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

export function buildCompositorScene(
  map: ReturnType<typeof buildWorkflowComponentMap>,
): WorkflowGraphScene {
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
  const width =
    MARGIN * 2 +
    layerIds.length * NODE_WIDTH +
    Math.max(0, layerIds.length - 1) * COLUMN_GAP;
  const height =
    MARGIN * 2 +
    maxRows * NODE_HEIGHT +
    Math.max(0, maxRows - 1) * ROW_GAP;
  const bodyHeight = maxRows * NODE_HEIGHT + Math.max(0, maxRows - 1) * ROW_GAP;

  const placed = new Map<
    string,
    {
      node: ReturnType<typeof buildWorkflowComponentMap>["nodes"][number];
      x: number;
      y: number;
      color: string;
      internal: number;
    }
  >();
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

  const nodes: WorkflowGraphNode[] = [...placed.values()].map(
    ({ node, x, y, color, internal: inner }) => ({
      id: node.id,
      kind: "component",
      label: node.id,
      detail: `${node.steps} steps · ${node.kinds} kind${node.kinds === 1 ? "" : "s"}`,
      meta: `${node.incoming} in · ${node.outgoing} out`,
      note: inner ? `${inner} internal` : undefined,
      tint: color,
      x,
      y,
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
      headerHeight: HEADER_HEIGHT,
      socketY: SOCKET_Y,
      dataTestId: "workflow-component-node",
      component: node.id,
    }),
  );

  const edges: WorkflowGraphEdge[] = [];
  for (const edge of map.edges) {
    if (edge.source === edge.target) continue;
    const source = placed.get(edge.source);
    const target = placed.get(edge.target);
    if (!source || !target) continue;
    const sx = source.x + NODE_WIDTH;
    const sy = source.y + SOCKET_Y;
    const tx = target.x;
    const ty = target.y + SOCKET_Y;
    const forward = tx >= sx;
    const dx = forward
      ? Math.max(56, (tx - sx) * 0.48)
      : 96;
    const c1x = sx + dx;
    const c1y = sy;
    const c2x = tx - dx;
    const c2y = ty;
    edges.push({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      path: `M ${sx} ${sy} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${tx} ${ty}`,
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
  rows: WorkflowStepRow[],
  tintFor: (component: string) => string,
): WorkflowGraphScene {
  const visible = new Map(rows.map((row) => [row.key, row]));
  const internal: Array<{ id: string; sourceKey: string; targetKey: string }> = [];
  const incoming = new Map<string, number>();
  const outgoing = new Map<string, number>();

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
      const targetComponent = connection.inputStepId[0];
      if (targetComponent === component) continue;
      outgoing.set(targetComponent, (outgoing.get(targetComponent) ?? 0) + 1);
    } else if (targetIn) {
      const sourceComponent = connection.outputStepId[0];
      if (sourceComponent === component) continue;
      incoming.set(sourceComponent, (incoming.get(sourceComponent) ?? 0) + 1);
    }
  }

  const count = rows.length;
  const leftEntries = [...incoming.entries()].sort(([a], [b]) => a.localeCompare(b));
  const rightEntries = [...outgoing.entries()].sort(([a], [b]) => a.localeCompare(b));
  const columns = Math.max(
    3,
    Math.min(
      18,
      Math.ceil(Math.sqrt((Math.max(count, 1) * 1.7) / 3.8)),
    ),
  );
  const rowsPerColumn = Math.max(1, Math.ceil(count / columns));
  const gridWidth =
    columns * STEP_NODE_WIDTH + Math.max(0, columns - 1) * STEP_GAP_X;
  const gridHeight =
    rowsPerColumn * STEP_NODE_HEIGHT +
    Math.max(0, rowsPerColumn - 1) * STEP_GAP_Y;
  const leftWidth = leftEntries.length ? BOUNDARY_WIDTH : 0;
  const rightWidth = rightEntries.length ? BOUNDARY_WIDTH : 0;
  const gridX = STEP_MARGIN + (leftEntries.length ? leftWidth + 42 : 0);
  const gridY = STEP_MARGIN;
  const rightX = gridX + gridWidth + (rightEntries.length ? 42 : 0);
  const leftStackHeight =
    leftEntries.length * BOUNDARY_HEIGHT +
    Math.max(0, leftEntries.length - 1) * 22;
  const rightStackHeight =
    rightEntries.length * BOUNDARY_HEIGHT +
    Math.max(0, rightEntries.length - 1) * 22;
  const canvasHeight =
    STEP_MARGIN * 2 + Math.max(gridHeight, leftStackHeight, rightStackHeight);
  const canvasWidth =
    gridX +
    gridWidth +
    (rightEntries.length ? 42 + rightWidth : 0) +
    STEP_MARGIN;

  const nodes: WorkflowGraphNode[] = [];
  const nodeByKey = new Map<string, WorkflowGraphNode>();

  rows.forEach((row, rowIndex) => {
    // Columns fill top-to-bottom, then advance to the next column. The flow
    // never wraps back to a new row.
    const column = Math.floor(rowIndex / rowsPerColumn);
    const line = rowIndex % rowsPerColumn;
    const node: WorkflowGraphNode = {
      id: row.key,
      kind: "step",
      label: row.name,
      detail: row.kindLabel,
      meta: `${row.inputs} in · ${row.outputs} out`,
      tint: tintFor(row.component),
      x: gridX + column * (STEP_NODE_WIDTH + STEP_GAP_X),
      y: gridY + line * (STEP_NODE_HEIGHT + STEP_GAP_Y),
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

  const leftStartY =
    STEP_MARGIN + Math.max(0, (gridHeight - leftStackHeight) / 2);
  leftEntries.forEach(([source, links], entryIndex) => {
    const node: WorkflowGraphNode = {
      id: `boundary:in:${source}`,
      kind: "in",
      label: source,
      detail: `${links} link${links === 1 ? "" : "s"}`,
      meta: "incoming boundary",
      tint: tintFor(source),
      x: STEP_MARGIN,
      y: leftStartY + entryIndex * (BOUNDARY_HEIGHT + 22),
      width: BOUNDARY_WIDTH,
      height: BOUNDARY_HEIGHT,
      headerHeight: STEP_HEADER_HEIGHT,
      socketY: BOUNDARY_HEIGHT / 2,
      dataTestId: "workflow-boundary-node",
      component: source,
    };
    nodes.push(node);
    nodeByKey.set(node.id, node);
  });

  const rightStartY =
    STEP_MARGIN + Math.max(0, (gridHeight - rightStackHeight) / 2);
  rightEntries.forEach(([target, links], entryIndex) => {
    const node: WorkflowGraphNode = {
      id: `boundary:out:${target}`,
      kind: "out",
      label: target,
      detail: `${links} link${links === 1 ? "" : "s"}`,
      meta: "outgoing boundary",
      tint: tintFor(target),
      x: rightX,
      y: rightStartY + entryIndex * (BOUNDARY_HEIGHT + 22),
      width: BOUNDARY_WIDTH,
      height: BOUNDARY_HEIGHT,
      headerHeight: STEP_HEADER_HEIGHT,
      socketY: BOUNDARY_HEIGHT / 2,
      dataTestId: "workflow-boundary-node",
      component: target,
    };
    nodes.push(node);
    nodeByKey.set(node.id, node);
  });

  const edges: WorkflowGraphEdge[] = [];
  const pushEdge = (sourceKey: string, targetKey: string, id: string, boundary: boolean) => {
    const source = nodeByKey.get(sourceKey);
    const target = nodeByKey.get(targetKey);
    if (!source || !target) return;
    const sx = source.x + source.width;
    const sy = source.y + source.socketY;
    const tx = target.x;
    const ty = target.y + target.socketY;
    const dx = Math.max(48, Math.abs(tx - sx) * 0.5);
    edges.push({
      id,
      source: sourceKey,
      target: targetKey,
      path: `M ${sx} ${sy} C ${sx + dx} ${sy}, ${tx - dx} ${ty}, ${tx} ${ty}`,
      dataTestId: "workflow-step-edge",
      boundary,
    });
  };

  for (const edge of internal) {
    pushEdge(edge.sourceKey, edge.targetKey, edge.id, false);
  }
  for (const connection of index.connections) {
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
 * One renderer for every workflow scene. Component nodes, step nodes and
 * boundary nodes share the same chrome; one selected id drives the same
 * incident-link highlight and dimming in both the component and step views.
 */
const DIM_NODE_OPACITY = 0.3;

export function WorkflowGraphSceneView({
  scene,
  selectedId,
  activeIds,
  onSelect,
  onOpen,
  onContextMenu,
}: {
  scene: WorkflowGraphScene;
  selectedId?: string;
  activeIds?: Set<string>;
  onSelect(node: WorkflowGraphNode): void;
  onOpen?(node: WorkflowGraphNode): void;
  onContextMenu?(
    node: WorkflowGraphNode,
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

  const renderEdge = (edge: WorkflowGraphEdge) => {
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
            fontSize={9.5}
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
              style={{ transition: "opacity 140ms var(--ease-instrument)" }}
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
                fontSize={isComponent ? 11.5 : 9.5}
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
                fontSize={isComponent ? 10.5 : 8.5}
                fontFamily="var(--font-mono)"
                pointerEvents="none"
              >
                {detail}
              </text>
              <text
                x={12}
                y={node.headerHeight + 46}
                fill={theme.faint}
                fontSize={isComponent ? 9.5 : 8}
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
                  fontSize={isComponent ? 9.5 : 8}
                  fontFamily="var(--font-mono)"
                  pointerEvents="none"
                >
                  {node.note}
                </text>
              ) : null}
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
