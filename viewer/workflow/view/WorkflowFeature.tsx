"use client";

import { useMemo, type ReactNode } from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  Boxes,
  ChevronRight,
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
import { cx, theme } from "@/shared/ui/theme";
import {
  activeDocument,
  type SubjectSelection,
  type WorkspaceProps,
} from "@/workbench/types";
import {
  buildWorkflowComponentMap,
  buildWorkflowModel,
  filterWorkflowRows,
  formatArtifactType,
  formatOpening,
  formatStepId,
  groupWorkflowRows,
  type WorkflowStepRow,
} from "@/workflow/model/WorkflowViewModel";
import { useWorkflowUi } from "./workflowUi";

function workflowModel(state: WorkspaceProps["state"]) {
  return buildWorkflowModel(state.index);
}

function stepSelection(row: WorkflowStepRow): SubjectSelection {
  return {
    kind: "step",
    component: row.component,
    name: row.name,
    stepId: row.id,
  };
}

function stepKeyForSelection(selection: SubjectSelection | undefined) {
  if (selection?.stepId) return stepKey(selection.stepId);
  if (selection?.component && selection.name) {
    return stepKey([selection.component, selection.name]);
  }
  return undefined;
}

// ---------------------------------------------------------------------------
// Outline: the workflow step list
// ---------------------------------------------------------------------------

function GroupHeader({ component, count }: { component: string; count: number }) {
  return (
    <div className="sticky top-0 z-10 flex items-center gap-1.5 border-b border-line-soft bg-panel-raised px-2 py-1">
      <ChevronRight aria-hidden className="size-3 text-faint" />
      <span className="min-w-0 flex-1 truncate font-mono text-[9px] font-semibold tracking-[0.08em] text-muted uppercase">
        {component}
      </span>
      <span className="font-mono text-[9px] text-faint">{count}</span>
    </div>
  );
}

function StepRow({
  row,
  active,
  onSelect,
  onOpenPermanent,
}: {
  row: WorkflowStepRow;
  active: boolean;
  onSelect(): void;
  onOpenPermanent(): void;
}) {
  return (
    <button
      type="button"
      className={cx(
        "flex w-full items-center gap-2 border-b border-line-soft/50 px-2 py-1.5 text-left",
        active
          ? "bg-selection/10 text-text shadow-[inset_2px_0_0_var(--color-selection)]"
          : "text-muted hover:bg-panel-soft/50 hover:text-text",
      )}
      onClick={onSelect}
      onDoubleClick={onOpenPermanent}
      data-testid="workflow-step"
      data-step-key={row.key}
      data-active={active ? "true" : undefined}
      title={`${row.component} · ${row.name}`}
    >
      <span className="min-w-0 flex-1">
        <span className="block truncate font-mono text-[10px]">{row.name}</span>
        <span className="block truncate font-mono text-[8.5px] text-faint">
          {row.kindLabel}
        </span>
      </span>
      <span className="flex shrink-0 items-center gap-1">
        <span className="font-mono text-[8.5px] text-faint">
          {row.inputs} in
        </span>
        <span className="font-mono text-[8.5px] text-faint">
          {row.outputs} out
        </span>
      </span>
    </button>
  );
}

