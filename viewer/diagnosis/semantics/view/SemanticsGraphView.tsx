"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import dagre from "@dagrejs/dagre";
import {
  Background,
  BackgroundVariant,
  BaseEdge,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  getBezierPath,
  type Edge,
  type EdgeProps,
  type Node,
  type ReactFlowInstance,
} from "@xyflow/react";
import { FlowInitializer } from "@/shared/graph/FlowInitializer";
import { horizontalHandles, measuredNode } from "@/shared/graph/geometry";
import { groupPalette, theme } from "@/shared/ui/theme";
import type {
  SemanticsCanvasEdgeModel,
  SemanticsMode,
  SemanticsModel,
} from "@/diagnosis/semantics/model/SemanticsModel";
import { SemanticsGrid } from "@/diagnosis/semantics/view/SemanticsGrid";
import {
  SemanticsEdgeGroupCard,
  SemanticsNodeCard,
} from "@/diagnosis/semantics/view/SemanticsNodeCard";
import { SemanticsBadgeLegend } from "@/diagnosis/semantics/view/SemanticsBadges";

export interface SemanticsGraphViewProps {
  model: SemanticsModel;
  /** Cards or Graph, owned by the panel header. */
  mode: SemanticsMode;
  /**
   * Optional external framing request (the panel header still owns Fit and
   * Read). The view owns the React Flow instance, zoom and hover state.
   */
  viewport?: { fitSignal?: number; fitMode?: "fit" | "read" };
}

const NODE_WIDTH = 248;
const NODE_HEIGHT = 248;
const EDGE_GROUP_WIDTH = 248;
const EDGE_GROUP_HEIGHT = 132;

interface SemanticsEdgeData extends Record<string, unknown> {
  edge: SemanticsCanvasEdgeModel;
}

function SemanticsEdge({
  id,
  data,
  label,
  labelStyle,
  labelShowBg,
  labelBgStyle,
  labelBgPadding,
  labelBgBorderRadius,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  style,
}: EdgeProps) {
  const [hovered, setHovered] = useState(false);
  const [path, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });
  const canvasEdge = (data as SemanticsEdgeData | undefined)?.edge;
  const name = canvasEdge?.name ?? id;
  const role = canvasEdge?.role ?? "source";
  const active = Boolean(canvasEdge?.active);
  const dimmed = Boolean(canvasEdge?.dimmed);
  const baseStroke =
    typeof style?.stroke === "string" ? style.stroke : theme.edge;
  const baseWidth =
    typeof style?.strokeWidth === "number" ? style.strokeWidth : 1.4;
  const baseOpacity =
    typeof style?.opacity === "number" ? style.opacity : 0.75;
  const stroke = active
    ? theme.selection
    : hovered
      ? theme.accent
      : baseStroke;
  const strokeWidth = active || hovered ? 2.5 : baseWidth;
  const opacity = active || hovered ? 0.95 : dimmed ? 0.06 : baseOpacity;

  return (
    <g
      data-testid={
        canvasEdge?.testId ??
        (role === "source" ? `bp-edge-${name}` : `bp-edge-${name}-${role}`)
      }
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <path
        d={path}
        fill="none"
        strokeOpacity={0}
        strokeWidth={20}
        className="react-flow__edge-interaction"
        vectorEffect="non-scaling-stroke"
        style={{ pointerEvents: "stroke" }}
      />
      <BaseEdge
        id={id}
        path={path}
        label={label}
        labelX={labelX}
        labelY={labelY}
        labelStyle={{
          ...labelStyle,
          fill: active ? theme.selection : theme.edgeStrong,
          opacity: active || hovered ? 0.95 : dimmed ? 0.06 : 1,
        }}
        labelShowBg={labelShowBg ?? true}
        labelBgStyle={{
          ...labelBgStyle,
          fill: theme.panel,
          fillOpacity: 0.9,
        }}
        labelBgPadding={labelBgPadding}
        labelBgBorderRadius={labelBgBorderRadius}
        markerEnd={markerEnd}
        interactionWidth={0}
        vectorEffect="non-scaling-stroke"
        style={{ ...style, stroke, strokeWidth, opacity }}
      />
    </g>
  );
}

