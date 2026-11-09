"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import dagre from "@dagrejs/dagre";
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  getViewportForBounds,
  type Edge,
  type Node,
  type ReactFlowInstance,
} from "@xyflow/react";
import { FlowInitializer } from "@/shared/graph/FlowInitializer";
import { horizontalHandles, measuredNode } from "@/shared/graph/geometry";
import {
  WorkflowGroupFrameNode,
  WorkflowGroupNode,
  WorkflowStepNode,
  type WorkflowTraceState,
} from "@/diagnosis/execution/view/ExecutionNodes";
import { TraceBanner } from "@/diagnosis/execution/view/TraceBanner";
import { severityColor, theme } from "@/shared/ui/theme";
import type {
  ArtifactSocket,
  WorkflowStepDetailData,
} from "@/diagnosis/execution/view/StepDetailPopover";
import type {
  ExecutionGroupModel,
  ExecutionModel,
  ExecutionStepModel,
} from "@/diagnosis/execution/model/ExecutionModel";
import type { StepId } from "@/lib/types";

export interface ExecutionGraphViewProps {
  model: ExecutionModel;
  /**
   * Optional framing request from the panel header. The view still owns the
   * React Flow instance, viewport, zoom and hover state.
   */
  viewport?: { fitSignal?: number; fitMode?: "fit" | "read" };
}

type GroupKey = string;

const NODE_WIDTH = 232;
const NODE_HEIGHT = 112;
const GROUP_WIDTH = 224;
const GROUP_HEIGHT = 64;
const FRAME_PAD = 14;
const FRAME_HEADER = 26;
const MIN_ZOOM = 0.15;
const GROUP_MAX_ZOOM = 1;
const GROUP_MIN_READABLE_ZOOM = 0.7;
const OVERVIEW_MAX_ZOOM = 1;
const READABLE_ZOOM = 0.9;
const OPENING_PADDING = 16;

/** Expanded-group shelf spacing and a safety-net fallback only. */
const SHELF_GAP = 24;
const FALLBACK_COLUMNS = 4;

/** An expanded group wraps ranks by column, then shelves whole groups. */
const STEP_MAX_PER_COLUMN = 10;
const STEP_COLUMN_GAP = 20;
const STEP_ROW_GAP = 14;
const GROUP_SHELF_WIDTH = 1600;

function flowId(prefix: string, id: readonly string[]): string {
  return `${prefix}-${id.map((part) => part.replace(/[^a-zA-Z0-9_-]/g, "_")).join("-")}`;
}

/**
 * Lay out the collapsed composition graph. Group cards stay one rank apart in
 * the order their step connections imply; the overview may be wider than the
 * viewport, which is correct — do not fold it into a grid.
 */
function layoutGroupGraph(
  nodes: readonly Node[],
  edges: readonly Edge[],
): Node[] {
  if (!nodes.length) return [];

  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({
    rankdir: "LR",
    nodesep: 32,
    ranksep: 96,
    marginx: 32,
    marginy: 32,
  });

  const ids = new Set(nodes.map((node) => node.id));
  for (const node of nodes) {
    graph.setNode(node.id, { width: GROUP_WIDTH, height: GROUP_HEIGHT });
  }
  for (const edge of edges) {
    if (ids.has(edge.source) && ids.has(edge.target)) {
      graph.setEdge(edge.source, edge.target);
    }
  }
  dagre.layout(graph);

  return nodes.map((node) => {
    const positioned = graph.node(node.id);
    return {
      ...node,
      position: {
        x: positioned.x - GROUP_WIDTH / 2,
        y: positioned.y - GROUP_HEIGHT / 2,
      },
    };
  });
}

function firstGroupNode(nodes: readonly Node[]): Node | undefined {
  return nodes
    .filter((node) => node.type === "workflowGroup")
    .reduce<Node | undefined>((best, node) => {
      if (!best) return node;
      if (node.position.x < best.position.x) return node;
      if (
        node.position.x === best.position.x &&
        node.position.y < best.position.y
      ) {
        return node;
      }
      return best;
    }, undefined);
}