export function WorkflowOutline(props: WorkspaceProps) {
  const model = useMemo(() => workflowModel(props.state), [props.state.index]);
  const { state: ui } = useWorkflowUi(props.state.snapshot.name);
  const rows = useMemo(
    () => filterWorkflowRows(model.rows, ui.filters),
    [model.rows, ui.filters],
  );
  const groups = useMemo(() => groupWorkflowRows(rows), [rows]);
  const active = activeDocument(props.state);
  const activeStepKey =
    active.kind === "subject" ? stepKeyForSelection(active.selection) : undefined;

  const open = (row: WorkflowStepRow, preview: boolean) => {
    props.actions.openTab({ selection: stepSelection(row), preview });
  };

  return (
    <div className="flex h-full flex-col" data-testid="workflow-outline">
      <div className="flex flex-none items-center justify-between border-b border-line-soft px-2 py-1.5">
        <span className="text-[9px] font-semibold tracking-[0.08em] text-faint uppercase">
          Steps
        </span>
        <span className="font-mono text-[9px] text-faint">
          {rows.length} / {model.steps}
        </span>
      </div>
      <div className="thin-scrollbar min-h-0 flex-1 overflow-y-auto">
        {groups.length ? (
          groups.map((group) => (
            <section key={group.component}>
              <GroupHeader component={group.component} count={group.rows.length} />
              {group.rows.map((row) => (
                <StepRow
                  key={row.key}
                  row={row}
                  active={activeStepKey === row.key}
                  onSelect={() => open(row, true)}
                  onOpenPermanent={() => open(row, false)}
                />
              ))}
            </section>
          ))
        ) : (
          <p className="p-3 text-[10px] leading-relaxed text-faint">
            No workflow steps match the Control filters.
          </p>
        )}
      </div>
    </div>
  );
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
          The filtered steps are listed in Outline. Select one to open its step
          detail document.
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
    <article className="min-h-full p-4" data-testid="workflow-step-detail">
      <header className="mb-4 border-b border-line-soft pb-3">
        <p className="mb-1 flex items-center gap-1.5 text-[9px] font-semibold tracking-[0.08em] text-faint uppercase">
          <Boxes aria-hidden className="size-3 text-selection" />
          Design · step · {step.id[0]}
        </p>
        <h2 className="truncate font-mono text-[15px] text-text">
          {step.id[1]}
        </h2>
        <p className="mt-1 font-mono text-[10px] text-muted">
          {step.instruction.kind?.join(":") ?? "unknown"} · {step.inputs?.length ?? 0}{" "}
          inputs · {step.outputs?.length ?? 0} outputs · {incoming.length} in /{" "}
          {outgoing.length} out
        </p>
      </header>

      <div className="mb-4 grid grid-cols-2 gap-x-6 gap-y-1">
        <Fact label="Step id">{formatStepId(step.id)}</Fact>
        <Fact label="Component">{step.id[0]}</Fact>
        <Fact label="Instruction">
          {step.instruction.kind?.join(":") ?? "unknown"}
        </Fact>
        <Fact label="Bindings">{bindings.length}</Fact>
      </div>

      <section className="mb-4">
        <h3 className="mb-1.5 text-[9px] font-semibold tracking-[0.08em] text-faint uppercase">
          Inputs
        </h3>
        <Openings step={step} direction="input" />
      </section>

      <section className="mb-4">
        <h3 className="mb-1.5 text-[9px] font-semibold tracking-[0.08em] text-faint uppercase">
          Outputs
        </h3>
        <Openings step={step} direction="output" />
      </section>

      <section className="mb-4">
        <h3 className="mb-1.5 text-[9px] font-semibold tracking-[0.08em] text-faint uppercase">
          Instruction payload
        </h3>
        <PayloadFacts step={step} />
      </section>

      <section className="mb-4 grid gap-3 xl:grid-cols-2">
        <div>
          <h3 className="mb-1.5 text-[9px] font-semibold tracking-[0.08em] text-faint uppercase">
            Incoming · {incoming.length}
          </h3>
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
            <p className="text-[10px] text-faint">This step has no inputs.</p>
          )}
        </div>
        <div>
          <h3 className="mb-1.5 text-[9px] font-semibold tracking-[0.08em] text-faint uppercase">
            Outgoing · {outgoing.length}
          </h3>
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
            <p className="text-[10px] text-faint">This step has no outputs.</p>
          )}
        </div>
      </section>

      {bindings.length ? (
        <section>
          <h3 className="mb-1.5 text-[9px] font-semibold tracking-[0.08em] text-faint uppercase">
            Blueprint bindings · {bindings.length}
          </h3>
          <div className="grid gap-1">
            {bindings.slice(0, 16).map((binding) => (
              <div
                key={binding.index}
                className="flex items-baseline gap-2 font-mono text-[9.5px]"
              >
                <span className="w-12 shrink-0 text-faint">#{binding.index}</span>
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
        </section>
      ) : null}
    </article>
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
      <div
        className="flex h-full items-center justify-center p-6"
        data-testid="workflow-step-editor"
      >
        <p className="max-w-[42ch] text-center text-[11px] leading-relaxed text-muted">
          This step is not present in the workflow plan.
        </p>
      </div>
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

const MAP_WIDTH = 1000;
const MAP_HEIGHT = 680;
const MAP_CX = MAP_WIDTH / 2;
const MAP_CY = MAP_HEIGHT / 2;
const NODE_RADIUS = 52;

function componentPositions(ids: string[]): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>();
  if (ids.length === 1) {
    positions.set(ids[0], { x: MAP_CX, y: MAP_CY });
    return positions;
  }
  const rx = 340;
  const ry = 232;
  ids.forEach((id, index) => {
    const angle = -Math.PI / 2 + (index * Math.PI * 2) / ids.length;
    positions.set(id, {
      x: MAP_CX + rx * Math.cos(angle),
      y: MAP_CY + ry * Math.sin(angle),
    });
  });
  return positions;
}

interface EdgeGeometry {
  path: string;
  labelX: number;
  labelY: number;
}

function edgeGeometry(
  source: { x: number; y: number },
  target: { x: number; y: number },
  sourceId: string,
  targetId: string,
): EdgeGeometry {
  if (sourceId === targetId) {
    const top = source.y - NODE_RADIUS;
    return {
      path: `M ${source.x - 22} ${top} C ${source.x - 92} ${top - 104}, ${
        source.x + 92
      } ${top - 104}, ${source.x + 22} ${top}`,
      labelX: source.x,
      labelY: top - 82,
    };
  }
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const length = Math.max(1, Math.hypot(dx, dy));
  const ux = dx / length;
  const uy = dy / length;
  const nx = -uy;
  const ny = ux;
  const bend = sourceId < targetId ? 26 : -26;
  // Stop at the circle edges so the arrow marker stays visible above the node.
  const startX = source.x + ux * NODE_RADIUS;
  const startY = source.y + uy * NODE_RADIUS;
  const endX = target.x - ux * (NODE_RADIUS + 4);
  const endY = target.y - uy * (NODE_RADIUS + 4);
  const cx = (startX + endX) / 2 + nx * bend;
  const cy = (startY + endY) / 2 + ny * bend;
  return {
    path: `M ${startX} ${startY} Q ${cx} ${cy} ${endX} ${endY}`,
    labelX: 0.25 * startX + 0.5 * cx + 0.25 * endX,
    labelY: 0.25 * startY + 0.5 * cy + 0.25 * endY,
  };
}

export function WorkflowEditor(props: WorkspaceProps) {
  const model = useMemo(() => workflowModel(props.state), [props.state.index]);
  const componentMap = useMemo(
    () => buildWorkflowComponentMap(props.state.index, model),
    [props.state.index, model],
  );
  const { state: ui, store } = useWorkflowUi(props.state.snapshot.name);
  const filtered = useMemo(
    () => filterWorkflowRows(model.rows, ui.filters),
    [model.rows, ui.filters],
  );
  const activeComponents = useMemo(
    () => new Set(filtered.map((row) => row.component)),
    [filtered],
  );
  const positions = useMemo(
    () => componentPositions(componentMap.nodes.map((node) => node.id)),
    [componentMap.nodes],
  );
  const filtering =
    Boolean(ui.filters.query.trim()) ||
    ui.filters.component !== "all" ||
    ui.filters.kind !== "all";

  if (!componentMap.nodes.length) {
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
            Design · workflow map
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

      <div className="relative min-h-0 flex-1">
        <svg
          viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`}
          preserveAspectRatio="xMidYMid meet"
          className="block h-full w-full select-none"
          role="img"
          aria-label={`Workflow component map with ${componentMap.nodes.length} components and ${componentMap.edges.length} aggregated connections`}
          data-testid="workflow-map"
        >
          <defs>
            <marker
              id="workflow-arrow"
              viewBox="0 0 8 8"
              refX="7"
              refY="4"
              markerWidth="6"
              markerHeight="6"
              orient="auto"
            >
              <path d="M0,0 L8,4 L0,8 Z" fill={theme.edge} />
            </marker>
            <marker
              id="workflow-arrow-selection"
              viewBox="0 0 8 8"
              refX="7"
              refY="4"
              markerWidth="6"
              markerHeight="6"
              orient="auto"
            >
              <path d="M0,0 L8,4 L0,8 Z" fill={theme.selection} />
            </marker>
          </defs>

          <g data-workflow-edges>
            {componentMap.edges.map((edge) => {
              const source = positions.get(edge.source);
              const target = positions.get(edge.target);
              if (!source || !target) return null;
              const geometry = edgeGeometry(
                source,
                target,
                edge.source,
                edge.target,
              );
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
                  opacity={incident ? 1 : active ? 0.62 : 0.12}
                  data-testid="workflow-component-edge"
                  data-source={edge.source}
                  data-target={edge.target}
                >
                  <path
                    d={geometry.path}
                    fill="none"
                    stroke={incident ? theme.selection : theme.edge}
                    strokeWidth={Math.min(3.4, 0.9 + Math.log2(edge.count + 1))}
                    markerEnd={
                      incident
                        ? "url(#workflow-arrow-selection)"
                        : "url(#workflow-arrow)"
                    }
                  />
                  <text
                    x={geometry.labelX}
                    y={geometry.labelY}
                    textAnchor="middle"
                    fill={incident ? theme.selectionStrong : theme.faint}
                    fontSize={9}
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
            })}
          </g>

          <g data-workflow-nodes>
            {componentMap.nodes.map((node) => {
              const position = positions.get(node.id);
              if (!position) return null;
              const selected = ui.filters.component === node.id;
              const active = !filtering || activeComponents.has(node.id);
              return (
                <g
                  key={node.id}
                  transform={`translate(${position.x} ${position.y})`}
                  className="cursor-pointer"
                  opacity={active ? 1 : 0.28}
                  onClick={() =>
                    store.setComponent(selected ? "all" : node.id)
                  }
                  role="button"
                  tabIndex={0}
                  aria-pressed={selected}
                  aria-label={`${node.id}: ${node.steps} steps, ${node.incoming} incoming and ${node.outgoing} outgoing connections`}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      store.setComponent(selected ? "all" : node.id);
                    }
                  }}
                  data-testid="workflow-component-node"
                  data-component={node.id}
                >
                  <circle
                    r={NODE_RADIUS + (selected ? 5 : 0)}
                    fill={selected ? theme.selectionSoft : theme.raised}
                    stroke={selected ? theme.selection : theme.lineStrong}
                    strokeWidth={selected ? 1.8 : 1}
                  />
                  <text
                    y={-3}
                    textAnchor="middle"
                    fill={selected ? theme.selectionStrong : theme.text}
                    fontSize={10.5}
                    fontFamily="var(--font-mono)"
                    pointerEvents="none"
                  >
                    {node.id}
                  </text>
                  <text
                    y={14}
                    textAnchor="middle"
                    fill={theme.faint}
                    fontSize={8.5}
                    fontFamily="var(--font-mono)"
                    pointerEvents="none"
                  >
                    {node.steps} steps
                  </text>
                </g>
              );
            })}
          </g>
        </svg>

        <div className="pointer-events-none absolute bottom-3 left-3 rounded border border-line-soft bg-panel/95 px-2 py-1 font-mono text-[9px] text-faint">
          node = component · arrow = aggregated connections · click a component
          to filter Outline
        </div>
      </div>
    </div>
  );
}
