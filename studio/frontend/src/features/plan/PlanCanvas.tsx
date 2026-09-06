"use client";

/**
 * The plan canvas: a lane band behind each module, a compositor card per step, and
 * bezier connections from socket to socket, coloured by the artifact role and
 * arrow-headed at the consumer (the data direction).
 *
 * Lanes are drawn inside `ViewportPortal`, so they pan and zoom with the graph
 * without becoming nodes — they must never be selectable, draggable, or counted as
 * steps. Hovering is passed in as a trace, computed by the feature so this
 * component stays a projection of the model.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Background,
  BackgroundVariant,
  MarkerType,
  ReactFlow,
  ReactFlowProvider,
  ViewportPortal,
  useReactFlow,
  type Edge,
  type Node,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { EmptyState } from "@/components/ui";
import type { Problem } from "@/lib/types";
import type { PlanModel } from "./model";
import { problemsForStep } from "./model";
import { StepNodeCard, STEP_WIDTH, type StepFlowNode } from "./StepNode";
import { stepRef } from "./detail";
import { roleColor } from "./roles";
import { TOKEN } from "./tokens";
import type { Trace } from "./subdag";

const NODE_TYPES = { step: StepNodeCard } as unknown as NodeTypes;

/** Scoped overrides React Flow's stylesheet does not expose as props. */
const CANVAS_CSS = `
.react-flow__node.plan-step-node { cursor: pointer; }
.react-flow__node.selected .studio-card { border-color: var(--color-info); box-shadow: 0 0 0 1px var(--color-info); }
.react-flow__edge { transition: opacity 90ms linear; }
.react-flow__handle { border: 1px solid var(--color-canvas); }
`;

function edgeStyle(edge: PlanModel["visibleEdges"][number], dimmed: boolean): Edge {
  const color = roleColor(edge.role ?? null);
  return {
    id: edge.id,
    source: edge.from_step,
    target: edge.to_step,
    sourceHandle: edge.from_slot,
    targetHandle: edge.to_slot,
    type: "default", // React Flow's default edge *is* the bezier
    style: { stroke: color, strokeWidth: 1.4, opacity: dimmed ? 0.08 : 0.9 },
    markerEnd: { type: MarkerType.ArrowClosed, width: 10, height: 10, color },
  };
}

export interface PlanCanvasProps {
  readonly model: PlanModel;
  readonly trace: Trace;
  readonly hovered: string | null;
  readonly byRefIndex: Readonly<Record<string, Problem[]>>;
  readonly fitToken: number;
  readonly onHover: (id: string | null) => void;
  readonly onSelectRef: (ref: string | null) => void;
  readonly onOpenSql: (id: string) => void;
}

function PlanCanvasInner({
  model,
  trace,
  hovered,
  byRefIndex,
  fitToken,
  onHover,
  onSelectRef,
  onOpenSql,
}: PlanCanvasProps) {
  const { fitView } = useReactFlow();
  const [interacting, setInteracting] = useState(false);

  const byId = useMemo(() => new Map(model.visibleNodes.map((node) => [node.id, node])), [model.visibleNodes]);

  const handleHover = useCallback(
    (id: string | null) => {
      if (id === hovered) return;
      onHover(id);
    },
    [hovered, onHover],
  );

  const nodes = useMemo<Node[]>(
    () =>
      model.layout.placed.flatMap((placed) => {
        const step = byId.get(placed.id);
        const detail = model.details.get(placed.id);
        if (!step || !detail) return [];
        const dimmed = hovered !== null && !trace.related.has(placed.id);
        return [
          {
            id: placed.id,
            type: "step",
            position: { x: placed.x, y: placed.y },
            width: placed.width || STEP_WIDTH,
            height: placed.height,
            draggable: false,
            selectable: true,
            focusable: true,
            zIndex: dimmed ? 0 : 2,
            className: "plan-step-node",
            data: {
              step,
              detail,
              laneColor: model.colors.get(placed.lane) ?? TOKEN.lineStrong,
              selected: model.selectedSteps.has(placed.id),
              dimmed,
              problems: problemsForStep(byRefIndex, step),
              onSelect: onSelectRef,
              onOpenSql,
              onHover: handleHover,
            },
          } satisfies StepFlowNode as unknown as Node,
        ];
      }),
    [byId, model, byRefIndex, hovered, trace, onSelectRef, onOpenSql, handleHover],
  );

  const edges = useMemo<Edge[]>(
    () =>
      model.visibleEdges.map((edge) =>
        edgeStyle(edge, hovered !== null && !trace.relatedEdges.has(edge.id)),
      ),
    [model.visibleEdges, hovered, trace],
  );

  // Fit on load, on every relayout the user asks for, and after a filter change.
  useEffect(() => {
    if (model.layout.placed.length === 0) return;
    const frame = requestAnimationFrame(() => {
      void fitView({ padding: 0.06, duration: interacting ? 160 : 0, maxZoom: 1.05 });
    });
    return () => cancelAnimationFrame(frame);
  }, [fitToken, model.layout, fitView, interacting]);

  return (
    <div className="relative min-h-0 flex-1" data-plan-canvas="true">
      <style>{CANVAS_CSS}</style>
      {model.layout.placed.length === 0 ? (
        <EmptyState
          title={model.nodes.length === 0 ? "No compiled plan to draw" : "Nothing matches these filters"}
          body={
            model.nodes.length === 0
              ? "GET /api/plan answered without a plan. Recompile to produce one."
              : `${model.totals.steps} steps are compiled; widen the filters to see them.`
          }
        />
      ) : (
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={NODE_TYPES}
          fitView
          fitViewOptions={{ padding: 0.06, maxZoom: 1.05 }}
          minZoom={0.06}
          maxZoom={2.4}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable
          onlyRenderVisibleElements
          onMoveStart={() => setInteracting(true)}
          onNodeClick={(_event, node) => {
            const step = byId.get(node.id);
            const ref = step ? stepRef(step) : null;
            if (ref) onSelectRef(model.selectedSteps.has(node.id) ? null : ref);
          }}
          onPaneClick={() => onSelectRef(null)}
        >
          <Background variant={BackgroundVariant.Dots} gap={26} size={1} color={TOKEN.line} />
          <ViewportPortal>
            {model.layout.lanes.map((lane) => {
              const color = model.colors.get(lane.moduleId) ?? TOKEN.lineStrong;
              return (
                <div
                  key={lane.moduleId}
                  data-lane={lane.moduleId}
                  className="pointer-events-none absolute select-none rounded-lg"
                  style={{
                    left: lane.x,
                    top: 0,
                    width: lane.width,
                    height: lane.height,
                    background: `${color}0e`,
                    border: `1px solid ${color}24`,
                  }}
                >
                  <span
                    className="absolute left-2 top-1.5 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.1em]"
                    style={{ color }}
                  >
                    <span aria-hidden className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />
                    {lane.label}
                    <span className="normal-case tracking-normal text-faint">
                      {lane.stepCount} steps · {lane.role}
                    </span>
                  </span>
                </div>
              );
            })}
          </ViewportPortal>
        </ReactFlow>
      )}
    </div>
  );
}

export function PlanCanvas(props: PlanCanvasProps) {
  return (
    <ReactFlowProvider>
      <PlanCanvasInner {...props} />
    </ReactFlowProvider>
  );
}