function leftAnchoredGroupViewport(
  node: Node,
  width: number,
  height: number,
  zoom: number,
  padding: number,
): { x: number; y: number; zoom: number } {
  const nodeHeight = node.height ?? node.measured?.height ?? GROUP_HEIGHT;
  return {
    x: padding - node.position.x * zoom,
    y: height / 2 - (node.position.y + nodeHeight / 2) * zoom,
    zoom,
  };
}

interface StepBlockLayout {
  positions: Map<string, { x: number; y: number }>;
  width: number;
  height: number;
}

/**
 * Lay out one expanded group as a wide, shallow block.
 *
 * Dagre still decides the rank order, but a rank is split into columns of at
 * most `STEP_MAX_PER_COLUMN` nodes. A source group with sixty independent
 * steps therefore becomes six columns of ten rather than one sixty-node column.
 */
function layoutStepBlock(
  nodes: readonly Node[],
  edges: readonly Edge[],
): StepBlockLayout {
  if (!nodes.length) {
    return { positions: new Map(), width: 0, height: 0 };
  }

  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({
    rankdir: "LR",
    nodesep: STEP_ROW_GAP,
    ranksep: STEP_COLUMN_GAP,
    marginx: 0,
    marginy: 0,
  });

  const ids = new Set(nodes.map((node) => node.id));
  for (const node of nodes) {
    graph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }
  for (const edge of edges) {
    if (ids.has(edge.source) && ids.has(edge.target)) {
      graph.setEdge(edge.source, edge.target);
    }
  }
  dagre.layout(graph);

  const byRank = new Map<number, Array<{ id: string; y: number }>>();
  for (const node of nodes) {
    const positioned = graph.node(node.id);
    const rank = Math.round(positioned.x);
    const rankNodes = byRank.get(rank) ?? [];
    rankNodes.push({ id: node.id, y: positioned.y });
    byRank.set(rank, rankNodes);
  }

  const ranks = [...byRank.entries()]
    .sort(([left], [right]) => left - right)
    .map(([, rankNodes]) =>
      rankNodes.sort(
        (left, right) => left.y - right.y || left.id.localeCompare(right.id),
      ),
    );

  const positions = new Map<string, { x: number; y: number }>();
  let column = 0;
  let height = 0;

  for (const rank of ranks) {
    for (let start = 0; start < rank.length; start += STEP_MAX_PER_COLUMN) {
      const chunk = rank.slice(start, start + STEP_MAX_PER_COLUMN);
      chunk.forEach((entry, row) => {
        positions.set(entry.id, {
          x: column * (NODE_WIDTH + STEP_COLUMN_GAP),
          y: row * (NODE_HEIGHT + STEP_ROW_GAP),
        });
      });
      height = Math.max(
        height,
        chunk.length * NODE_HEIGHT + (chunk.length - 1) * STEP_ROW_GAP,
      );
      column += 1;
    }
  }

  return {
    positions,
    width: column * NODE_WIDTH + Math.max(0, column - 1) * STEP_COLUMN_GAP,
    height,
  };
}

function detailData(step: ExecutionStepModel): WorkflowStepDetailData {
  return {
    stepId: step.detail.stepId,
    ...(step.detail.componentVersion
      ? { componentVersion: step.detail.componentVersion }
      : {}),
    runtimeFields: step.detail.runtimeFields,
    instructionKind: step.detail.instructionKind,
    producerCount: step.detail.producerCount,
    consumerCount: step.detail.consumerCount,
    artifactTypes: step.detail.artifactTypes,
    inputSockets: step.detail.inputSockets as ArtifactSocket[],
    outputSockets: step.detail.outputSockets as ArtifactSocket[],
    findings: step.detail.findings,
    onReview: step.commands.review,
    onTrace: step.commands.trace,
  };
}

/**
 * React Flow binding for the execution model.
 *
 * The model owns grouping, collapse, trace and commands. This view owns the
 * React Flow node/edge layout, the viewport and hover state.
 */
