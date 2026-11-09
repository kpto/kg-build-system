"use client";

import { useState } from "react";
import type { Node, NodeProps } from "@xyflow/react";
import { Handle, Position } from "@xyflow/react";
import { Boxes, ChevronRight, ChevronUp, GitBranch, Info } from "lucide-react";
import { StepDetailPopover } from "@/diagnosis/execution/view/StepDetailPopover";
import type {
  ArtifactSocket,
  WorkflowStepDetailData,
} from "@/diagnosis/execution/view/StepDetailPopover";
import { cx, severityColor, groupPalette, theme } from "@/shared/ui/theme";
import type { Severity } from "@/lib/reviewTypes";
import type { StepId } from "@/lib/types";

export type WorkflowTraceState = "focus" | "path" | "dim";

export interface WorkflowStepNodeData extends Record<string, unknown> {
  label: string;
  component: string;
  emitter: string;
  artifacts: string[];
  stepId: StepId;
  selected: boolean;
  onSelect: (id: StepId) => void;
  inputSockets: ArtifactSocket[];
  outputSockets: ArtifactSocket[];
  auditCount: number;
  auditSeverity?: Severity;
  detail: WorkflowStepDetailData;
  traceState?: WorkflowTraceState;
  subjectMatched?: boolean;
}

export interface WorkflowGroupNodeData extends Record<string, unknown> {
  key: string;
  label: string;
  count: number;
  collapsed: boolean;
  onToggle: () => void;
  auditCount: number;
  auditSeverity?: Severity;
  traceState?: WorkflowTraceState;
}

export interface WorkflowGroupFrameNodeData extends Record<string, unknown> {
  key: string;
  label: string;
  count: number;
  auditCount: number;
  auditSeverity?: Severity;
  focused: boolean;
  lockedOpen?: boolean;
  onToggle: () => void;
  traceState?: WorkflowTraceState;
}

export type WorkflowStepFlowNode = Node<WorkflowStepNodeData, "workflowStep">;
export type WorkflowGroupFlowNode = Node<WorkflowGroupNodeData, "workflowGroup">;
export type WorkflowGroupFrameFlowNode = Node<
  WorkflowGroupFrameNodeData,
  "workflowGroupFrame"
>;

function AuditBadge({
  count,
  severity,
  showZero = false,
}: {
  count: number;
  severity?: Severity;
  showZero?: boolean;
}) {
  if (count <= 0 && !showZero) return null;
  return (
    <span
      title={`${count} audit finding${count === 1 ? "" : "s"}${severity ? ` · highest ${severity}` : ""}`}
      className="inline-flex shrink-0 items-center gap-1 font-mono text-[9px] text-muted tabular-nums"
    >
      <span
        className="size-1.5 rounded-full"
        style={{
          backgroundColor: severity
            ? severityColor[severity]
            : count > 0
              ? theme.faint
              : theme.lineSoft,
        }}
      />
      {count}
    </span>
  );
}

function socketTitle(sockets: ArtifactSocket[], fallback: string): string {
  if (!sockets.length) return fallback;
  return sockets.map((socket) => socket.title).join("\n");
}

/**
 * Stable header tone for an instruction or component key. The node header is
 * the only place colour appears; the body stays graphite.
 */
function categoryTone(key: string): string {
  let hash = 0;
  for (let index = 0; index < key.length; index += 1) {
    hash = (hash * 31 + key.charCodeAt(index)) >>> 0;
  }
  return groupPalette[hash % groupPalette.length];
}