function layout(nodes: Node[], edges: Edge[]): { nodes: Node[]; edges: Edge[] } {
  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({
    rankdir: "LR",
    nodesep: 36,
    ranksep: 44,
    marginx: 20,
    marginy: 20,
  });
  for (const node of nodes) {
    graph.setNode(node.id, {
      width: node.width ?? NODE_WIDTH,
      height: node.height ?? NODE_HEIGHT,
    });
  }
  for (const edge of edges) graph.setEdge(edge.source, edge.target);
  dagre.layout(graph);

  return {
    nodes: nodes.map((node) => {
      const point = graph.node(node.id);
      return {
        ...node,
        position: {
          x: point.x - (node.width ?? NODE_WIDTH) / 2,
          y: point.y - (node.height ?? NODE_HEIGHT) / 2,
        },
      };
    }),
    edges,
  };
}

const nodeTypes = {
  semanticsNode: SemanticsNodeCard,
  semanticsEdgeGroup: SemanticsEdgeGroupCard,
};
const edgeTypes = { semanticsEdge: SemanticsEdge };

/**
 * The Blueprint representation body.
 *
 * Graph and Cards are two readings of one semantic index; the view owns which
 * reading, whether the whole graph is shown, the audit key and the viewport.
 * The model owns what an entity, a property and a source field mean.
 */