export function ExecutionGraphView({
  model,
  viewport,
}: ExecutionGraphViewProps) {
  const fitMode = viewport?.fitMode ?? "fit";
  const fitSignal = viewport?.fitSignal ?? 0;
  const graph = model.graph;
  const groups = graph.groups;
  const [hoveredEdgeId, setHoveredEdgeId] = useState<string | undefined>();

  const requestedCollapsed = useMemo(
    () =>
      new Set(
        groups
          .filter((group) => group.requestedCollapsed)
          .map((group) => group.key),
      ),
    [groups],
  );

  const { nodes, edges } = useMemo(() => {
    const visibleByStep = new Map<string, string>();
    const visibleNodes: Node[] = [];
    const frameGroups: Array<{
      key: GroupKey;
      label: string;
      count: number;
      auditCount: number;
      auditSeverity?: ExecutionGroupModel["audit"]["severity"];
      focused: boolean;
      lockedOpen: boolean;
      traceState?: WorkflowTraceState;
      stepIds: string[];
    }> = [];

    for (const group of groups) {
      if (group.collapsed) {
        const id = flowId("group", [group.key]);
        visibleNodes.push({
          id,
          type: "workflowGroup",
          position: { x: 0, y: 0 },
          data: {
            key: group.key,
            label: group.label,
            count: group.count,
            collapsed: true,
            onToggle: group.commands.toggle,
            auditCount: group.audit.count,
            auditSeverity: group.audit.severity,
            traceState: group.traceState,
          },
          width: GROUP_WIDTH,
          height: GROUP_HEIGHT,
          measured: measuredNode(GROUP_WIDTH, GROUP_HEIGHT),
          handles: horizontalHandles(GROUP_WIDTH, GROUP_HEIGHT),
          draggable: false,
        });
        for (const step of group.steps) visibleByStep.set(step.key, id);
        continue;
      }

      const stepIds: string[] = [];
      for (const step of group.steps) {
        const id = flowId("step", step.id);
        visibleByStep.set(step.key, id);
        stepIds.push(id);

        visibleNodes.push({
          id,
          type: "workflowStep",
          position: { x: 0, y: 0 },
          data: {
            label: step.label,
            component: step.component,
            emitter: step.emitter,
            artifacts: step.artifacts,
            stepId: step.id,
            selected: step.selected,
            subjectMatched: step.subjectMatched,
            inputSockets: step.inputSockets,
            outputSockets: step.outputSockets,
            auditCount: step.audit.count,
            auditSeverity: step.audit.severity,
            detail: detailData(step),
            traceState: step.traceState,
            onSelect: (selectedId: StepId) => model.commands.selectStep(selectedId),
          },
          width: NODE_WIDTH,
          height: NODE_HEIGHT,
          measured: measuredNode(NODE_WIDTH, NODE_HEIGHT),
          handles: horizontalHandles(NODE_WIDTH, NODE_HEIGHT),
          draggable: false,
        });
      }

      frameGroups.push({
        key: group.key,
        label: group.label,
        count: group.count,
        auditCount: group.audit.count,
        auditSeverity: group.audit.severity,
        focused: group.focused,
        lockedOpen: group.lockedOpen,
        traceState: group.traceState,
        stepIds,
      });
    }

    const edgeMap = new Map<string, Edge>();
    for (const connection of graph.connections) {
      const source = visibleByStep.get(connection.sourceKey);
      const target = visibleByStep.get(connection.targetKey);
      if (!source || !target || source === target) continue;
      const id = flowId("edge", [source, target]);
      if (edgeMap.has(id)) continue;

      const stroke = connection.active ? theme.selection : theme.edge;

      edgeMap.set(id, {
        id,
        source,
        target,
        type: "default",
        style: {
          stroke,
          strokeWidth: connection.active ? 1.6 : 1.3,
          opacity: connection.dimmed ? 0.06 : connection.active ? 0.95 : 0.8,
        },
      });
    }

    const visibleById = new Map(
      visibleNodes.map((node) => [node.id, node] as const),
    );
    const positionedById = new Map<string, Node>();
    const frameNodes: Node[] = [];

    if (frameGroups.length === 0) {
      // Every group is collapsed. The edge map has already collapsed each step
      // connection to its group ids, so it is the deduplicated ordered group
      // graph. Dagre gives the composition its natural left-to-right ranks.
      const collapsedNodes = groups
        .map((group) => visibleById.get(flowId("group", [group.key])))
        .filter((node): node is Node => Boolean(node));
      for (const node of layoutGroupGraph(
        collapsedNodes,
        [...edgeMap.values()],
      )) {
        positionedById.set(node.id, node);
      }
    } else {
      const frameByKey = new Map(
        frameGroups.map((frame) => [frame.key, frame] as const),
      );
      let cursorX = 0;
      let cursorY = 0;
      let rowHeight = 0;

      for (const group of groups) {
        const frame = frameByKey.get(group.key);
        if (!frame) {
          const node = visibleById.get(flowId("group", [group.key]));
          if (!node) continue;
          if (cursorX > 0 && cursorX + GROUP_WIDTH > GROUP_SHELF_WIDTH) {
            cursorX = 0;
            cursorY += rowHeight + SHELF_GAP;
            rowHeight = 0;
          }
          positionedById.set(node.id, {
            ...node,
            position: { x: cursorX, y: cursorY },
          });
          cursorX += GROUP_WIDTH + SHELF_GAP;
          rowHeight = Math.max(rowHeight, GROUP_HEIGHT);
          continue;
        }

        const stepNodes = frame.stepIds
          .map((id) => visibleById.get(id))
          .filter((node): node is Node => Boolean(node));
        if (!stepNodes.length) continue;

        const block = layoutStepBlock(stepNodes, [...edgeMap.values()]);
        const width = block.width + FRAME_PAD * 2;
        const height = block.height + FRAME_PAD * 2 + FRAME_HEADER;

        if (cursorX > 0 && cursorX + width > GROUP_SHELF_WIDTH) {
          cursorX = 0;
          cursorY += rowHeight + SHELF_GAP;
          rowHeight = 0;
        }

        for (const node of stepNodes) {
          const local = block.positions.get(node.id);
          if (!local) continue;
          positionedById.set(node.id, {
            ...node,
            position: {
              x: cursorX + FRAME_PAD + local.x,
              y: cursorY + FRAME_HEADER + FRAME_PAD + local.y,
            },
          });
        }

        frameNodes.push({
          id: flowId("frame", [frame.key]),
          type: "workflowGroupFrame",
          position: { x: cursorX, y: cursorY },
          data: {
            key: frame.key,
            label: frame.label,
            count: frame.count,
            auditCount: frame.auditCount,
            auditSeverity: frame.auditSeverity,
            focused: frame.focused,
            lockedOpen: frame.lockedOpen,
            onToggle: group.commands.toggle,
            traceState: frame.traceState,
          },
          width,
          height,
          measured: measuredNode(width, height),
          draggable: false,
          selectable: false,
          focusable: false,
        });

        cursorX += width + SHELF_GAP;
        rowHeight = Math.max(rowHeight, height);
      }

      // Safety net: never leave a visible node at the default origin.
      let fallbackIndex = 0;
      for (const node of visibleNodes) {
        if (positionedById.has(node.id)) continue;
        const column = fallbackIndex % FALLBACK_COLUMNS;
        const row = Math.floor(fallbackIndex / FALLBACK_COLUMNS);
        positionedById.set(node.id, {
          ...node,
          position: {
            x: column * (NODE_WIDTH + SHELF_GAP),
            y:
              cursorY +
              rowHeight +
              SHELF_GAP +
              row * (NODE_HEIGHT + SHELF_GAP),
          },
        });
        fallbackIndex += 1;
      }
    }

    return {
      nodes: [
        ...frameNodes,
        ...visibleNodes.map((node) => positionedById.get(node.id) ?? node),
      ],
      edges: [...edgeMap.values()],
    };
  }, [groups, graph.connections, model.commands]);

  const flowRef = useRef<ReactFlowInstance | null>(null);
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const nodesRef = useRef(nodes);
  nodesRef.current = nodes;
  const previousCollapsedRef = useRef<Set<string> | null>(null);
  const previousModeRef = useRef(graph.grouping);
  const lastFitSignalRef = useRef(fitSignal);

  useEffect(() => {
    const currentCollapsed = new Set(requestedCollapsed);
    const previousCollapsed = previousCollapsedRef.current;
    const modeChanged = previousModeRef.current !== graph.grouping;
    previousModeRef.current = graph.grouping;

    if (!previousCollapsed) {
      previousCollapsedRef.current = currentCollapsed;
      return;
    }

    previousCollapsedRef.current = currentCollapsed;

    const newlyExpanded = [...previousCollapsed].filter(
      (key) => !currentCollapsed.has(key),
    );

    let target: GroupKey | "overview" | undefined;
    if (modeChanged) {
      target = "overview";
    } else if (newlyExpanded.length === 1) {
      target = newlyExpanded[0];
    } else if (
      newlyExpanded.length > 1 ||
      currentCollapsed.size > previousCollapsed.size
    ) {
      target = "overview";
    }

    if (!target) return;

    const groupKey = target === "overview" ? undefined : target;
    let rafId: number | null = null;
    let timerId: number | null = null;
    let fitted = false;

    const cancelScheduledFit = () => {
      if (rafId !== null) cancelAnimationFrame(rafId);
      if (timerId !== null) window.clearTimeout(timerId);
      rafId = null;
      timerId = null;
    };

    const runFit = () => {
      if (fitted) return;
      const instance = flowRef.current;
      const canvas = canvasRef.current;
      if (!instance || !canvas) return;

      const { width, height } = canvas.getBoundingClientRect();
      if (width < 1 || height < 1) return;

      const visibleNodes = nodesRef.current;

      if (!groupKey && graph.allCollapsed) {
        const first = firstGroupNode(visibleNodes);
        if (first) {
          void instance.setViewport(
            leftAnchoredGroupViewport(
              first,
              width,
              height,
              READABLE_ZOOM,
              OPENING_PADDING,
            ),
            { duration: 200 },
          );
          fitted = true;
          return;
        }
      }

      const frameId = groupKey ? flowId("frame", [groupKey]) : undefined;
      const frame = frameId
        ? visibleNodes.find((node) => node.id === frameId)
        : undefined;

      let bounds:
        | { x: number; y: number; width: number; height: number }
        | undefined;
      if (frame) {
        const frameWidth = frame.width ?? frame.measured?.width;
        const frameHeight = frame.height ?? frame.measured?.height;
        if (frameWidth && frameHeight) {
          bounds = {
            x: frame.position.x,
            y: frame.position.y,
            width: frameWidth,
            height: frameHeight,
          };
        }
      }

      if (!bounds) {
        const rects = visibleNodes
          .filter((node) =>
            groupKey
              ? node.type === "workflowGroupFrame"
              : node.type === "workflowGroup" ||
                node.type === "workflowGroupFrame",
          )
          .map((node) => {
            const nodeWidth = node.width ?? node.measured?.width;
            const nodeHeight = node.height ?? node.measured?.height;
            return nodeWidth && nodeHeight
              ? {
                  x: node.position.x,
                  y: node.position.y,
                  width: nodeWidth,
                  height: nodeHeight,
                }
              : undefined;
          })
          .filter(
            (
              rect,
            ): rect is { x: number; y: number; width: number; height: number } =>
              Boolean(rect),
          );

        if (rects.length) {
          const minX = Math.min(...rects.map((rect) => rect.x));
          const minY = Math.min(...rects.map((rect) => rect.y));
          const maxX = Math.max(...rects.map((rect) => rect.x + rect.width));
          const maxY = Math.max(...rects.map((rect) => rect.y + rect.height));
          bounds = {
            x: minX,
            y: minY,
            width: maxX - minX,
            height: maxY - minY,
          };
        }
      }

      if (!bounds) {
        void instance.fitView({
          padding: groupKey ? 0.12 : 0.16,
          maxZoom: groupKey ? GROUP_MAX_ZOOM : OVERVIEW_MAX_ZOOM,
          duration: 200,
        });
        fitted = true;
        return;
      }

      const padding = groupKey ? 0.12 : 0.16;
      let viewport = getViewportForBounds(
        bounds,
        width,
        height,
        MIN_ZOOM,
        groupKey ? GROUP_MAX_ZOOM : OVERVIEW_MAX_ZOOM,
        padding,
      );

      if (groupKey) {
        const usableWidth = width * (1 - padding * 2);
        const usableHeight = height * (1 - padding * 2);
        const fitZoom = Math.min(
          GROUP_MAX_ZOOM,
          usableWidth / bounds.width,
          usableHeight / bounds.height,
        );

        // Narrow viewports may still not fit a whole block. Keep the frame
        // header readable and top-anchored; the group remains pannable.
        if (fitZoom < GROUP_MIN_READABLE_ZOOM) {
          const zoom = Math.min(
            GROUP_MAX_ZOOM,
            Math.max(GROUP_MIN_READABLE_ZOOM, usableWidth / bounds.width),
          );
          const contentWidth = bounds.width * zoom;
          const x =
            contentWidth > usableWidth
              ? padding * width - bounds.x * zoom
              : (width - contentWidth) / 2 - bounds.x * zoom;
          const y = padding * height - bounds.y * zoom;
          viewport = { x, y, zoom };
        }
      }

      void instance.setViewport(viewport, { duration: 200 });
      fitted = true;
    };

    // React Flow mounts the expanded nodes after the first frame. Two rAFs plus
    // a short timer let the new nodes reach the canvas before the transform is
    // set. Bounds come from our laid-out node data, not DOM measurements.
    const scheduleFit = () => {
      cancelScheduledFit();
      rafId = requestAnimationFrame(() => {
        rafId = requestAnimationFrame(runFit);
      });
      timerId = window.setTimeout(runFit, 110);
    };

    scheduleFit();
    return cancelScheduledFit;
  }, [requestedCollapsed, graph.grouping, graph.allCollapsed]);

  const displayEdges = useMemo(() => {
    if (!hoveredEdgeId) return edges;
    return edges.map((edge) =>
      edge.id === hoveredEdgeId
        ? {
            ...edge,
            style: {
              ...(edge.style ?? {}),
              stroke: theme.accent,
              strokeWidth: 1.7,
              opacity: 1,
            },
          }
        : edge,
    );
  }, [edges, hoveredEdgeId]);

  return (
    <div
      data-testid="workflow-canvas"
      className="flex h-full w-full flex-col overflow-hidden bg-abyss"
    >
      <div ref={canvasRef} className="relative min-h-0 flex-1">
        <ReactFlow
          key={`${fitSignal}-${fitMode}`}
          nodes={nodes}
          edges={displayEdges}
          nodeTypes={{
            workflowStep: WorkflowStepNode,
            workflowGroup: WorkflowGroupNode,
            workflowGroupFrame: WorkflowGroupFrameNode,
          }}
          defaultViewport={
            fitMode === "read" ? { x: 32, y: 32, zoom: 0.7 } : undefined
          }
          minZoom={0.15}
          maxZoom={1.6}
          nodesDraggable={false}
          nodesConnectable={false}
          edgesFocusable={false}
          onlyRenderVisibleElements={false}
          proOptions={{ hideAttribution: true }}
          className="bg-abyss"
          onEdgeMouseEnter={(_event, edge) => setHoveredEdgeId(edge.id)}
          onEdgeMouseLeave={() => setHoveredEdgeId(undefined)}
          onInit={(instance) => {
            flowRef.current = instance;
            const explicitFit = lastFitSignalRef.current !== fitSignal;
            lastFitSignalRef.current = fitSignal;
            if (fitMode === "read") return;

            if (explicitFit) {
              void instance.fitView({
                padding: 0.16,
                maxZoom: OVERVIEW_MAX_ZOOM,
                duration: 0,
              });
              return;
            }

            const applyOpeningViewport = (): boolean => {
              const canvas = canvasRef.current;
              const rect = canvas?.getBoundingClientRect();
              if (!rect || rect.width < 1 || rect.height < 1) return false;

              const first = graph.allCollapsed
                ? firstGroupNode(nodesRef.current)
                : undefined;
              if (first) {
                void instance.setViewport(
                  leftAnchoredGroupViewport(
                    first,
                    rect.width,
                    rect.height,
                    READABLE_ZOOM,
                    OPENING_PADDING,
                  ),
                  { duration: 0 },
                );
                return true;
              }

              void instance.fitView({
                padding: 0.16,
                maxZoom: OVERVIEW_MAX_ZOOM,
                duration: 0,
              });
              return true;
            };

            if (!applyOpeningViewport()) {
              requestAnimationFrame(() => {
                if (!applyOpeningViewport()) {
                  window.setTimeout(applyOpeningViewport, 80);
                }
              });
            }
          }}
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={20}
            size={1.1}
            color={theme.lineSoft}
          />
          <MiniMap
            pannable
            zoomable
            nodeColor={(node) => {
              if (node.type === "workflowGroupFrame") return theme.accent;
              if (node.type === "workflowGroup") return theme.accent;
              if (String(node.data?.traceState) === "focus") return theme.accent;
              if (String(node.data?.traceState) === "path") return theme.selection;
              if (String(node.data?.selected) === "true") return theme.selection;
              if (String(node.data?.subjectMatched) === "true") return theme.asset;
              return theme.line;
            }}
            maskColor="color-mix(in srgb, var(--color-abyss) 74%, transparent)"
            className="!m-2 !h-24 !w-40 overflow-hidden !rounded-[2px] border border-line"
          />
          <Controls
            position="top-right"
            showInteractive={false}
            className="m-2 overflow-hidden rounded-[2px] border border-line shadow-none [&_button]:border-line [&_button]:bg-panel [&_button]:text-muted [&_button:hover]:bg-panel-soft [&_button:hover]:text-accent"
          />
          <FlowInitializer nodes={nodes} />
        </ReactFlow>
        <div
          data-testid="execution-canvas-overlay"
          data-level="canvas-overlay"
          role="toolbar"
          aria-label="Execution graph grouping"
          className="absolute top-2 left-2 z-20 flex max-w-[calc(100%-1rem)] items-center gap-x-2 gap-y-1 overflow-hidden rounded-[4px] border border-line-soft bg-panel-raised/95 px-2 py-1"
        >
          <span className="shrink-0 text-[9px] text-faint">
            {model.overlay.grouping.label}
          </span>
          <div
            role="group"
            aria-label={model.overlay.grouping.ariaLabel}
            className="flex shrink-0 items-center gap-0.5"
          >
            {model.overlay.grouping.options.map((option) => (
              <button
                key={option.id}
                type="button"
                data-testid={`group-mode-${option.id}`}
                aria-pressed={option.active}
                onClick={option.command}
                className="ui-button ui-button-ghost min-h-[22px] px-1.5 text-[9px]"
              >
                {option.label}
              </button>
            ))}
          </div>
          <span className="h-3 w-px shrink-0 bg-line" aria-hidden />
          {model.overlay.actions.map((action) => (
            <button
              key={action.id}
              type="button"
              data-testid={action.id}
              onClick={action.run}
              aria-label={action.title ?? action.label}
              title={action.title ?? action.label}
              className="ui-button ui-button-ghost min-h-[22px] shrink-0 px-1.5 text-[9px]"
            >
              {action.label}
            </button>
          ))}
        </div>
        {graph.trace.focusStepId ? (
          <TraceBanner
            focusStepId={graph.trace.focusStepId}
            onClear={model.commands.clearTrace}
          />
        ) : null}
        <div
          role="note"
          className="pointer-events-none absolute bottom-2 left-2 z-10 inline-flex max-w-[calc(100%-12rem)] flex-wrap items-center gap-x-3 gap-y-1 rounded-[4px] border border-line-soft bg-panel-raised/90 px-2 py-1"
        >
          <span className="text-[9px] text-faint">{model.hint}</span>
          <span className="h-3 w-px bg-line" aria-hidden />
          <span className="flex flex-wrap items-center gap-2">
            <span className="text-[9px] text-faint">audit</span>
            {model.auditLegend.map(({ severity, label }) => (
              <span
                key={severity}
                className="inline-flex items-center gap-1 text-[9px] text-muted"
              >
                <span
                  className="size-1.5 rounded-full"
                  style={{ backgroundColor: severityColor[severity] }}
                  aria-hidden
                />
                {label}
              </span>
            ))}
          </span>
        </div>
      </div>
    </div>
  );
}