export function WorkflowStepNode({ data }: NodeProps<WorkflowStepFlowNode>) {
  const [hovered, setHovered] = useState(false);
  const [pinned, setPinned] = useState(false);
  const showDetail = hovered || pinned;
  const traceState = data.traceState;
  const input = data.inputSockets[0];
  const output = data.outputSockets[0];
  const headerColor = categoryTone(data.emitter || data.component);
  const selected = data.selected;
  const focus = traceState === "focus";
  const path = traceState === "path";
  const borderColor = selected
    ? theme.selection
    : focus
      ? theme.accent
      : path
        ? `color-mix(in srgb, ${theme.selection} 42%, ${theme.line})`
        : data.subjectMatched
          ? theme.asset
          : hovered
            ? theme.accent
            : theme.line;
  const glow = selected
    ? `0 0 0 1px ${theme.selectionSoft}, 0 0 8px color-mix(in srgb, ${theme.selection} 24%, transparent)`
    : focus
      ? `0 0 0 1px ${theme.accentSoft}, 0 0 8px color-mix(in srgb, ${theme.accent} 24%, transparent)`
      : undefined;

  return (
    <div
      data-testid={`step-${data.component}-${data.label}`}
      data-level="canvas-item"
      role="button"
      tabIndex={0}
      aria-pressed={data.selected}
      aria-label={`Select step ${data.component}/${data.label}`}
      className={cx(
        "ui-node group relative flex h-[112px] w-[232px] cursor-pointer flex-col overflow-visible text-left transition-[border-color,box-shadow] duration-150",
        traceState === "dim" && "opacity-25",
      )}
      style={{ borderColor, boxShadow: glow }}
      onClick={() => data.onSelect(data.stepId)}
      onKeyDown={(event) => {
        if (event.target !== event.currentTarget) return;
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          data.onSelect(data.stepId);
        }
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!size-[7px] !border-abyss"
        style={{ background: theme.muted }}
      />
      <div className="relative flex h-[24px] shrink-0 items-center gap-1 overflow-hidden rounded-t-[3px] border-b border-line-soft bg-panel-raised px-2">
        <span
          aria-hidden
          className="absolute inset-y-0 left-0 w-[3px]"
          style={{ backgroundColor: headerColor }}
        />
        <p className="min-w-0 flex-1 truncate pl-1 text-[10.5px] leading-none font-semibold tracking-tight text-text">
          {data.label}
        </p>
        <AuditBadge count={data.auditCount} severity={data.auditSeverity} />
        <button
          type="button"
          data-testid="step-info"
          aria-label={`Step details for ${data.component}/${data.label}`}
          onClick={(event) => {
            event.stopPropagation();
            setPinned((value) => !value);
          }}
          className="nodrag inline-flex size-4 shrink-0 cursor-pointer items-center justify-center rounded-[2px] text-faint opacity-0 transition-all group-hover:opacity-100 group-focus-within:opacity-100 hover:bg-panel-soft hover:text-text focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent-strong/70"
        >
          <Info className="size-2.5" aria-hidden />
        </button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-0.5 px-2 py-1">
        <div className="flex min-w-0 items-center gap-1.5">
          <span className="min-w-0 flex-1 truncate font-mono text-[9px] text-muted">
            {data.component}
          </span>
          <span
            className="max-w-[46%] min-w-0 shrink-0 truncate rounded-[2px] bg-panel-soft px-1 py-0.5 font-mono text-[9px] text-ink-soft"
            title={`Instruction kind: ${data.emitter}`}
          >
            {data.emitter}
          </span>
        </div>

        {data.artifacts.length ? (
          <div
            className="flex min-w-0 items-center gap-1"
            title={data.artifacts.join("\n")}
          >
            <span className="shrink-0 text-[9px] text-faint">out</span>
            <span className="min-w-0 truncate font-mono text-[9px] text-source">
              {data.artifacts[0]}
            </span>
            {data.artifacts.length > 1 ? (
              <span className="shrink-0 font-mono text-[9px] text-faint">
                +{data.artifacts.length - 1}
              </span>
            ) : null}
          </div>
        ) : null}

        <div className="mt-auto flex min-w-0 items-center justify-between gap-1 border-t border-line-soft pt-1 font-mono text-[9px] text-muted">
          <span
            className="inline-flex min-w-0 items-center gap-1"
            title={socketTitle(data.inputSockets, "no input sockets")}
          >
            <span className="ui-socket !size-[7px]" />
            <span className="truncate">{input?.label ?? "\u2014"}</span>
          </span>
          <span className="shrink-0 px-0.5 text-faint" aria-hidden>
            &rarr;
          </span>
          <span
            className="inline-flex min-w-0 items-center justify-end gap-1 text-right"
            title={socketTitle(data.outputSockets, "no output sockets")}
          >
            <span className="truncate">{output?.label ?? "\u2014"}</span>
            <span className="ui-socket !size-[7px] bg-source" />
          </span>
        </div>

        <div className="flex items-center gap-1">
          <button
            type="button"
            data-testid="trace-step"
            onClick={(event) => {
              event.stopPropagation();
              data.detail.onTrace?.();
            }}
            className="nodrag inline-flex flex-1 cursor-pointer items-center justify-center gap-1 rounded-[2px] border border-accent/40 bg-accent/10 px-1 py-0.5 text-[9px] font-medium text-accent-strong transition-colors hover:border-accent/70 hover:bg-accent/20 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent/70"
          >
            <GitBranch className="size-2.5" aria-hidden />
            trace
          </button>
          <button
            type="button"
            data-testid="review-step"
            onClick={(event) => {
              event.stopPropagation();
              data.detail.onReview?.();
            }}
            className="nodrag inline-flex flex-1 cursor-pointer items-center justify-center rounded-[2px] border border-line bg-panel-soft px-1 py-0.5 text-[9px] font-medium text-muted opacity-0 transition-all group-hover:opacity-100 group-focus-within:opacity-100 hover:border-accent/50 hover:text-accent focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent/70"
          >
            review
          </button>
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="!size-[7px] !border-abyss"
        style={{ background: theme.source }}
      />
      {showDetail ? <StepDetailPopover data={data.detail} /> : null}
    </div>
  );
}

export function WorkflowGroupNode({ data }: NodeProps<WorkflowGroupFlowNode>) {
  return (
    <div
      data-level="canvas-item"
      role="group"
      aria-label={`${data.label} group, ${data.count} steps, collapsed`}
      onClick={data.onToggle}
      className={cx(
        "ui-node relative flex h-[64px] w-[224px] cursor-pointer flex-col text-left transition-[border-color,background-color] duration-150 hover:border-accent/60",
        data.traceState === "dim" && "opacity-25",
      )}
      title={`Expand ${data.label}`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!size-[7px] !border-abyss"
        style={{ background: theme.muted }}
      />
      <div className="relative flex h-[24px] shrink-0 items-center gap-1 overflow-hidden rounded-t-[3px] border-b border-line-soft bg-panel-raised px-2">
        <span
          aria-hidden
          className="absolute inset-y-0 left-0 w-[3px] bg-accent"
        />
        <Boxes className="size-3 shrink-0 text-muted" aria-hidden />
        <p className="min-w-0 flex-1 truncate text-[10.5px] leading-none font-semibold tracking-tight text-text">
          {data.label}
        </p>
        <AuditBadge
          count={data.auditCount}
          severity={data.auditSeverity}
          showZero
        />
      </div>
      <div className="flex min-h-0 flex-1 items-center gap-1.5 px-2 py-1">
        <span className="truncate font-mono text-[9px] text-muted tabular-nums">
          {data.count} steps
        </span>
        <span className="shrink-0 text-[9px] text-faint">collapsed</span>
        <button
          type="button"
          data-testid={`expand-group-${data.key}`}
          aria-expanded={false}
          aria-label={`Expand ${data.label}`}
          onClick={(event) => {
            event.stopPropagation();
            data.onToggle();
          }}
          className="nodrag ml-auto inline-flex h-5 shrink-0 cursor-pointer items-center gap-1 rounded-[2px] border border-accent/50 bg-accent/10 px-1.5 text-[9px] font-medium text-accent-strong transition-colors hover:border-accent/80 hover:bg-accent/20 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent/70"
        >
          <ChevronRight className="size-2.5" aria-hidden />
          expand
        </button>
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="!size-[7px] !border-abyss"
        style={{ background: theme.accent }}
      />
    </div>
  );
}

export function WorkflowGroupFrameNode({
  data,
}: NodeProps<WorkflowGroupFrameFlowNode>) {
  return (
    <div
      data-level="canvas-item"
      role="group"
      aria-label={`${data.label} group, ${data.count} steps, expanded`}
      data-group-key={data.key}
      className={cx(
        "pointer-events-none relative h-full w-full overflow-hidden rounded-[4px] border border-dashed shadow-none transition-colors duration-150",
        data.focused
          ? "border-accent/60 bg-accent/[0.04]"
          : "border-line-strong/70 bg-panel/20",
        data.traceState === "dim" && "opacity-20",
      )}
    >
      <div
        data-testid={`group-frame-${data.key}`}
        className={cx(
          "pointer-events-none absolute inset-x-0 top-0 flex h-[26px] items-center gap-1.5 border-b px-2",
          data.focused
            ? "border-accent/35 bg-accent/10"
            : "border-line-soft bg-panel-raised/85",
        )}
      >
        <span
          aria-hidden
          className={cx(
            "h-3 w-[2px] shrink-0 rounded-full",
            data.focused ? "bg-accent" : "bg-accent/55",
          )}
        />
        <span className="min-w-0 truncate text-[10px] font-semibold text-ink-soft">
          {data.label}
        </span>
        <span className="shrink-0 font-mono text-[9px] text-muted tabular-nums">
          {data.count} steps
        </span>
        <span className="shrink-0 text-[9px] text-line" aria-hidden>
          /
        </span>
        <AuditBadge
          count={data.auditCount}
          severity={data.auditSeverity}
          showZero
        />
        {data.focused ? (
          <span className="inline-flex shrink-0 items-center gap-1 text-[9px] text-accent-strong">
            <span className="size-1.5 rounded-full bg-accent-strong" aria-hidden />
            focused
          </span>
        ) : null}
        <button
          type="button"
          data-testid={`collapse-group-${data.key}`}
          aria-expanded={true}
          aria-label={`Collapse ${data.label}`}
          disabled={data.lockedOpen}
          title={
            data.lockedOpen
              ? "Clear the trace to collapse this group"
              : `Collapse ${data.label}`
          }
          onClick={(event) => {
            event.stopPropagation();
            data.onToggle();
          }}
          className="nodrag pointer-events-auto ml-auto inline-flex h-5 shrink-0 cursor-pointer items-center gap-1 rounded-[2px] border border-accent/40 bg-accent/10 px-1.5 text-[9px] font-medium text-accent-strong transition-colors hover:border-accent/75 hover:bg-accent/20 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent/70 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ChevronUp className="size-2.5" aria-hidden />
          collapse
        </button>
      </div>
    </div>
  );
}
