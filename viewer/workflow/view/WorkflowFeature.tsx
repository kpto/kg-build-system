"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  Boxes,
  ListTree,
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
import { cx, groupPalette, theme } from "@/shared/ui/theme";
import { activeDocument, type WorkspaceProps } from "@/workbench/types";
import {
  buildWorkflowComponentMap,
  buildWorkflowModel,
  filterWorkflowRows,
  formatArtifactType,
  formatOpening,
  formatStepId,
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
          Filters dim the compositor graph. Every step remains available in
          Explorer; select one there to open its step detail document.
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
      kicker={`Design · step · ${step.id[0]}`}
      icon={<Boxes aria-hidden className="size-3 text-selection" />}
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
        kicker="Design · step"
        icon={<Boxes aria-hidden className="size-3 text-selection" />}
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

interface PlacedNode {
  node: ReturnType<typeof buildWorkflowComponentMap>["nodes"][number];
  x: number;
  y: number;
  color: string;
  internal: number;
}

interface PlacedEdge {
  edge: ReturnType<typeof buildWorkflowComponentMap>["edges"][number];
  path: string;
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  labelX: number;
  labelY: number;
}

interface CompositorLayout {
  nodes: PlacedNode[];
  edges: PlacedEdge[];
  width: number;
  height: number;
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

function buildCompositorLayout(
  map: ReturnType<typeof buildWorkflowComponentMap>,
): CompositorLayout {
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

  const placed = new Map<string, PlacedNode>();
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

  const edges: PlacedEdge[] = [];
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
      edge,
      path: `M ${sx} ${sy} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${tx} ${ty}`,
      sourceX: sx,
      sourceY: sy,
      targetX: tx,
      targetY: ty,
      labelX:
        0.125 * sx + 0.375 * c1x + 0.375 * c2x + 0.125 * tx,
      labelY:
        0.125 * sy + 0.375 * c1y + 0.375 * c2y + 0.125 * ty,
    });
  }

  return {
    nodes: [...placed.values()],
    edges,
    width,
    height,
  };
}

