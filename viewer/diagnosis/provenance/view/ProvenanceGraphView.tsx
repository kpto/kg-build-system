"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
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
  type NodeProps,
  type ReactFlowInstance,
} from "@xyflow/react";
import {
  ArrowRight,
  Filter,
  MousePointerClick,
  X,
} from "lucide-react";
import { FlowInitializer } from "@/shared/graph/FlowInitializer";
import { horizontalHandles, measuredNode } from "@/shared/graph/geometry";
import { cx, laneColor, theme } from "@/shared/ui/theme";
import type { LineageLane } from "@/lib/types";
import type {
  ProvenanceEmptyModel,
  ProvenanceLaneModel,
  ProvenanceModel,
  ProvenanceNodeModel,
} from "@/diagnosis/provenance/model/ProvenanceModel";
import { LineageNodeCard } from "@/diagnosis/provenance/view/LineageNodeCard";
import { ProofReceipt } from "@/diagnosis/provenance/view/ProofReceipt";
import { BranchComparison } from "@/diagnosis/provenance/view/BranchComparison";
import { EntityQuestions } from "@/diagnosis/provenance/view/EntityQuestions";
import {
  DecisionsPanel,
  ImpactPanel,
} from "@/diagnosis/provenance/view/ProvenanceSections";

export interface ProvenanceGraphViewProps {
  model: ProvenanceModel;
  /**
   * Optional external framing request (the old panel header still owns Fit and
   * Read). The view owns the React Flow instance, zoom, hover and the dismissed
   * source-filter chip.
   */
  viewport?: { fitSignal?: number; fitMode?: "fit" | "read" };
}

const NODE_WIDTH = 236;
const NODE_HEIGHT = 96;
const LANE_HEADER_WIDTH = 180;
const LANE_HEADER_HEIGHT = 22;

const laneBar: Record<LineageLane, string> = {
  asset: "bg-asset",
  source: "bg-source",
  transformation: "bg-transform",
  binding: "bg-binding",
  post: "bg-post",
  target: "bg-target",
};

interface LineageLaneHeaderData extends Record<string, unknown> {
  label: string;
  lane: LineageLane;
  count: number;
  order: number;
}

type LineageLaneHeaderNode = Node<LineageLaneHeaderData, "laneHeader">;

function LineageLaneHeader({ data }: NodeProps<LineageLaneHeaderNode>) {
  return (
    <div
      className="flex h-[22px] w-[180px] items-center gap-1.5 overflow-hidden rounded-[2px] border border-line-soft bg-panel-raised/95 pl-1.5 pr-2"
      title={`${data.label} · ${data.count} node${data.count === 1 ? "" : "s"}`}
    >
      <span
        className={cx("h-3 w-[3px] shrink-0 rounded-sm", laneBar[data.lane])}
        aria-hidden
      />
      <span className="tnum shrink-0 font-mono text-[8.5px] text-faint">
        {String(data.order + 1).padStart(2, "0")}
      </span>
      <span className="ui-label truncate text-text">{data.label}</span>
      <span className="tnum ml-auto shrink-0 font-mono text-[8.5px] text-faint">
        {data.count}
      </span>
    </div>
  );
}

