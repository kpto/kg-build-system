"use client";

import type { Node, NodeProps } from "@xyflow/react";
import { Handle, Position, useReactFlow } from "@xyflow/react";
import { ShieldQuestion } from "lucide-react";
import { AnnotationPopover } from "@/shared/ui/AnnotationPopover";
import { cx, groupPalette, theme } from "@/shared/ui/theme";
import type { MetaGraphIndex } from "@/lib/types";
import type {
  SemanticsEdgeGroupModel,
  SemanticsEntityModel,
} from "@/diagnosis/semantics/model/SemanticsModel";
import { SemanticsPropertyRow } from "@/diagnosis/semantics/view/SemanticsPropertyRow";

export interface SemanticsNodeData extends Record<string, unknown> {
  entity: SemanticsEntityModel;
  metaGraph: MetaGraphIndex;
}

export type SemanticsFlowNode = Node<SemanticsNodeData, "semanticsNode">;

export interface SemanticsEdgeGroupData extends Record<string, unknown> {
  group: SemanticsEdgeGroupModel;
}

export type SemanticsEdgeGroupFlowNode = Node<
  SemanticsEdgeGroupData,
  "semanticsEdgeGroup"
>;

/**
 * One grouped edge card for the focused composition.
 *
 * Parallel relationships between the same two nodes share one card and one
 * connector pair. The card shows the relationship role, its edge count, and two
 * readable relationship names; the remaining names stay in the DOM for tests
 * and for assistive technology.
 */
export function SemanticsEdgeGroupCard({
  data,
}: NodeProps<SemanticsEdgeGroupFlowNode>) {
  const { group } = data;
  const tone =
    groupPalette[group.paletteIndex % groupPalette.length] ?? theme.binding;
  const visible = group.edgeNames.slice(0, 2);
  const rest = group.edgeNames.slice(2);

  return (
    <div
      data-testid={`bp-edge-group-${group.edgeNames[0]}`}
      data-edge-count={group.edgeNames.length}
      data-selected={group.highlighted ? "true" : undefined}
      className={cx(
        "ui-node group/edgegroup relative flex w-[248px] flex-col overflow-hidden rounded-[4px] text-left transition-colors",
        group.highlighted ? "ui-node-selected" : "hover:border-line-strong",
      )}
    >
      <span
        aria-hidden
        className="absolute inset-y-0 left-0 z-10 w-[3px]"
        style={{ backgroundColor: tone }}
      />
      <Handle type="target" position={Position.Left} />

      <header className="ui-node-header min-h-[26px] min-w-0 bg-panel-raised px-2.5 py-0.5">
        <span
          aria-hidden
          className="size-1.5 shrink-0 rotate-45"
          style={{ backgroundColor: tone }}
        />
        <p
          className="min-w-0 flex-1 truncate text-[10.5px] font-medium text-text"
          title={`${group.role} · ${group.edgeNames.length} edges`}
        >
          {group.role}
          <span className="text-faint">
            {" "}
            · {group.edgeNames.length} edges
          </span>
        </p>
      </header>

      <div className="min-w-0 px-2.5 py-1">
        <p className="text-[9px] text-faint">relationships</p>
        {visible.map((name) => (
          <p
            key={name}
            data-testid={`bp-edge-${name}`}
            className="truncate font-mono text-[10px] leading-[1.55] text-text"
            title={name}
          >
            {name}
          </p>
        ))}
        {rest.length ? (
          <p className="text-[9px] text-faint">+{rest.length} more</p>
        ) : null}
        {rest.length ? (
          <span className="sr-only">
            {rest.map((name) => (
              <span key={name} data-testid={`bp-edge-${name}`}>
                {name}
              </span>
            ))}
          </span>
        ) : null}
      </div>

      <Handle type="source" position={Position.Right} />
    </div>
  );
}

/**
 * One semantic entity on the blueprint canvas.
 *
 * Blender node-editor shape: the card body stays graphite, a 3px lane stripe
 * owns the identity, property rows are compact list rows and the selected node
 * is outlined in the graph-selection orange. Focus fits this node in the canvas
 * without changing the graph, so a dense blueprint can be inspected one entity
 * at a time.
 */