export function WorkflowEditor(props: WorkspaceProps) {
  const model = useMemo(() => workflowModel(props.state), [props.state.index]);
  const componentMap = useMemo(
    () => buildWorkflowComponentMap(props.state.index, model),
    [props.state.index, model],
  );
  const layout = useMemo(() => buildCompositorLayout(componentMap), [componentMap]);
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
  }, [layout.nodes.length]);

  const fitView = useCallback(() => {
    if (!size.width || !size.height || !layout.width || !layout.height) return;
    const pad = 30;
    const scale = Math.max(
      0.12,
      Math.min(
        1.4,
        Math.min(
          (size.width - pad * 2) / layout.width,
          (size.height - pad * 2) / layout.height,
        ),
      ),
    );
    setView({
      scale,
      x: (size.width - layout.width * scale) / 2,
      y: (size.height - layout.height * scale) / 2,
    });
  }, [size.width, size.height, layout.width, layout.height]);

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
  }, [layout.nodes.length]);

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

  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      x: view.x,
      y: view.y,
      moved: false,
    };
    suppressClickRef.current = false;
  };

  const onPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const dx = event.clientX - drag.startX;
    const dy = event.clientY - drag.startY;
    if (!drag.moved) {
      if (Math.abs(dx) <= 3 && Math.abs(dy) <= 3) return;
      drag.moved = true;
    }
    setView((current) => ({ ...current, x: drag.x + dx, y: drag.y + dy }));
  };

  const onPointerUp = (event: ReactPointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag) return;
    dragRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    if (drag.moved) {
      suppressClickRef.current = true;
      window.setTimeout(() => {
        suppressClickRef.current = false;
      }, 0);
    }
  };

  if (!layout.nodes.length) {
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
      <header className="flex flex-none items-start justify-between gap-4 border-b border-line-soft bg-panel px-4 py-3">
        <div className="min-w-0">
          <p className="mb-1 flex items-center gap-1.5 text-[9px] font-semibold tracking-[0.08em] text-faint uppercase">
            <ListTree aria-hidden className="size-3 text-selection" />
            Design · workflow compositor
          </p>
          <h1 className="text-[15px] font-semibold tracking-tight text-text">
            Workflow
          </h1>
          <p className="mt-1 font-mono text-[10px] text-muted">
            {model.steps} steps · {model.connections} connections ·{" "}
            {componentMap.nodes.length} components
          </p>
        </div>
        <span className="shrink-0 rounded border border-line-soft bg-panel-raised px-2 py-1 font-mono text-[9px] text-faint">
          {activeComponents.size} / {componentMap.nodes.length} components active
        </span>
      </header>

      <div
        ref={containerRef}
        className="relative min-h-0 flex-1 cursor-grab touch-none overflow-hidden select-none"
        data-testid="workflow-canvas"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <svg
          className="block h-full w-full select-none"
          role="img"
          aria-label={`Workflow compositor graph with ${layout.nodes.length} component nodes and ${layout.edges.length} aggregated links`}
          data-testid="workflow-map"
        >
          <g
            data-testid="workflow-scene"
            transform={`translate(${view.x} ${view.y}) scale(${view.scale})`}
            opacity={size.width ? 1 : 0}
          >
            <g data-workflow-edges>
              {layout.edges.map(
                ({ edge, path, sourceX, sourceY, targetX, targetY, labelX, labelY }) => {
                const incident =
                  ui.filters.component !== "all" &&
                  (edge.source === ui.filters.component ||
                    edge.target === ui.filters.component);
                const active =
                  !filtering ||
                  (activeComponents.has(edge.source) &&
                    activeComponents.has(edge.target));
                return (
                  <g
                    key={edge.id}
                    opacity={incident ? 1 : active ? 0.58 : 0.1}
                    data-testid="workflow-component-edge"
                    data-source={edge.source}
                    data-target={edge.target}
                    data-source-x={sourceX}
                    data-source-y={sourceY}
                    data-target-x={targetX}
                    data-target-y={targetY}
                  >
                    <path
                      d={path}
                      fill="none"
                      stroke={incident ? theme.selection : theme.edge}
                      strokeWidth={Math.min(
                        2.6,
                        1 + Math.log2(edge.count + 1) * 0.45,
                      )}
                      strokeLinecap="round"
                    />
                    <text
                      x={labelX}
                      y={labelY - 4}
                      textAnchor="middle"
                      fill={incident ? theme.selectionStrong : theme.faint}
                      fontSize={9.5}
                      fontFamily="var(--font-mono)"
                      stroke={theme.page}
                      strokeWidth={3}
                      paintOrder="stroke"
                      pointerEvents="none"
                    >
                      {edge.count}
                    </text>
                  </g>
                  );
                },
              )}
            </g>

            <g data-workflow-nodes>
              {layout.nodes.map(({ node, x, y, color, internal }) => {
                const selected = ui.filters.component === node.id;
                const active = !filtering || activeComponents.has(node.id);
                return (
                  <g
                    key={node.id}
                    transform={`translate(${x} ${y})`}
                    className="cursor-pointer"
                    opacity={active ? 1 : 0.3}
                    onClick={() => {
                      if (suppressClickRef.current) {
                        suppressClickRef.current = false;
                        return;
                      }
                      store.setComponent(selected ? "all" : node.id);
                    }}
                    role="button"
                    tabIndex={0}
                    aria-pressed={selected}
                    aria-label={`${node.id}: ${node.steps} steps, ${node.kinds} instruction kinds, ${node.incoming} incoming and ${node.outgoing} outgoing links`}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        store.setComponent(selected ? "all" : node.id);
                      }
                    }}
                    data-testid="workflow-component-node"
                    data-component={node.id}
                  >
                    <rect
                      width={NODE_WIDTH}
                      height={NODE_HEIGHT}
                      rx={6}
                      fill={theme.panel}
                      stroke={selected ? theme.selection : theme.lineStrong}
                      strokeWidth={selected ? 1.8 : 1}
                    />
                    <path
                      d={`M 0 6 Q 0 0 6 0 H ${NODE_WIDTH - 6} Q ${NODE_WIDTH} 0 ${NODE_WIDTH} 6 V ${HEADER_HEIGHT} H 0 Z`}
                      fill={color}
                      fillOpacity={selected ? 0.62 : 0.34}
                      stroke="none"
                    />
                    <text
                      x={12}
                      y={19}
                      fill={theme.text}
                      fontSize={11.5}
                      fontWeight={600}
                      fontFamily="var(--font-mono)"
                      pointerEvents="none"
                    >
                      {node.id}
                    </text>

                    <circle
                      cx={0}
                      cy={SOCKET_Y}
                      r={5}
                      fill={theme.raised}
                      stroke={selected ? theme.selection : color}
                      strokeWidth={1.4}
                      pointerEvents="none"
                    />
                    <text
                      x={12}
                      y={SOCKET_Y + 4}
                      fill={theme.faint}
                      fontSize={8.5}
                      fontFamily="var(--font-mono)"
                      pointerEvents="none"
                    >
                      in
                    </text>
                    <circle
                      cx={NODE_WIDTH}
                      cy={SOCKET_Y}
                      r={5}
                      fill={theme.raised}
                      stroke={selected ? theme.selection : color}
                      strokeWidth={1.4}
                      pointerEvents="none"
                    />
                    <text
                      x={NODE_WIDTH - 12}
                      y={SOCKET_Y + 4}
                      textAnchor="end"
                      fill={theme.faint}
                      fontSize={8.5}
                      fontFamily="var(--font-mono)"
                      pointerEvents="none"
                    >
                      out
                    </text>

                    <text
                      x={12}
                      y={HEADER_HEIGHT + 50}
                      fill={theme.text}
                      fontSize={10.5}
                      fontFamily="var(--font-mono)"
                      pointerEvents="none"
                    >
                      {node.steps} steps · {node.kinds} kinds
                    </text>
                    <text
                      x={12}
                      y={HEADER_HEIGHT + 72}
                      fill={theme.faint}
                      fontSize={9.5}
                      fontFamily="var(--font-mono)"
                      pointerEvents="none"
                    >
                      {node.incoming} in · {node.outgoing} out
                    </text>
                    {internal ? (
                      <text
                        x={12}
                        y={HEADER_HEIGHT + 94}
                        fill={theme.faint}
                        fontSize={9.5}
                        fontFamily="var(--font-mono)"
                        pointerEvents="none"
                      >
                        {internal} internal
                      </text>
                    ) : null}
                  </g>
                );
              })}
            </g>
          </g>
        </svg>

        <div
          className="absolute top-3 right-3 z-10 flex items-stretch border border-line-soft bg-panel/95"
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

        <div className="pointer-events-none absolute bottom-3 left-3 rounded border border-line-soft bg-panel/95 px-2 py-1 font-mono text-[9px] text-faint">
          drag to pan · wheel to zoom · node = component · link = aggregated
          step connections
        </div>
      </div>
    </div>
  );
}