export function SemanticsGraphView({
  model,
  mode,
  viewport,
}: SemanticsGraphViewProps) {
  const [legendOpen, setLegendOpen] = useState(false);
  const [wholeGraph, setWholeGraph] = useState(false);
  const fitMode = viewport?.fitMode ?? "fit";

  useEffect(() => {
    if (mode === "cards") setWholeGraph(false);
  }, [mode]);

  const focusKey = model.graph.focus?.groupId ?? "none";
  const focusNodes = useMemo(
    () => (model.graph.focus?.nodeIds ?? []).map((id) => ({ id })),
    [model.graph.focus],
  );
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const lastFitSignalRef = useRef(viewport?.fitSignal ?? 0);

  const { nodes, edges } = useMemo(() => {
    const focus = model.graph.focus;
    const entities = wholeGraph
      ? [...model.graph.entityCards, ...model.graph.edgeCards]
      : [...(focus?.nodeCards ?? []), ...(focus?.edgeCards ?? [])];
    const visibleNodes: Node[] = entities.map((entity) => ({
      id: entity.id,
      type: "semanticsNode",
      position: { x: 0, y: 0 },
      data: { entity, metaGraph: model.metaGraph },
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
      measured: measuredNode(NODE_WIDTH, NODE_HEIGHT),
      handles: horizontalHandles(NODE_WIDTH, NODE_HEIGHT),
      draggable: false,
    }));

    if (!wholeGraph) {
      for (const group of focus?.edgeGroups ?? []) {
        visibleNodes.push({
          id: group.id,
          type: "semanticsEdgeGroup",
          position: { x: 0, y: 0 },
          data: { group },
          width: EDGE_GROUP_WIDTH,
          height: EDGE_GROUP_HEIGHT,
          measured: measuredNode(EDGE_GROUP_WIDTH, EDGE_GROUP_HEIGHT),
          handles: horizontalHandles(EDGE_GROUP_WIDTH, EDGE_GROUP_HEIGHT),
          draggable: false,
        });
      }
    }

    const canvasEdges = wholeGraph
      ? model.graph.edges
      : (focus?.edges ?? []);

    const visibleEdges: Edge[] = canvasEdges.map((canvasEdge) => ({
      id: canvasEdge.id,
      source: canvasEdge.source,
      target: canvasEdge.target,
      label: canvasEdge.label,
      type: "semanticsEdge",
      data: { edge: canvasEdge },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: canvasEdge.active ? 15 : 13,
        height: canvasEdge.active ? 15 : 13,
        color: canvasEdge.active ? theme.selection : theme.edge,
      },
      style: {
        stroke: canvasEdge.active ? theme.selection : theme.edge,
        strokeWidth: canvasEdge.active ? 2.5 : 1.4,
        opacity: canvasEdge.active ? 0.95 : canvasEdge.dimmed ? 0.06 : 0.8,
      },
      labelStyle: {
        fill: canvasEdge.active ? theme.selection : theme.edgeStrong,
        fontSize: 9,
      },
      labelBgStyle: { fill: theme.panel, fillOpacity: 0.9 },
    }));

    return layout(visibleNodes, visibleEdges);
  }, [model.graph, model.metaGraph, wholeGraph]);

  /**
   * Open at a readable zoom. A composition that fits is centred; one that does
   * not is anchored to its top edge and stays pannable. The explicit Fit and
   * Read controls still fit the whole visible graph.
   */
  const handleInit = useCallback(
    (instance: ReactFlowInstance) => {
      const signal = viewport?.fitSignal ?? 0;
      const explicitFit = signal !== lastFitSignalRef.current;
      lastFitSignalRef.current = signal;

      if (wholeGraph) {
        void instance.fitView({ padding: 0.14, minZoom: 0.02, maxZoom: 1 });
        return;
      }

      const readable = fitMode === "read";
      if (readable || explicitFit) {
        void instance.fitView({
          nodes: focusNodes.length ? focusNodes : undefined,
          padding: 0.12,
          minZoom: readable ? 0.7 : 0.02,
          maxZoom: readable ? 0.9 : 1,
        });
        return;
      }

      const canvas = canvasRef.current;
      const rect = canvas?.getBoundingClientRect();
      if (!rect || rect.width < 1 || rect.height < 1 || !nodes.length) {
        void instance.fitView({
          nodes: focusNodes.length ? focusNodes : undefined,
          padding: 0.12,
          maxZoom: 0.85,
        });
        return;
      }

      const minX = Math.min(...nodes.map((node) => node.position.x));
      const minY = Math.min(...nodes.map((node) => node.position.y));
      const maxX = Math.max(
        ...nodes.map((node) => node.position.x + (node.width ?? NODE_WIDTH)),
      );
      const maxY = Math.max(
        ...nodes.map((node) => node.position.y + (node.height ?? NODE_HEIGHT)),
      );
      const padding = 24;
      const topPadding = 56;
      const fitZoom = Math.min(
        (rect.width - padding * 2) / Math.max(1, maxX - minX),
        (rect.height - topPadding - padding) / Math.max(1, maxY - minY),
        0.95,
      );
      // The grouped focused composition is small enough to open readably; the
      // wide canvas takes the larger floor, the narrow one still keeps card
      // text legible. Fit remains the way to see the whole composition.
      const openingFloor = rect.width >= 1000 ? 0.85 : 0.7;
      const zoom = Math.max(openingFloor, fitZoom);
      const contentWidth = (maxX - minX) * zoom;
      const contentHeight = (maxY - minY) * zoom;
      void instance.setViewport({
        // Always anchor the composition to its left edge. A wide composition
        // that is centred would push its first cards under the Outliner and
        // make their annotation and actions unreachable.
        x: padding - minX * zoom,
        y:
          contentHeight > rect.height - topPadding - padding
            ? topPadding - minY * zoom
            : (rect.height - contentHeight) / 2 - minY * zoom,
        zoom,
      });
    },
    [fitMode, focusNodes, nodes, viewport?.fitSignal, wholeGraph],
  );

  const subjectName =
    model.graph.selectedSubject?.component ?? model.graph.selectedSubject?.name;

  return (
    <div className="relative h-full w-full bg-abyss">
      {mode === "cards" ? (
        <SemanticsGrid model={model} />
      ) : (
        <div
          ref={canvasRef}
          data-testid="blueprint-canvas"
          className="h-full w-full [&_.react-flow__pane]:cursor-grab"
        >
          <ReactFlow
            key={`${viewport?.fitSignal ?? 0}-${fitMode}-${
              wholeGraph ? "whole" : focusKey
            }`}
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            onInit={handleInit}
            minZoom={0.02}
            maxZoom={1.5}
            nodesDraggable={false}
            nodesConnectable={false}
            proOptions={{ hideAttribution: true }}
            className="bg-abyss"
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={20}
              size={1}
              color={theme.lineSoft}
            />
            <MiniMap
              pannable
              zoomable
              className="rounded-[2px] shadow-none"
              nodeColor={(node) => {
                const entity = (
                  node.data as { entity?: { name?: string; kind?: string; paletteIndex?: number } }
                )?.entity;
                if (!entity) return theme.edge;
                if (subjectName && subjectName === entity.name) {
                  return theme.selection;
                }
                if (entity.kind === "edge") return theme.accent;
                return (
                  groupPalette[
                    (entity.paletteIndex ?? 0) % groupPalette.length
                  ] ?? theme.edge
                );
              }}
              maskColor="color-mix(in srgb, var(--color-abyss) 74%, transparent)"
            />
            <Controls
              showInteractive={false}
              className="rounded-[2px] shadow-none [&_button:hover]:text-accent-strong"
            />
            <FlowInitializer nodes={nodes} />
          </ReactFlow>

          <div
            data-testid="blueprint-graph-overlay"
            data-level="canvas-overlay"
            role="toolbar"
            aria-label={model.overlay.label}
            className="absolute top-2 left-2 z-20 inline-flex max-w-[calc(100%-1rem)] flex-wrap items-center gap-x-2 gap-y-1 rounded-[4px] border border-line-soft bg-panel-raised/95 px-2 py-1"
          >
            <button
              type="button"
              data-testid="bp-graph-whole"
              aria-pressed={wholeGraph}
              onClick={() => setWholeGraph((whole) => !whole)}
              className="ui-button ui-button-ghost min-h-[22px] px-1.5 text-[9px]"
              title={
                wholeGraph
                  ? model.overlay.wholeGraph.focusTitle
                  : model.overlay.wholeGraph.title
              }
            >
              {wholeGraph
                ? model.overlay.wholeGraph.focusLabel
                : model.overlay.wholeGraph.label}
            </button>
            <span className="h-3 w-px bg-line" aria-hidden />
            <button
              type="button"
              data-testid="bp-badge-legend-toggle"
              aria-expanded={legendOpen}
              onClick={() => setLegendOpen((open) => !open)}
              className="ui-button ui-button-ghost min-h-[22px] px-1.5 text-[9px]"
              title={model.overlay.auditKey.title}
            >
              {model.overlay.auditKey.label}
            </button>
            {legendOpen ? (
              <>
                <span className="h-3 w-px bg-line" aria-hidden />
                <SemanticsBadgeLegend
                  entries={model.overlay.auditKey.legend}
                />
              </>
            ) : null}
            <p
              data-testid="blueprint-graph-hint"
              className={
                legendOpen
                  ? "sr-only"
                  : "hidden min-w-0 max-w-[16rem] shrink truncate text-[9px] text-faint 2xl:block"
              }
            >
              {wholeGraph
                ? model.overlay.hints.wholeGraph
                : model.overlay.hints.graph}
            </p>
            <span className="shrink-0 font-mono text-[9px] text-muted tabular-nums">
              {wholeGraph
                ? model.overlay.counts.wholeLabel
                : model.overlay.counts.focusLabel}
            </span>
            {model.overlay.scaleHint.visible ? (
              <span
                data-testid="blueprint-scale-hint"
                title={
                  wholeGraph
                    ? model.overlay.scaleHint.wholeTitle
                    : model.overlay.scaleHint.focusTitle
                }
                className={
                  wholeGraph
                    ? "hidden shrink-0 items-center gap-1 text-[9px] text-faint 2xl:inline-flex"
                    : "hidden"
                }
              >
                <span className="size-1.5 rounded-full bg-medium" aria-hidden />
                {wholeGraph
                  ? model.overlay.scaleHint.wholeChip
                  : model.overlay.scaleHint.focusChip}
              </span>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