function layout(
  nodes: Node[],
  edges: Edge[],
  lanes: ProvenanceLaneModel[],
): Node[] {
  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({
    rankdir: "LR",
    nodesep: 22,
    ranksep: 72,
    marginx: 32,
    marginy: 60,
  });
  for (const node of nodes) {
    graph.setNode(node.id, {
      width: node.width ?? NODE_WIDTH,
      height: node.height ?? NODE_HEIGHT,
    });
  }
  for (const edge of edges) graph.setEdge(edge.source, edge.target);
  dagre.layout(graph);

  const positioned = nodes.map((node) => {
    const point = graph.node(node.id);
    return {
      ...node,
      position: {
        x: point.x - (node.width ?? NODE_WIDTH) / 2,
        y: point.y - (node.height ?? NODE_HEIGHT) / 2,
      },
    };
  });

  const headers: Node[] = [];
  const laneMeta = new Map(lanes.map((lane) => [lane.id, lane]));
  const lanePositions = new Map<
    string,
    { x: number; label: string; count: number; order: number }
  >();
  for (const node of positioned) {
    const modelNode = (node.data as { node?: ProvenanceNodeModel }).node;
    if (!modelNode) continue;
    const meta = laneMeta.get(modelNode.lane);
    const existing = lanePositions.get(modelNode.lane);
    if (!existing) {
      lanePositions.set(modelNode.lane, {
        x: node.position.x,
        label: meta?.label ?? laneLabel(modelNode.lane),
        count: meta?.count ?? 0,
        order: meta?.order ?? laneOrder(modelNode.lane),
      });
    } else if (node.position.x < existing.x) {
      existing.x = node.position.x;
    }
  }
  for (const [lane, position] of lanePositions) {
    headers.push({
      id: `lane:${lane}`,
      type: "laneHeader",
      position: { x: position.x, y: -52 },
      data: {
        label: position.label,
        lane: lane as LineageLane,
        count: position.count,
        order: position.order,
      },
      width: LANE_HEADER_WIDTH,
      height: LANE_HEADER_HEIGHT,
      measured: measuredNode(LANE_HEADER_WIDTH, LANE_HEADER_HEIGHT),
      draggable: false,
      selectable: false,
    });
  }

  return [...positioned, ...headers];
}

function laneLabel(lane: LineageLane): string {
  return (
    {
      asset: "Asset",
      source: "Source / Table",
      transformation: "Transformation / Projection",
      binding: "Binding",
      post: "Post-processing",
      target: "Target",
    } as Record<LineageLane, string>
  )[lane];
}

function laneOrder(lane: LineageLane): number {
  const order: LineageLane[] = [
    "asset",
    "source",
    "transformation",
    "binding",
    "post",
    "target",
  ];
  return Math.max(0, order.indexOf(lane));
}

function LineageEdge({
  id,
  label,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  style,
}: EdgeProps) {
  const [path, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });
  return (
    <g>
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
        markerEnd={markerEnd}
        interactionWidth={0}
        vectorEffect="non-scaling-stroke"
        style={style}
      />
      {label ? (
        <text
          x={labelX}
          y={labelY}
          textAnchor="middle"
          dominantBaseline="middle"
          fill={typeof style?.stroke === "string" ? style.stroke : theme.edge}
          opacity={typeof style?.opacity === "number" ? style.opacity : 1}
          fontSize={8}
          fontFamily="var(--font-mono)"
          style={{ paintOrder: "stroke", stroke: theme.panel, strokeWidth: 3 }}
        >
          {label}
        </text>
      ) : null}
    </g>
  );
}

const nodeTypes = {
  lineageNode: LineageNodeCard,
  laneHeader: LineageLaneHeader,
};
const edgeTypes = { lineageEdge: LineageEdge };

const chainToneClass: Record<string, string> = {
  source: "border-source/40 bg-source/10 text-source",
  asset: "border-asset/40 bg-asset/10 text-asset",
  transform: "border-transform/40 bg-transform/10 text-transform",
  accent: "border-accent/40 bg-accent/10 text-accent",
  target: "border-target/40 bg-target/10 text-target",
};

