"use client";

import type { KeyboardEvent } from "react";
import type { Node, NodeProps } from "@xyflow/react";
import { Handle, Position } from "@xyflow/react";
import {
  Boxes,
  Database,
  FileOutput,
  GitBranch,
  Layers3,
  Waypoints,
} from "lucide-react";
import { AnnotationPopover } from "@/shared/ui/AnnotationPopover";
import { cx, laneColor } from "@/shared/ui/theme";
import type { LineageLane, LineageNode, MetaGraphIndex } from "@/lib/types";
import type { ProvenanceNodeModel } from "@/diagnosis/provenance/model/ProvenanceModel";

export interface LineageNodeCardData extends Record<string, unknown> {
  node: ProvenanceNodeModel;
  metaGraph: MetaGraphIndex;
  onSelect: (node: LineageNode) => void;
}

export type LineageFlowNode = Node<LineageNodeCardData, "lineageNode">;

const laneText: Record<LineageLane, string> = {
  asset: "text-asset",
  source: "text-source",
  transformation: "text-transform",
  binding: "text-binding",
  post: "text-post",
  target: "text-target",
};

const laneDot: Record<LineageLane, string> = {
  asset: "bg-asset",
  source: "bg-source",
  transformation: "bg-transform",
  binding: "bg-binding",
  post: "bg-post",
  target: "bg-target",
};

const laneIcon = {
  asset: Boxes,
  source: Database,
  transformation: Layers3,
  binding: Waypoints,
  post: GitBranch,
  target: FileOutput,
} as const;

/**
 * One node on the focused lineage canvas.
 *
 * Blender node-editor shape: the lane colour is a tint on a 22px header strip,
 * the body remains graphite, sockets stay small and the selected node uses the
 * graph-selection orange. A node outside the active source filter is dimmed,
 * never removed: the review still needs to see that another source exists. The
 * whole card is a keyboard focus target so the canvas can be audited without a
 * mouse.
 */
export function LineageNodeCard({ data }: NodeProps<LineageFlowNode>) {
  const { node } = data;
  const lineageNode = node.node;
  const Icon = laneIcon[lineageNode.lane] ?? Waypoints;
  const isProperty = lineageNode.kind === "property";
  const select = () => data.onSelect(lineageNode);

  return (
    <div
      data-testid={`lineage-node-${lineageNode.id}`}
      role="button"
      tabIndex={0}
      aria-pressed={node.selected}
      aria-label={`Focus ${lineageNode.label}`}
      onClick={select}
      onKeyDown={(event: KeyboardEvent<HTMLDivElement>) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          select();
        }
      }}
      className={cx(
        "ui-node group relative w-[228px] cursor-pointer overflow-hidden rounded-[4px] text-left transition-colors",
        node.selected ? "ui-node-selected" : "hover:border-line-strong",
        node.dimmed && "opacity-30 saturate-50",
      )}
    >
      <Handle type="target" position={Position.Left} />

      <header
        className="ui-node-header min-h-[24px] min-w-0 rounded-t-none px-2 py-1"
        style={{
          backgroundColor: "var(--color-panel-raised)",
          boxShadow: `inset 3px 0 0 ${laneColor[lineageNode.lane]}`,
        }}
      >
        <span
          className={cx("size-1.5 shrink-0 rounded-full", laneDot[lineageNode.lane])}
          aria-hidden
        />
        <Icon
          className={cx("size-3 shrink-0", laneText[lineageNode.lane])}
          aria-hidden
        />
        <span className="min-w-0 truncate text-[9.5px] text-faint">
          {lineageNode.lane}
        </span>
        <span className="ml-auto flex shrink-0 items-center gap-1">
          {node.selected ? (
            <span className="ui-chip text-[9.5px] text-selection">
              focused
            </span>
          ) : node.terminal ? (
            <span className="ui-chip text-[9.5px] text-target">
              target
            </span>
          ) : null}
        </span>
      </header>

      <div className="min-w-0 px-2 py-1">
        <p
          className={cx(
            "line-clamp-2 break-words text-[11.5px] leading-snug",
            node.selected
              ? "font-semibold text-selection"
              : isProperty
                ? "font-semibold text-accent"
                : "font-medium text-text",
          )}
          title={lineageNode.label}
        >
          {lineageNode.label}
        </p>

        {node.description ? (
          <p className="mt-0.5 line-clamp-1 text-[10px] leading-relaxed text-muted">
            {node.description}
          </p>
        ) : null}

        <div className="mt-1 flex min-w-0 items-center gap-1 border-t border-line-soft/60 pt-1">
          {node.artifact ? (
            <span
              className="ui-chip min-w-0 max-w-full truncate font-mono text-[9.5px] text-faint"
              title={node.artifact}
            >
              {node.artifact}
            </span>
          ) : null}
          {node.dimmed ? (
            <span className="ui-chip shrink-0 text-[9.5px] text-faint">
              outside filter
            </span>
          ) : null}
          <span className="nodrag ml-auto shrink-0">
            <AnnotationPopover
              annotations={node.annotations}
              context={{ component: node.component, property: node.property }}
              metaGraph={data.metaGraph}
              compact
            />
          </span>
        </div>
      </div>

      <Handle type="source" position={Position.Right} />
    </div>
  );
}
