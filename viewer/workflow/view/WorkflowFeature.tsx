"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type MouseEvent as ReactMouseEvent,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  RotateCcw,
  Search,
} from "lucide-react";

import type {
  NormalizedConnection,
  StepId,
  ViewerIndex,
  WorkflowStep,
} from "@/lib/types";
import { stepKey } from "@/lib/indexes";
import { DetailDocument, DetailPanel } from "@/detail/view/DetailChrome";
import { ContextMenu } from "@/shared/ui/ContextMenu";
import { cx, groupPalette, theme } from "@/shared/ui/theme";
import { activeDocument, type WorkspaceProps } from "@/workbench/types";
import {
  buildWorkflowComponentMap,
  buildWorkflowModel,
  filterWorkflowRows,
  formatArtifactType,
  formatOpening,
  formatStepId,
  type WorkflowComponentNode,
  type WorkflowStepRow,
} from "@/workflow/model/WorkflowViewModel";
import { useWorkflowUi } from "./workflowUi";

function workflowModel(state: WorkspaceProps["state"]) {
  return buildWorkflowModel(state.index);
}

// ---------------------------------------------------------------------------
// Control: workflow filters
// ---------------------------------------------------------------------------

export function WorkflowControls({ state }: WorkspaceProps) {
  const model = useMemo(() => workflowModel(state), [state.index]);
  const { state: ui, store } = useWorkflowUi(state.snapshot.name);
  const rows = useMemo(
    () => filterWorkflowRows(model.rows, ui.filters),
    [model.rows, ui.filters],
  );

  return (
    <div className="flex h-full flex-col" data-testid="workflow-controls">
      <div className="flex flex-none items-center gap-1.5 border-b border-line-soft p-2">
        <Search aria-hidden className="size-3 text-faint" />
        <input
          value={ui.filters.query}
          onChange={(event) => store.setQuery(event.target.value)}
          placeholder="Filter workflow steps"
          aria-label="Filter workflow steps"
          spellCheck={false}
          className="h-6 min-w-0 flex-1 border border-line bg-inset px-1.5 font-mono text-[10px] text-text outline-none placeholder:text-faint focus:border-selection"
          data-testid="workflow-filter-query"
        />
      </div>

      <div className="thin-scrollbar min-h-0 flex-1 space-y-3 overflow-y-auto p-2">
        <label className="block">
          <span className="mb-1 block text-[9px] font-semibold tracking-[0.08em] text-faint uppercase">
            Component
          </span>
          <select
            value={ui.filters.component}
            onChange={(event) => store.setComponent(event.target.value)}
            className="h-6 w-full border border-line bg-inset px-1 font-mono text-[10px] text-text outline-none focus:border-selection"
            data-testid="workflow-filter-component"
          >
            <option value="all">All components · {model.components.length}</option>
            {model.components.map((component) => (
              <option key={component} value={component}>
                {component}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="mb-1 block text-[9px] font-semibold tracking-[0.08em] text-faint uppercase">
            Instruction
          </span>
          <select
            value={ui.filters.kind}
            onChange={(event) => store.setKind(event.target.value)}
            className="h-6 w-full border border-line bg-inset px-1 font-mono text-[10px] text-text outline-none focus:border-selection"
            data-testid="workflow-filter-kind"
          >
            <option value="all">All instruction kinds</option>
            {model.kinds.map((kind) => (
              <option key={kind.key} value={kind.key}>
                {kind.label} · {kind.count}
              </option>
            ))}
          </select>
        </label>

        <div className="flex items-center justify-between border-t border-line-soft pt-2 font-mono text-[9px] text-faint">
          <span>
            {rows.length} / {model.steps} steps
          </span>
          <span>{model.connections} connections</span>
        </div>

        <p className="text-[9px] leading-relaxed text-faint">
          Choosing a component selects it. Use Open step group in the canvas
          toolbar to enter its step graph. Filters narrow that graph and dim the
          component overview; every step remains available in Explorer.
        </p>

        <button
          type="button"
          onClick={() => store.resetFilters()}
          className="flex w-full items-center justify-center gap-1.5 border border-line-soft px-2 py-1 font-mono text-[9px] text-muted hover:border-line-strong hover:text-text"
          data-testid="workflow-reset"
        >
          <RotateCcw aria-hidden className="size-3" />
          Reset workflow filters
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step detail document
// ---------------------------------------------------------------------------

function Fact({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="flex min-w-0 items-baseline gap-2">
      <span className="w-24 shrink-0 text-[8.5px] font-semibold tracking-[0.07em] text-faint uppercase">
        {label}
      </span>
      <span className="min-w-0 flex-1 truncate font-mono text-[10px] text-text">
        {children}
      </span>
    </div>
  );
}

function scalar(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value || "—";
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return "";
}

function PayloadFacts({ step }: { step: WorkflowStep }) {
  const entries = Object.entries(step.instruction.payload ?? {});
  if (!entries.length) {
    return (
      <p className="text-[10px] text-faint">
        This instruction carries no payload.
      </p>
    );
  }
  return (
    <div className="grid gap-1" data-testid="workflow-payload">
      {entries.map(([key, value]) => {
        const text = scalar(value);
        if (text) {
          return (
            <div key={key} className="flex items-baseline gap-2">
              <span className="w-40 shrink-0 truncate font-mono text-[9px] text-faint">
                {key}
              </span>
              <span
                className="min-w-0 flex-1 truncate font-mono text-[10px] text-text"
                title={text}
              >
                {text}
              </span>
            </div>
          );
        }
        const label = Array.isArray(value)
          ? `array · ${value.length}`
          : typeof value === "object"
            ? "object"
            : String(value);
        return (
          <details key={key} className="group rounded border border-line-soft">
            <summary className="flex cursor-pointer list-none items-baseline gap-2 px-1.5 py-1 hover:bg-panel-soft/50">
              <span className="w-40 shrink-0 truncate font-mono text-[9px] text-faint">
                {key}
              </span>
              <span className="min-w-0 flex-1 truncate font-mono text-[10px] text-muted">
                {label}
              </span>
            </summary>
            <pre className="thin-scrollbar max-h-56 overflow-auto border-t border-line-soft bg-inset p-2 font-mono text-[9px] leading-relaxed text-muted">
              {JSON.stringify(value, null, 2)}
            </pre>
          </details>
        );
      })}
    </div>
  );
}

function Openings({
  step,
  direction,
}: {
  step: WorkflowStep;
  direction: "input" | "output";
}) {
  const items = direction === "input" ? step.inputs ?? [] : step.outputs ?? [];
  if (!items.length) {
    return (
      <p className="text-[10px] text-faint">No {direction}s are declared.</p>
    );
  }
  return (
    <div className="grid gap-1" data-testid={`workflow-${direction}s`}>
      {items.map((item, index) => (
        <div
          key={`${direction}:${index}:${formatOpening(item.opening_name)}`}
          className="flex min-w-0 items-baseline gap-2"
        >
          <span className="w-40 shrink-0 truncate font-mono text-[9px] text-muted">
            {formatOpening(item.opening_name)}
          </span>
          <span className="min-w-0 flex-1 truncate font-mono text-[9.5px] text-text">
            {formatArtifactType(item.type)}
          </span>
        </div>
      ))}
    </div>
  );
}

function ConnectionLine({
  connection,
  direction,
}: {
  connection: NormalizedConnection;
  direction: "in" | "out";
}) {
  const other =
    direction === "in" ? connection.outputStepId : connection.inputStepId;
  const local = direction === "in" ? connection.input : connection.output;
  const remote = direction === "in" ? connection.output : connection.input;
  const Icon = direction === "in" ? ArrowDownLeft : ArrowUpRight;
  return (
    <div
      className="flex min-w-0 items-baseline gap-2 border-b border-line-soft/50 py-1 last:border-b-0"
      data-testid="workflow-connection"
    >
      <Icon
        aria-hidden
        className={cx(
          "size-3 shrink-0",
          direction === "in" ? "text-source" : "text-target",
        )}
      />
      <span className="min-w-0 flex-1 truncate font-mono text-[9.5px] text-text">
        {formatStepId(other)}
      </span>
      <span className="min-w-0 max-w-[42%] shrink-0 truncate font-mono text-[8.5px] text-faint">
        {formatOpening(remote.opening)} → {formatOpening(local.opening)}
      </span>
    </div>
  );
}

function DetailSubhead({ children }: { children: ReactNode }) {
  return (
    <h3 className="mb-1.5 text-[9px] font-semibold tracking-[0.08em] text-faint uppercase">
      {children}
    </h3>
  );
}

function StepDetail({
  index,
  step,
}: {
  index: ViewerIndex;
  step: WorkflowStep;
}) {
  const key = stepKey(step.id);
  const incoming = index.incomingByStepId.get(key) ?? [];
  const outgoing = index.outgoingByStepId.get(key) ?? [];
  const bindings = index.bindings.filter(
    (binding) => binding.step && stepKey(binding.step.id) === key,
  );

  return (
    <DetailDocument
      testId="workflow-step-detail"
      kind="step"
      kicker={`Design · step · ${step.id[0]}`}
      title={step.id[1]}
      subtitle={`${step.instruction.kind?.join(":") ?? "unknown"} · ${
        step.inputs?.length ?? 0
      } inputs · ${step.outputs?.length ?? 0} outputs · ${incoming.length} in / ${
        outgoing.length
      } out`}
    >
      <div className="flex flex-col gap-[11px]">
        <DetailPanel title="Identity" meta={formatStepId(step.id)}>
          <div className="grid grid-cols-2 gap-x-6 gap-y-1">
            <Fact label="Step id">{formatStepId(step.id)}</Fact>
            <Fact label="Component">{step.id[0]}</Fact>
            <Fact label="Instruction">
              {step.instruction.kind?.join(":") ?? "unknown"}
            </Fact>
            <Fact label="Bindings">{bindings.length}</Fact>
          </div>
        </DetailPanel>

        <DetailPanel title="Inputs" meta={`${step.inputs?.length ?? 0}`}>
          <Openings step={step} direction="input" />
        </DetailPanel>

        <DetailPanel title="Outputs" meta={`${step.outputs?.length ?? 0}`}>
          <Openings step={step} direction="output" />
        </DetailPanel>

        <DetailPanel
          title="Instruction payload"
          meta={`${Object.keys(step.instruction.payload ?? {}).length} fields`}
        >
          <PayloadFacts step={step} />
        </DetailPanel>

        <DetailPanel
          title="Connections"
          meta={`${incoming.length} in · ${outgoing.length} out`}
        >
          <div className="grid gap-3 xl:grid-cols-2">
            <div>
              <DetailSubhead>Incoming · {incoming.length}</DetailSubhead>
              {incoming.length ? (
                <div className="rounded border border-line-soft bg-panel px-2">
                  {incoming.slice(0, 24).map((connection) => (
                    <ConnectionLine
                      key={connection.id}
                      connection={connection}
                      direction="in"
                    />
                  ))}
                  {incoming.length > 24 ? (
                    <p className="py-1 font-mono text-[8.5px] text-faint">
                      showing 24 of {incoming.length}
                    </p>
                  ) : null}
                </div>
              ) : (
                <p className="text-[10px] text-faint">
                  This step has no inputs.
                </p>
              )}
            </div>
            <div>
              <DetailSubhead>Outgoing · {outgoing.length}</DetailSubhead>
              {outgoing.length ? (
                <div className="rounded border border-line-soft bg-panel px-2">
                  {outgoing.slice(0, 24).map((connection) => (
                    <ConnectionLine
                      key={connection.id}
                      connection={connection}
                      direction="out"
                    />
                  ))}
                  {outgoing.length > 24 ? (
                    <p className="py-1 font-mono text-[8.5px] text-faint">
                      showing 24 of {outgoing.length}
                    </p>
                  ) : null}
                </div>
              ) : (
                <p className="text-[10px] text-faint">
                  This step has no outputs.
                </p>
              )}
            </div>
          </div>
        </DetailPanel>

        {bindings.length ? (
          <DetailPanel title="Blueprint bindings" meta={`${bindings.length}`}>
            <div className="grid gap-1">
              {bindings.slice(0, 16).map((binding) => (
                <div
                  key={binding.index}
                  className="flex items-baseline gap-2 font-mono text-[9.5px]"
                >
                  <span className="w-12 shrink-0 text-faint">
                    #{binding.index}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-text">
                    {binding.component}
                  </span>
                  <span className="shrink-0 text-faint">
                    {binding.binding.debug_name ?? binding.kind}
                  </span>
                </div>
              ))}
              {bindings.length > 16 ? (
                <p className="font-mono text-[8.5px] text-faint">
                  showing 16 of {bindings.length}
                </p>
              ) : null}
            </div>
          </DetailPanel>
        ) : null}
      </div>
    </DetailDocument>
  );
}

export function WorkflowStepEditor({ state }: WorkspaceProps) {
  const document = activeDocument(state);
  const selection =
    document.kind === "subject" ? document.selection : undefined;
  const stepId: StepId | undefined = selection?.stepId
    ? selection.stepId
    : selection?.component && selection.name
      ? [selection.component, selection.name]
      : undefined;
  const step = stepId ? state.index.stepsById.get(stepKey(stepId)) : undefined;

  if (!step) {
    return (
      <DetailDocument
        testId="workflow-step-editor"
        kind="step"
        kicker="Design · step"
        title="Step unavailable"
        subtitle="This step is not present in the workflow plan."
      >
        <DetailPanel title="Step">
          <p className="text-[10.5px] leading-relaxed text-faint">
            The selected workflow step could not be resolved from the snapshot.
          </p>
        </DetailPanel>
      </DetailDocument>
    );
  }

  return (
    <div className="min-h-full" data-testid="workflow-step-editor">
      <StepDetail index={state.index} step={step} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Workflow document: component map
// ---------------------------------------------------------------------------

const NODE_WIDTH = 208;
const NODE_HEIGHT = 140;
const HEADER_HEIGHT = 28;
const COLUMN_GAP = 68;
const ROW_GAP = 56;
const MARGIN = 36;
const SOCKET_Y = 50;

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
interface WorkflowGraphNode {
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
interface WorkflowGraphEdge {
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

interface WorkflowGraphScene {
  nodes: WorkflowGraphNode[];
  edges: WorkflowGraphEdge[];
  width: number;
  height: number;
  stats?: WorkflowGraphStats;
}

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

function buildCompositorScene(
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

function buildStepScene(
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
      tint: tintFor(component),
      x: gridX + column * (STEP_NODE_WIDTH + STEP_GAP_X),
      y: gridY + line * (STEP_NODE_HEIGHT + STEP_GAP_Y),
      width: STEP_NODE_WIDTH,
      height: STEP_NODE_HEIGHT,
      headerHeight: STEP_HEADER_HEIGHT,
      socketY: STEP_NODE_HEIGHT / 2,
      dataTestId: "workflow-step-node",
      row,
      component,
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

function WorkflowGraphSceneView({
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
  onContextMenu(node: WorkflowGraphNode, event: ReactMouseEvent<SVGGElement>): void;
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
              onContextMenu={(event) => {
                event.preventDefault();
                event.stopPropagation();
                onContextMenu(node, event);
              }}
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

export function WorkflowEditor(props: WorkspaceProps) {
  const model = useMemo(() => workflowModel(props.state), [props.state.index]);
  const componentMap = useMemo(
    () => buildWorkflowComponentMap(props.state.index, model),
    [props.state.index, model],
  );
  const componentScene = useMemo(() => buildCompositorScene(componentMap), [componentMap]);
  const { state: ui, store } = useWorkflowUi(props.state.snapshot.name);
  const filtered = useMemo(
    () => filterWorkflowRows(model.rows, ui.filters),
    [model.rows, ui.filters],
  );
  const activeComponents = useMemo(
    () => new Set(filtered.map((row) => row.component)),
    [filtered],
  );
  const filtering =
    Boolean(ui.filters.query.trim()) ||
    ui.filters.component !== "all" ||
    ui.filters.kind !== "all";
  const selectedNode =
    ui.filters.component === "all"
      ? undefined
      : componentMap.nodes.find((node) => node.id === ui.filters.component);
  const focusedNode = ui.focusedComponent
    ? componentMap.nodes.find((node) => node.id === ui.focusedComponent)
    : undefined;
  const focusedGroupRows = focusedNode
    ? filtered.filter((row) => row.component === focusedNode.id)
    : [];
  const selectedStepRow = ui.selectedNodeKey
    ? focusedGroupRows.find((row) => row.key === ui.selectedNodeKey)
    : undefined;
  const tintByComponent = useMemo(
    () =>
      new Map(
        componentMap.nodes.map((node, index) => [
          node.id,
          groupPalette[index % groupPalette.length],
        ]),
      ),
    [componentMap.nodes],
  );
  const tintFor = useCallback(
    (component: string) => tintByComponent.get(component) ?? theme.edge,
    [tintByComponent],
  );
  const stepScene = useMemo(
    () =>
      focusedNode
        ? buildStepScene(
            props.state.index,
            focusedNode.id,
            focusedGroupRows,
            tintFor,
          )
        : undefined,
    [props.state.index, focusedNode, focusedGroupRows, tintFor],
  );
  const selectedBoundaryNode = ui.selectedNodeKey
    ? stepScene?.nodes.find(
        (node) => node.id === ui.selectedNodeKey && node.kind !== "step",
      )
    : undefined;
  const activeScene = stepScene ?? componentScene;
  const inStepGroup = Boolean(stepScene && focusedNode);

  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });
  const [view, setView] = useState({ scale: 1, x: 0, y: 0 });
  const dragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    x: number;
    y: number;
    moved: boolean;
  } | null>(null);
  const suppressClickRef = useRef(false);
  const cleanupDragRef = useRef<(() => void) | null>(null);
  const [menu, setMenu] = useState<
    | {
        x: number;
        y: number;
        label: string;
        items: Array<{ label: string; hint?: string; run(): void }>;
      }
    | undefined
  >(undefined);

  useEffect(() => {
    return () => cleanupDragRef.current?.();
  }, []);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      setSize({
        width: entry.contentRect.width,
        height: entry.contentRect.height,
      });
    });
    observer.observe(element);
    setSize({ width: element.clientWidth, height: element.clientHeight });
    return () => observer.disconnect();
  }, [activeScene.nodes.length]);

  const fitView = useCallback(() => {
    if (
      !size.width ||
      !size.height ||
      !activeScene.width ||
      !activeScene.height
    ) {
      return;
    }
    const pad = 30;
    const scale = Math.max(
      0.12,
      Math.min(
        1.4,
        Math.min(
          (size.width - pad * 2) / activeScene.width,
          (size.height - pad * 2) / activeScene.height,
        ),
      ),
    );
    setView({
      scale,
      x: (size.width - activeScene.width * scale) / 2,
      y: (size.height - activeScene.height * scale) / 2,
    });
  }, [size.width, size.height, activeScene.width, activeScene.height]);

  useEffect(() => {
    fitView();
  }, [fitView]);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      const rect = element.getBoundingClientRect();
      const px = event.clientX - rect.left;
      const py = event.clientY - rect.top;
      setView((current) => {
        const next = Math.max(
          0.15,
          Math.min(3, current.scale * Math.exp(-event.deltaY * 0.0015)),
        );
        const ratio = next / current.scale;
        return {
          scale: next,
          x: px - ratio * (px - current.x),
          y: py - ratio * (py - current.y),
        };
      });
    };
    element.addEventListener("wheel", onWheel, { passive: false });
    return () => element.removeEventListener("wheel", onWheel);
  }, [activeScene.nodes.length]);

  const zoomBy = (factor: number) => {
    setView((current) => {
      const next = Math.max(0.15, Math.min(3, current.scale * factor));
      const ratio = next / current.scale;
      const px = size.width / 2;
      const py = size.height / 2;
      return {
        scale: next,
        x: px - ratio * (px - current.x),
        y: py - ratio * (py - current.y),
      };
    });
  };

  const endDrag = () => {
    const drag = dragRef.current;
    if (!drag) return;
    dragRef.current = null;
    cleanupDragRef.current?.();
    cleanupDragRef.current = null;
    if (drag.moved) {
      suppressClickRef.current = true;
      window.setTimeout(() => {
        suppressClickRef.current = false;
      }, 0);
    }
  };

  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    if (dragRef.current) endDrag();
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      x: view.x,
      y: view.y,
      moved: false,
    };
    suppressClickRef.current = false;

    const onMove = (move: PointerEvent) => {
      const drag = dragRef.current;
      if (!drag || drag.pointerId !== move.pointerId) return;
      const dx = move.clientX - drag.startX;
      const dy = move.clientY - drag.startY;
      if (!drag.moved) {
        if (Math.abs(dx) <= 3 && Math.abs(dy) <= 3) return;
        drag.moved = true;
      }
      setView((current) => ({ ...current, x: drag.x + dx, y: drag.y + dy }));
    };
    const onUp = () => endDrag();

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp, { once: true });
    window.addEventListener("pointercancel", onUp, { once: true });
    cleanupDragRef.current = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
    };
  };

  const openStepNode = (row: WorkflowStepRow, preview: boolean) => {
    props.actions.openTab({
      selection: {
        kind: "step",
        component: row.component,
        name: row.name,
        stepId: row.id,
      },
      preview,
    });
  };

  if (!componentScene.nodes.length) {
    return (
      <div
        className="flex h-full items-center justify-center p-6"
        data-testid="workflow-editor"
      >
        <p className="max-w-[42ch] text-center text-[11px] leading-relaxed text-muted">
          This snapshot has no workflow plan.
        </p>
      </div>
    );
  }

  return (
    <div
      className="relative flex h-full min-h-0 flex-col bg-abyss"
      data-testid="workflow-editor"
    >
      <div
        ref={containerRef}
        className="relative min-h-0 flex-1 cursor-grab touch-none overflow-hidden select-none"
        data-testid="workflow-canvas"
        onPointerDown={onPointerDown}
        onContextMenu={(event) => {
          event.preventDefault();
          setMenu({
            x: event.clientX,
            y: event.clientY,
            label: inStepGroup
              ? (focusedNode?.id ?? "Step group")
              : "Workflow graph",
            items: inStepGroup
              ? [
                  {
                    label: "Back to components",
                    hint: "Workflow",
                    run: () => store.focusComponent(undefined),
                  },
                  {
                    label: "Fit graph",
                    hint: "Reset view",
                    run: fitView,
                  },
                ]
              : [
                  {
                    label: "Show all components",
                    hint: "Reset filters",
                    run: () => store.resetFilters(),
                  },
                  {
                    label: "Fit graph",
                    hint: "Reset view",
                    run: fitView,
                  },
                ],
          });
        }}
      >
        <div
          className="absolute top-3 right-3 z-20 flex max-w-[65%] flex-wrap items-center justify-end gap-1.5"
          data-testid="workflow-toolbar"
          onPointerDown={(event) => event.stopPropagation()}
          onPointerMove={(event) => event.stopPropagation()}
          onPointerUp={(event) => event.stopPropagation()}
        >
          {inStepGroup && stepScene ? (
            <>
              <span
                className="rounded border border-line-soft bg-panel/95 px-2 py-1 font-mono text-[9px] text-faint"
                data-testid="workflow-step-group-label"
              >
                {focusedNode?.id ?? "Step group"} ·{" "}
                {stepScene.stats?.stepCount ?? 0} steps ·{" "}
                {stepScene.stats?.boundaryCount ?? 0} boundary
              </span>
              {selectedStepRow ? (
                <button
                  type="button"
                  onClick={() => openStepNode(selectedStepRow, false)}
                  className="flex items-center gap-1 border border-accent/60 bg-accent/10 px-2 py-1 font-mono text-[9px] text-accent-strong hover:border-accent hover:text-text"
                  data-testid="workflow-open-step"
                >
                  Open step →
                </button>
              ) : selectedBoundaryNode?.component ? (
                <button
                  type="button"
                  onClick={() =>
                    store.focusComponent(selectedBoundaryNode.component)
                  }
                  className="flex items-center gap-1 border border-accent/60 bg-accent/10 px-2 py-1 font-mono text-[9px] text-accent-strong hover:border-accent hover:text-text"
                  data-testid="workflow-open-step-group"
                >
                  Open {selectedBoundaryNode.component} step group →
                </button>
              ) : null}
              <button
                type="button"
                onClick={() => store.focusComponent(undefined)}
                className="flex items-center gap-1 border border-line-soft bg-panel/95 px-2 py-1 font-mono text-[9px] text-muted hover:border-line-strong hover:text-text"
                data-testid="workflow-back-components"
              >
                ← Components
              </button>
            </>
          ) : (
            <>
              {selectedNode ? (
                <button
                  type="button"
                  onClick={() => store.focusComponent(selectedNode.id)}
                  className="flex items-center gap-1 border border-accent/60 bg-accent/10 px-2 py-1 font-mono text-[9px] text-accent-strong hover:border-accent hover:text-text"
                  data-testid="workflow-open-step-group"
                >
                  Open step group →
                </button>
              ) : null}
              <span className="rounded border border-line-soft bg-panel/95 px-2 py-1 font-mono text-[9px] text-faint">
                {activeComponents.size} / {componentMap.nodes.length} components
                active
              </span>
            </>
          )}
        </div>

        <svg
          className="block h-full w-full select-none"
          role="img"
          aria-label={
            inStepGroup && stepScene
              ? `Workflow step graph for ${focusedNode?.id ?? "component"} with ${stepScene.stats?.stepCount ?? 0} steps and ${stepScene.edges.length} links`
              : `Workflow compositor graph with ${componentScene.nodes.length} component nodes and ${componentScene.edges.length} aggregated links`
          }
          data-testid="workflow-map"
          onClick={() => {
            if (inStepGroup) store.selectNode(undefined);
          }}
        >
          <g
            data-testid="workflow-scene"
            transform={`translate(${view.x} ${view.y}) scale(${view.scale})`}
            opacity={size.width ? 1 : 0}
          >
            <WorkflowGraphSceneView
              scene={inStepGroup ? (stepScene ?? componentScene) : componentScene}
              selectedId={inStepGroup ? ui.selectedNodeKey : selectedNode?.id}
              activeIds={
                inStepGroup || !filtering ? undefined : activeComponents
              }
              onSelect={(node) => {
                if (suppressClickRef.current) {
                  suppressClickRef.current = false;
                  return;
                }
                if (inStepGroup) {
                  store.selectNode(node.id);
                  return;
                }
                store.setComponent(
                  ui.filters.component === node.id ? "all" : node.id,
                );
              }}
              onOpen={
                inStepGroup
                  ? (node) => {
                      if (node.kind !== "step" || !node.row) return;
                      store.selectNode(node.id);
                      openStepNode(node.row, false);
                    }
                  : undefined
              }
              onContextMenu={(node, event) => {
                const isStep = node.kind === "step";
                const isComponent = node.kind === "component";
                setMenu({
                  x: event.clientX,
                  y: event.clientY,
                  label: node.label,
                  items: isStep
                    ? [
                        {
                          label: "Open step",
                          hint: "Document",
                          run: () => {
                            if (!node.row) return;
                            store.selectNode(node.id);
                            openStepNode(node.row, false);
                          },
                        },
                        {
                          label: "Back to components",
                          hint: "Workflow",
                          run: () => store.focusComponent(undefined),
                        },
                        {
                          label: "Fit graph",
                          hint: "Reset view",
                          run: fitView,
                        },
                      ]
                    : isComponent
                      ? [
                          {
                            label:
                              ui.filters.component === node.id
                                ? "Clear component filter"
                                : "Select component",
                            hint:
                              ui.filters.component === node.id
                                ? "Show all"
                                : "Filter",
                            run: () =>
                              store.setComponent(
                                ui.filters.component === node.id
                                  ? "all"
                                  : node.id,
                              ),
                          },
                          {
                            label: "Open step group",
                            hint: "Expand",
                            run: () => store.focusComponent(node.id),
                          },
                          {
                            label: "Show steps in Explorer",
                            hint: "Focus",
                            run: () => store.setComponent(node.id),
                          },
                          {
                            label: "Fit graph",
                            hint: "Reset view",
                            run: fitView,
                          },
                        ]
                      : [
                          ...(node.component
                            ? [
                                {
                                  label: `Open ${node.component} step group`,
                                  hint: "Expand",
                                  run: () =>
                                    store.focusComponent(node.component!),
                                },
                              ]
                            : []),
                          {
                            label: "Back to components",
                            hint: "Workflow",
                            run: () => store.focusComponent(undefined),
                          },
                          {
                            label: "Fit graph",
                            hint: "Reset view",
                            run: fitView,
                          },
                        ],
                });
              }}
            />
          </g>
        </svg>

        <div
          className="absolute top-3 left-3 z-10 flex items-stretch border border-line-soft bg-panel/95"
          onPointerDown={(event) => event.stopPropagation()}
          onPointerMove={(event) => event.stopPropagation()}
          onPointerUp={(event) => event.stopPropagation()}
        >
          <button
            type="button"
            onClick={() => zoomBy(1 / 1.25)}
            className="flex size-6 items-center justify-center border-r border-line text-muted hover:bg-panel-soft hover:text-text"
            aria-label="Zoom out workflow"
            title="Zoom out"
            data-testid="workflow-zoom-out"
          >
            −
          </button>
          <span
            className="flex w-12 items-center justify-center border-r border-line font-mono text-[10px] text-muted tabular-nums"
            data-testid="workflow-zoom"
          >
            {Math.round(view.scale * 100)}%
          </span>
          <button
            type="button"
            onClick={() => zoomBy(1.25)}
            className="flex size-6 items-center justify-center border-r border-line text-muted hover:bg-panel-soft hover:text-text"
            aria-label="Zoom in workflow"
            title="Zoom in"
            data-testid="workflow-zoom-in"
          >
            +
          </button>
          <button
            type="button"
            onClick={fitView}
            className="flex h-6 items-center justify-center px-2 text-muted hover:bg-panel-soft hover:text-text"
            aria-label="Fit workflow graph"
            title="Fit graph"
            data-testid="workflow-fit"
          >
            Fit
          </button>
        </div>

        {inStepGroup && stepScene && (stepScene.stats?.stepCount ?? 0) === 0 ? (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <p className="border border-line-soft bg-panel/95 px-3 py-2 font-mono text-[11px] text-muted">
              No steps match the current query and instruction filters.
            </p>
          </div>
        ) : null}

        <div className="pointer-events-none absolute bottom-3 left-3 rounded border border-line-soft bg-panel/95 px-2 py-1 font-mono text-[9px] text-faint">
          {inStepGroup
            ? "drag to pan · wheel to zoom · click a step to select · double-click to open · Open step in the toolbar"
            : "drag to pan · wheel to zoom · right-click a component for actions · node = component · link = aggregated step connections"}
        </div>
      </div>

      {menu ? (
        <ContextMenu
          x={menu.x}
          y={menu.y}
          label={menu.label}
          items={menu.items.map((item) => ({
            label: item.label,
            hint: item.hint,
            onSelect: item.run,
          }))}
          onClose={() => setMenu(undefined)}
        />
      ) : null}
    </div>
  );
}
