"use client";

import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import clsx from "clsx";

import { ProblemBadge } from "@/components/ui";
import type { Component, ComponentTier } from "@/lib/ir";
import { useProblemsForRef } from "@/stores/problemStore";
import { useTopologyCanvas } from "./canvasContext";

/** The `data` a vertex node carries — the component plus what the card shows. */
export interface VertexData extends Record<string, unknown> {
  component: Component;
  title: string;
  subtitle: string;
}

export type VertexNode = Node<VertexData, "vertex">;

const TIER_SHELL: Record<ComponentTier, string> = {
  // concrete node = filled blue; category = dashed grey; template = amber.
  concrete: "border-node bg-node-soft",
  category: "border-dashed border-category/70 bg-raised",
  template: "border-template/70 bg-raised",
};

const TIER_GLYPH: Record<ComponentTier, string> = {
  concrete: "rounded-full bg-node",
  // A ring reads as "abstract parent" (never bound on its own).
  category: "rounded-full border-2 border-dashed border-category",
  // A diamond reads as a mix-in, distinct from the circle of a real vertex.
  template: "rotate-45 rounded-[2px] bg-template",
};

/**
 * One topology vertex: name, a kind/tier glyph, and the ref's problem badge.
 *
 * It carries an out-port (source handle) and an in-port (target handle) so an edge is
 * drawn by dragging port-to-port rather than filling a form. Both handles are on every
 * node — a category or a node template is still a legal endpoint; the edge-kind pairing
 * that makes an illegal edge impossible is refused in the create flow with a reason, so
 * a half-hidden port never leaves the user guessing why a drag was rejected.
 */
export function VertexNodeComponent({ id, data, selected }: NodeProps<VertexNode>) {
  const ref = `component:${data.component.id}`;
  const problems = useProblemsForRef(ref);
  const { onSelectRef, onNodeClick } = useTopologyCanvas();
  const component = data.component;

  const activate = () => {
    onNodeClick(id);
    onSelectRef(ref);
  };

  return (
    <div
      data-testid={`vertex-${component.id}`}
      data-tier={component.tier}
      data-kind={component.kind}
      onClick={activate}
      className={clsx(
        "studio-card min-w-[10rem] max-w-[13rem] cursor-pointer px-2 py-1.5 transition-colors",
        TIER_SHELL[component.tier],
        selected && "border-info ring-1 ring-info",
      )}
    >
      <Handle
        type="target"
        id="in"
        position={Position.Left}
        className="!left-[-5px]"
        aria-label={`${component.name} in-port`}
      />
      <div className="flex items-center gap-1.5">
        <span aria-hidden className={clsx("h-2.5 w-2.5 shrink-0", TIER_GLYPH[component.tier])} />
        <span className="min-w-0 flex-1 truncate text-[12px] font-semibold text-ink">
          {data.title}
        </span>
        <ProblemBadge
          problems={problems}
          ref={ref}
          compact
          onClick={() => onSelectRef(ref)}
        />
      </div>
      <div className="mt-0.5 flex items-center gap-1.5 pl-4">
        <span
          className={clsx(
            "shrink-0 font-mono text-[9px] uppercase tracking-wide",
            component.kind === "edge" ? "text-edgekind" : "text-muted",
          )}
        >
          {component.kind}
        </span>
        <span className="truncate font-mono text-[10px] text-faint">{data.subtitle}</span>
      </div>
      <Handle
        type="source"
        id="out"
        position={Position.Right}
        className="!right-[-5px]"
        aria-label={`${component.name} out-port`}
      />
    </div>
  );
}