export function SemanticsNodeCard({ id, data }: NodeProps<SemanticsFlowNode>) {
  const { fitView } = useReactFlow();
  const { entity } = data;
  const selected = entity.highlighted;
  const tone =
    groupPalette[entity.paletteIndex % groupPalette.length] ?? theme.binding;
  const review = entity.actions.find((action) => action.id === "open-review");

  return (
    <div
      data-testid={`bp-node-${entity.name}`}
      data-selected={selected ? "true" : undefined}
      className={cx(
        "ui-node group/node relative flex w-[248px] flex-col overflow-hidden rounded-[4px] text-left transition-colors",
        selected ? "ui-node-selected" : "hover:border-line-strong",
      )}
    >
      <span
        aria-hidden
        className="absolute inset-y-0 left-0 z-10 w-[3px]"
        style={{ backgroundColor: tone }}
      />
      <Handle type="target" position={Position.Left} />

      <header className="ui-node-header min-h-[26px] min-w-0 bg-panel-raised px-2.5 py-0.5">
        <span
          aria-hidden
          className={cx(
            "size-1.5 shrink-0",
            entity.kind === "edge" ? "rotate-45" : "rounded-full",
          )}
          style={{ backgroundColor: tone }}
        />
        <p
          className="min-w-0 flex-1 truncate font-mono text-[10.5px] font-medium tracking-tight text-text"
          title={entity.name}
        >
          {entity.name}
        </p>
        <span className="shrink-0 opacity-0 transition-opacity group-hover/node:opacity-100 group-focus-within/node:opacity-100">
          <AnnotationPopover
            annotations={entity.annotations}
            context={{ kind: entity.kind, component: entity.name }}
            metaGraph={data.metaGraph}
            compact
          />
        </span>
      </header>

      <div className="min-w-0 px-2.5 py-1">
        {entity.labels.length || entity.abstract ? (
          <div className="mb-1 flex flex-wrap gap-1">
            {entity.labels.slice(0, 3).map((label) => (
              <span
                key={label}
                className="ui-chip border-line-soft bg-panel-soft/40 text-[9px] text-muted"
              >
                {label}
              </span>
            ))}
            {entity.abstract ? (
              <span className="ui-chip border-line-soft bg-panel-soft/40 text-[9px] text-faint">
                abstract
              </span>
            ) : null}
          </div>
        ) : null}

        {entity.description ? (
          <p className="line-clamp-1 text-[9px] leading-[1.45] text-muted">
            {entity.description}
          </p>
        ) : null}
      </div>

      <div className="border-t border-line-soft">
        <div className="flex items-baseline justify-between gap-2 px-2.5 py-1">
          <span className="text-[9px] text-faint">Properties</span>
          <span className="font-mono text-[9px] text-faint tabular-nums">
            {entity.propertyCount}
          </span>
        </div>
        <div className="thin-scrollbar nowheel max-h-[150px] overflow-y-auto border-t border-line-soft/60 py-0.5">
          {entity.properties.map((property) => (
            <SemanticsPropertyRow
              key={property.id}
              row={property}
              metaGraph={data.metaGraph}
              variant="node"
            />
          ))}
          {!entity.propertyCount ? (
            <p className="px-2.5 py-1 font-mono text-[9px] text-faint">
              No properties declared.
            </p>
          ) : null}
        </div>
      </div>

      <div className="nodrag mt-auto flex items-center gap-1 border-t border-line-soft bg-panel px-1.5 py-1 opacity-0 transition-opacity group-hover/node:opacity-100 group-focus-within/node:opacity-100">
        <button
          type="button"
          data-testid={`review-entity-${entity.name}`}
          onClick={() => review?.run()}
          disabled={!review}
          className="ui-button ui-button-ghost min-h-[20px] flex-1 px-1 text-[9px]"
          title={
            review
              ? (review.title ?? `Open review for ${entity.kind} ${entity.name}`)
              : "Review surface is not wired in this shell"
          }
        >
          <ShieldQuestion className="size-3" aria-hidden />
          Review
        </button>
        <button
          type="button"
          data-testid={`bp-card-focus-${entity.name}`}
          onClick={() => {
            void fitView({
              nodes: [{ id }],
              duration: 280,
              padding: 0.25,
              maxZoom: 1.15,
            });
          }}
          className="ui-button min-h-[20px] shrink-0 px-1.5 text-[9px]"
          title={`Focus ${entity.kind} ${entity.name} on the canvas`}
        >
          Focus
        </button>
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