function EmptyLineage({ model }: { model: ProvenanceEmptyModel }) {
  return (
    <div
      data-testid="lineage-empty"
      className="flex h-full items-center justify-center overflow-y-auto bg-abyss p-6"
    >
      <div
        data-level="section"
        role="region"
        aria-label="which property should be traced?"
        className="ui-section w-full max-w-xl text-left"
      >
        <div className="ui-section-header border-b border-line-soft bg-panel">
          <MousePointerClick className="size-3 shrink-0 text-accent" aria-hidden />
          <span className="ui-section-title">{model.title}</span>
          <span className="ui-section-count ml-auto shrink-0">
            {model.countLabel}
          </span>
        </div>
        <div className="ui-section-body p-2">
          <p className="text-[12px] font-semibold tracking-tight text-text">
            {model.heading}
          </p>
          <p className="mt-1 max-w-[58ch] text-[10.5px] leading-relaxed text-muted">
            {model.body}
          </p>

          <div className="mt-2 flex flex-wrap items-center gap-1.5 font-mono text-[9px]">
            {model.chain.map((step, index) => (
              <span key={step.id} className="flex items-center gap-1.5">
                {index > 0 ? (
                  <ArrowRight className="size-3 text-faint" aria-hidden />
                ) : null}
                <span className={cx("ui-chip", chainToneClass[step.tone])}>
                  {step.label}
                </span>
              </span>
            ))}
          </div>

          <div className="mt-2 border-t border-line-soft pt-2">
            <p className="ui-section-label text-faint">example properties</p>
            <div className="mt-1 flex flex-wrap items-center gap-1">
              {model.examples.map((example) => (
                <button
                  key={example.id}
                  type="button"
                  data-testid={example.id}
                  onClick={() => example.action?.run()}
                  disabled={!example.action}
                  className="ui-button ui-button-ghost min-h-[22px] font-mono text-[10px]"
                >
                  {example.label}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-2 flex flex-wrap items-center justify-between gap-2 border-t border-line-soft pt-2">
            <button
              type="button"
              data-testid="lineage-empty-open-blueprint"
              onClick={() => model.openBlueprint.run()}
              className="ui-button ui-button-primary min-h-[24px] text-[11px]"
            >
              {model.openBlueprint.label}
              <ArrowRight className="size-3.5" aria-hidden />
            </button>
            <span className="font-mono text-[9px] text-faint">
              {model.footnote}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * The Provenance representation body.
 *
 * The model owns the traced property, its branches, receipt, impact, decisions
 * and questions. The view owns the canvas, hover, zoom and the dismissed
 * source-filter chip; it maps the plain lineage nodes and edges to React Flow.
 */
export function ProvenanceGraphView({
  model,
  viewport,
}: ProvenanceGraphViewProps) {
  const [dismissedFilter, setDismissedFilter] = useState(false);
  const fitMode = viewport?.fitMode ?? "fit";

  useEffect(() => {
    setDismissedFilter(false);
  }, [model.sourceFilter.active]);

  const activeFilter =
    model.sourceFilter.visible && !dismissedFilter
      ? model.sourceFilter.active
      : undefined;

  const { nodes, edges } = useMemo(() => {
    if (!model.graph) return { nodes: [] as Node[], edges: [] as Edge[] };
    const graph = model.graph;
    const visibleNodes: Node[] = graph.nodes.map((node) => ({
      id: node.id,
      type: "lineageNode",
      position: { x: 0, y: 0 },
      data: {
        node: activeFilter ? node : { ...node, dimmed: false },
        metaGraph: model.metaGraph,
        onSelect: model.commands.selectNode,
      },
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
      measured: measuredNode(NODE_WIDTH, NODE_HEIGHT),
      handles: horizontalHandles(NODE_WIDTH, NODE_HEIGHT),
      draggable: false,
    }));

    const visibleEdges: Edge[] = graph.edges.map((edge) => {
      const dimmed = Boolean(activeFilter) && edge.dimmed;
      const laneTint = edge.laneTint
        ? laneColor[edge.laneTint]
        : undefined;
      const stroke = edge.active
        ? theme.selection
        : dimmed
          ? theme.edge
          : (laneTint ?? theme.edge);
      const opacity = edge.active
        ? 0.95
        : dimmed
          ? 0.06
          : laneTint
            ? 0.78
            : 0.8;
      return {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.label,
        type: "lineageEdge",
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: edge.active ? 15 : 13,
          height: edge.active ? 15 : 13,
          color: edge.active
            ? theme.selection
            : (laneTint ?? theme.edge),
        },
        style: {
          stroke,
          strokeWidth: edge.active ? 2.5 : 1.3,
          opacity,
        },
      };
    });

    return {
      nodes: layout(visibleNodes, visibleEdges, graph.lanes),
      edges: visibleEdges,
    };
  }, [model.graph, model.metaGraph, model.commands.selectNode, activeFilter]);

  const seenFitSignal = useRef(viewport?.fitSignal ?? 0);
  const handleInit = useCallback(
    (instance: ReactFlowInstance) => {
      const signal = viewport?.fitSignal ?? 0;
      const explicitRequest = signal !== seenFitSignal.current;
      seenFitSignal.current = signal;
      const readable = fitMode === "read";

      if (explicitRequest && !readable) {
        void instance.fitView({ padding: 0.15, maxZoom: 1 });
        return;
      }

      const focusNodeId = model.graph?.focusNodeId;
      if (focusNodeId) {
        void instance.fitView({
          nodes: [{ id: focusNodeId }],
          padding: 0.3,
          minZoom: 0.7,
          maxZoom: 0.8,
        });
        return;
      }

      void instance.fitView({ padding: 0.15, minZoom: 0.7, maxZoom: 0.8 });
    },
    [fitMode, model.graph?.focusNodeId, viewport?.fitSignal],
  );

  if (!model.graph) {
    return <EmptyLineage model={model.empty} />;
  }

  const graph = model.graph;
  const selectedNodeId = graph.nodes.find((node) => node.selected)?.id;

  return (
    <div className="flex h-full w-full flex-col">
      <div data-testid="lineage-canvas" className="relative min-h-0 flex-1">
        <ReactFlow
          key={`${viewport?.fitSignal ?? 0}-${fitMode}-${graph.selectionLabel}`}
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          onInit={handleInit}
          minZoom={0.12}
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
              if (node.type === "laneHeader") return theme.lineSoft;
              const modelNode = (node.data as { node?: ProvenanceNodeModel }).node;
              if (!modelNode) return theme.edge;
              if (modelNode.id === selectedNodeId) return theme.selection;
              if (modelNode.terminal) return theme.target;
              return laneColor[modelNode.lane];
            }}
            maskColor={`color-mix(in srgb, ${theme.page} 72%, transparent)`}
          />
          <Controls
            showInteractive={false}
            className="rounded-[2px] shadow-none [&_button:hover]:text-accent-strong"
          />
          <FlowInitializer nodes={nodes} />
        </ReactFlow>

        {activeFilter ? (
          <div
            data-testid="lineage-source-filter"
            data-level="canvas-overlay"
            className="ui-panel absolute top-2 left-2 z-10 flex max-w-[calc(100%-1rem)] flex-wrap items-center gap-x-2 gap-y-1 overflow-hidden rounded-[2px] px-1.5 py-1"
          >
            <Filter className="size-3 shrink-0 text-accent" aria-hidden />
            <div className="min-w-0">
              <p className="ui-label text-faint">
                {model.sourceFilter.label}
              </p>
              <p className="truncate font-mono text-[10px] text-accent">
                {activeFilter}
              </p>
            </div>
            <span className="ui-chip tnum border-line-soft bg-panel-soft/40 font-mono text-[9px] text-muted">
              {model.sourceFilter.countLabel}
            </span>
            <button
              type="button"
              data-testid="clear-source-filter"
              onClick={() => {
                setDismissedFilter(true);
                model.sourceFilter.clear.run();
              }}
              className="ui-button ui-button-ghost gap-1 font-mono text-[9px]"
              title={model.sourceFilter.title}
            >
              <X className="size-2.5" aria-hidden />
              clear
            </button>
          </div>
        ) : null}

        <div
          data-testid="lineage-hint"
          className="ui-hint pointer-events-none absolute bottom-3 left-1/2 z-10 max-w-[calc(100%-12rem)] -translate-x-1/2 px-2.5 py-1 text-center font-mono text-[10px]"
        >
          <span className="text-muted">Drag to pan</span>
          <span className="mx-1 text-line">·</span>
          <span className="text-muted">scroll to zoom</span>
          <span className="mx-1 text-line">·</span>
          <span className="text-muted">click a node for detail</span>
        </div>
      </div>

      <div className="flex max-h-[52%] shrink-0 flex-col border-t border-line-soft bg-panel">
        <div className="thin-scrollbar min-h-0 flex-1 overflow-y-auto p-1">
          <div className="grid grid-cols-1 gap-1 2xl:grid-cols-[3fr_2fr]">
            <div className="min-w-0">
              {model.receipt ? <ProofReceipt model={model.receipt} /> : null}
            </div>

            <div className="min-w-0">
              {model.branchComparison ? (
                <BranchComparison model={model.branchComparison} />
              ) : null}
              {model.questions ? (
                <EntityQuestions model={model.questions} />
              ) : null}
              {model.impact ? <ImpactPanel model={model.impact} /> : null}
              {model.decisions ? (
                <DecisionsPanel model={model.decisions} />
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
