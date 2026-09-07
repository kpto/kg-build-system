"use client";

/**
 * One step, drawn as a compositor node: a title bar in its module's colour, then a
 * body listing every input socket above every output socket, one handle each, with
 * the role name beside it. Below the sockets sit the facts that matter for the kind
 * (declared columns, build keys, `UNION ALL`, `→ graph.jsonl`).
 *
 * The card is `memo`ised and its `data` record is rebuilt only when something it
 * actually shows changes, which is what keeps a 60-node DAG smooth under hover.
 */

import { memo } from "react";
import clsx from "clsx";
import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";

import { Chip, CopyButton, ProblemBadge, RowButton } from "@/components/ui";
import type { Problem } from "@/lib/types";
import type { StepDetail, StepNode } from "./types";
import { TOKEN } from "./tokens";
import { groupSockets } from "./sockets";
import { primaryRole, stepRef } from "./detail";
import { roleColor, roleFamily, ROLE_LABEL } from "./roles";

/** The one place the card width is decided; the layout sizes its columns to it. */
export const STEP_WIDTH = 232;

export interface StepNodeData extends Record<string, unknown> {
  readonly step: StepNode;
  readonly detail: StepDetail;
  readonly laneColor: string;
  readonly selected: boolean;
  readonly dimmed: boolean;
  readonly problems: readonly Problem[];
  readonly onSelect: (ref: string | null) => void;
  readonly onOpenSql: (id: string) => void;
  readonly onHover: (id: string | null) => void;
}

export type StepFlowNode = Node<StepNodeData, "step">;

/** A socket row: the handle on the node's edge, the role name inside the body. */
const SocketRow = memo(function SocketRow({
  socket,
  side,
}: {
  socket: { id: string; label: string; role: string | null };
  side: "in" | "out";
}) {
  const color = side === "out" ? roleColor(socket.role) : TOKEN.lineStrong;
  return (
    <div className="relative flex h-4 items-center">
      <Handle
        id={socket.id}
        type={side === "in" ? "target" : "source"}
        position={side === "in" ? Position.Left : Position.Right}
        className="!h-2 !w-2 !min-h-0 !min-w-0 !rounded-[3px] !border !border-canvas"
        style={{ background: color }}
        title={
          socket.role
            ? `${socket.role} · ${ROLE_LABEL[roleFamily(socket.role)]}`
            : `${socket.label} — whatever feeds this slot`
        }
      />
      <span
        className={clsx(
          "min-w-0 flex-1 truncate font-mono text-[10px] leading-none text-muted",
          side === "in" ? "pl-2" : "pr-2 text-right",
        )}
      >
        {socket.label}
      </span>
    </div>
  );
});

