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
  ViewerIndex,
  WorkflowStep,
} from "@/lib/types";
import { stepKey } from "@/lib/indexes";
import { cx } from "@/shared/ui/theme";
import type { WorkspaceProps } from "@/workbench/types";
import {
  buildWorkflowModel,
  filterWorkflowRows,
  formatArtifactType,
  formatOpening,
  formatStepId,
  groupWorkflowRows,
  type WorkflowStepRow,
} from "@/workflow/model/WorkflowViewModel";
import { useWorkflowUi } from "./workflowUi";

function workflowRows(state: WorkspaceProps["state"]) {
  return buildWorkflowModel(state.index);
}

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
}: {
  row: WorkflowStepRow;
  active: boolean;
  onSelect(): void;
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
        <span className="font-mono text-[8.5px] text-faint">{row.inputs}in</span>
        <span className="font-mono text-[8.5px] text-faint">{row.outputs}out</span>
      </span>
    </button>
  );
}

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
          Workflow step · {step.id[0]}
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
        <Fact label="Step id">
          {formatStepId(step.id)}
        </Fact>
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
          </div>
        </section>
      ) : null}
    </article>
  );
}

export function WorkflowEditor({ state }: WorkspaceProps) {
  const model = useMemo(() => workflowRows(state), [state.index]);
  const { state: ui, store } = useWorkflowUi(state.snapshot.name);
  const rows = useMemo(
    () => filterWorkflowRows(model.rows, ui.filters),
    [model.rows, ui.filters],
  );
  const groups = useMemo(() => groupWorkflowRows(rows), [rows]);
  const selected =
    rows.find((row) => row.key === ui.selectedStepKey) ?? rows[0];
  const selectedStep = selected
    ? state.index.stepsById.get(selected.key)
    : undefined;

  return (
    <div
      className="flex h-full min-h-0 flex-col bg-abyss"
      data-testid="workflow-editor"
    >
      <header className="flex flex-none items-start justify-between gap-4 border-b border-line-soft bg-panel px-4 py-3">
        <div className="min-w-0">
          <p className="mb-1 flex items-center gap-1.5 text-[9px] font-semibold tracking-[0.08em] text-faint uppercase">
            <ListTree aria-hidden className="size-3 text-selection" />
            Design · workflow
          </p>
          <h1 className="text-[15px] font-semibold tracking-tight text-text">
            Workflow
          </h1>
          <p className="mt-1 font-mono text-[10px] text-muted">
            {model.steps} steps · {model.connections} connections ·{" "}
            {model.components.length} components
          </p>
        </div>
        <span className="shrink-0 rounded border border-line-soft bg-panel-raised px-2 py-1 font-mono text-[9px] text-faint">
          {rows.length} / {model.steps} visible
        </span>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside className="flex w-[320px] flex-none flex-col border-r border-line-soft bg-panel">
          <div className="flex flex-none items-center justify-between border-b border-line-soft px-2 py-1.5">
            <span className="text-[9px] font-semibold tracking-[0.08em] text-faint uppercase">
              Steps
            </span>
            <span className="font-mono text-[9px] text-faint">
              {groups.length} components
            </span>
          </div>
          <div className="thin-scrollbar min-h-0 flex-1 overflow-y-auto">
            {groups.length ? (
              groups.map((group) => (
                <section key={group.component}>
                  <GroupHeader
                    component={group.component}
                    count={group.rows.length}
                  />
                  {group.rows.map((row) => (
                    <StepRow
                      key={row.key}
                      row={row}
                      active={selected?.key === row.key}
                      onSelect={() => store.selectStep(row.key)}
                    />
                  ))}
                </section>
              ))
            ) : (
              <p className="p-3 text-[10px] text-faint">
                No workflow steps match these filters.
              </p>
            )}
          </div>
        </aside>

        <section className="thin-scrollbar min-w-0 flex-1 overflow-y-auto">
          {selectedStep ? (
            <StepDetail index={state.index} step={selectedStep} />
          ) : (
            <div className="flex h-full items-center justify-center p-6">
              <p className="max-w-[42ch] text-center text-[11px] leading-relaxed text-muted">
                This snapshot has no workflow plan, or no steps match the
                selected Control filters.
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export function WorkflowSidebar({ state }: WorkspaceProps) {
  const model = useMemo(() => workflowRows(state), [state.index]);
  const { state: ui, store } = useWorkflowUi(state.snapshot.name);
  const rows = useMemo(
    () => filterWorkflowRows(model.rows, ui.filters),
    [model.rows, ui.filters],
  );

  return (
    <div className="flex h-full flex-col" data-testid="workflow-sidebar">
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