function StepNodeView({ data }: NodeProps<StepFlowNode>) {
  // The ring is the model's answer to "which steps belong to the selected ref",
  // not React Flow's own click-selection: a component's whole chain lights up,
  // including the steps that were not clicked.
  const { step, detail, laneColor, selected, dimmed, problems, onSelect, onOpenSql, onHover } = data;
  const sockets = groupSockets(step);
  const ref = stepRef(step);
  const outputColor = roleColor(primaryRole(step));

  return (
    <div
      data-step-id={step.id}
      onMouseEnter={() => onHover(step.id)}
      onMouseLeave={() => onHover(null)}
      className={clsx(
        "studio-card flex flex-col overflow-hidden transition-opacity duration-100",
        selected && "border-info ring-1 ring-info",
        dimmed && "opacity-20",
      )}
      style={{ width: STEP_WIDTH, borderColor: selected ? undefined : `${laneColor}44` }}
    >
      <header
        className="flex h-[22px] shrink-0 items-center gap-1 px-1.5"
        style={{ background: `${laneColor}26`, borderBottom: `1px solid ${laneColor}44` }}
      >
        <span aria-hidden className="h-2 w-2 shrink-0 rounded-[2px]" style={{ background: laneColor }} />
        <span
          className="min-w-0 flex-1 truncate font-mono text-[11px] font-semibold text-ink"
          title={`${step.kind} · ${step.id}`}
        >
          {step.label}
        </span>
        {problems.length > 0 && <ProblemBadge problems={problems} ref={ref} compact />}
        {detail.hasSql && (
          <button
            type="button"
            className="shrink-0 rounded border border-edge bg-raised px-1 font-mono text-[9px] leading-[14px] text-info hover:border-info hover:text-ink"
            title="Inspect the lowered SQL of this step"
            aria-label={`Show SQL for ${step.label}`}
            onClick={(event) => {
              event.stopPropagation();
              onOpenSql(step.id);
            }}
          >
            {"{ }"}
          </button>
        )}
      </header>

      <div className="flex flex-col gap-1 px-1.5 py-1">
        <div className="flex items-center gap-1">
          <span className="shrink-0 font-mono text-[9px] uppercase tracking-[0.08em] text-faint">
            {detail.kindLabel}
          </span>
          {ref && (
            // The wrapper exists for two reasons. It stops the click, because React
            // Flow's own node click selects the same ref and the two toggles would
            // cancel out. And it carries `nopan`, so a drag starting on the ref
            // selects text instead of sliding the canvas: this canvas never moves a
            // card (`draggable: false` throughout), so the gesture a text-selection
            // drag competes with is the pan. `nodrag` is the same documented
            // convention, applied so the answer holds if cards ever do move.
            <div
              className="nopan nodrag flex min-w-0 flex-1 items-center gap-0.5"
              onClick={(event) => event.stopPropagation()}
            >
              <RowButton
                onActivate={() => onSelect(selected ? null : ref)}
                active={selected}
                title={`${ref} — select this IR ref`}
                // `select-text` because React Flow's stylesheet sets
                // `user-select: none` on `.react-flow__node`, which every child would
                // otherwise inherit: swapping the element alone does not make the ref
                // selectable.
                className="select-text min-w-0 flex-1 truncate text-left font-mono text-[9px] text-faint hover:text-info"
              >
                {ref}
              </RowButton>
              {/* Beside the row, never inside it: `role="button"` owns its descendants.
                  The ref is `truncate`d, so a drag reaches only the visible part —
                  this hands over the whole string. */}
              <CopyButton
                text={ref}
                title="Copy the whole IR ref"
                // Sized into the card's 12 px meta line rather than the kit's 24 px
                // default: node heights are computed before the DOM exists
                // (`sizing.ts`), so a taller row here would overflow its box.
                className="!h-3 !gap-0 !px-1 !text-[8px] !leading-none"
              />
            </div>
          )}
          <span
            aria-hidden
            className="h-1.5 w-1.5 shrink-0 rounded-full"
            style={{ background: outputColor }}
            title={primaryRole(step) ?? "no output role"}
          />
        </div>

        {detail.summary && (
          <p className="truncate text-[10px] leading-[13px] text-muted" title={detail.summary}>
            {detail.summary}
          </p>
        )}

        {(sockets.inputs.length > 0 || sockets.outputs.length > 0) && (
          <div className="flex flex-col gap-0.5 pt-0.5">
            {sockets.inputs.map((socket) => (
              <SocketRow key={socket.id} socket={socket} side="in" />
            ))}
            {sockets.outputs.map((socket) => (
              <SocketRow key={socket.id} socket={socket} side="out" />
            ))}
          </div>
        )}

        {detail.facts.length > 0 && (
          <ul className="flex flex-col border-t border-edge pt-1">
            {detail.facts.slice(0, 3).map((fact) => (
              <li
                key={`${fact.text}:${fact.title ?? ""}`}
                title={fact.title ?? fact.text}
                className={clsx(
                  "truncate font-mono text-[10px] leading-[13px]",
                  fact.tone === "info" && "text-info",
                  fact.tone === "relation" && "text-relation",
                  fact.tone === "template" && "text-template",
                  fact.tone === "warn" && "text-warn",
                  (!fact.tone || fact.tone === "neutral") && "text-faint",
                )}
              >
                {fact.text}
              </li>
            ))}
          </ul>
        )}

        {detail.badges.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {detail.badges.map((badge) => (
              <Chip
                key={`${badge.text}:${badge.title ?? ""}`}
                tone={badge.tone === "info" ? "info" : badge.tone === "relation" ? "relation" : "template"}
                title={badge.title ?? badge.text}
                className="!px-1 !text-[9px]"
              >
                {badge.text}
              </Chip>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export const StepNodeCard = memo(StepNodeView);
