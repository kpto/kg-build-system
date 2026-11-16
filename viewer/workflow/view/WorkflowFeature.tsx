"use client";

import {
  useCallback,
  useMemo,
  useState,
  type MouseEvent as ReactMouseEvent,
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
import { DetailBand, DetailDocument, FactGrid } from "@/detail/view/DetailChrome";
import { ContextMenu } from "@/shared/ui/ContextMenu";
import { useGraphViewport } from "@/shared/ui/GraphCanvas";
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
import {
  WorkflowGraphSceneView,
  buildCompositorScene,
  buildStepScene,
} from "./WorkflowGraph";
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
      concept="step"
      kicker={`Design · step · ${step.id[0]}`}
      title={step.id[1]}
      subtitle={`${step.instruction.kind?.join(":") ?? "unknown"} · ${
        step.inputs?.length ?? 0
      } inputs · ${step.outputs?.length ?? 0} outputs · ${incoming.length} in / ${
        outgoing.length
      } out`}
    >
      <DetailBand
        concept="step"
        title="Overview"
        question="What does this step do, in one screen?"
        meta={formatStepId(step.id)}
      >
        <FactGrid
          facts={[
            { label: "Step id", value: formatStepId(step.id) },
            { label: "Component", value: step.id[0] },
            {
              label: "Instruction",
              value: step.instruction.kind?.join(":") ?? "unknown",
            },
            { label: "Bindings", value: `${bindings.length}` },
            {
              label: "Ports",
              value: `${step.inputs?.length ?? 0} in · ${
                step.outputs?.length ?? 0
              } out`,
            },
          ]}
        />
      </DetailBand>

      <DetailBand
        concept="semantics"
        title="Meaning"
        question="What is this step for?"
        meta="build machinery"
      >
        <p className="text-[10px] leading-relaxed text-faint">
          A step is build machinery. It carries no design meaning of its own;
          the meaning of the values it moves stays on the record and the
          relation declarations.
        </p>
      </DetailBand>

      <DetailBand
        concept="graph"
        title="Sources"
        question="Where does this step read from?"
        meta="upstream ports"
      >
        <p className="text-[10px] leading-relaxed text-faint">
          A step has no release source. It reads the artifacts its input
          openings declare; the source of a value is stated by the record and
          relation documents.
        </p>
      </DetailBand>

      <DetailBand
        concept="step"
        title="Ports"
        question="Which artifacts does this step open?"
        meta={`${(step.inputs?.length ?? 0) + (step.outputs?.length ?? 0)}`}
      >
        <div className="grid gap-3 xl:grid-cols-2">
          <div>
            <DetailSubhead>Inputs · {step.inputs?.length ?? 0}</DetailSubhead>
            <Openings step={step} direction="input" />
          </div>
          <div>
            <DetailSubhead>Outputs · {step.outputs?.length ?? 0}</DetailSubhead>
            <Openings step={step} direction="output" />
          </div>
        </div>
      </DetailBand>

      <DetailBand
        concept="step"
        title="Payload"
        question="Which instruction does this step execute?"
        meta={`${Object.keys(step.instruction.payload ?? {}).length} fields`}
      >
        <PayloadFacts step={step} />
      </DetailBand>

      <DetailBand
        concept="edge"
        title="Connections"
        question="Which steps feed this step and which does it feed?"
        meta={`${incoming.length} in · ${outgoing.length} out`}
      >
        <div className="grid gap-3 xl:grid-cols-2">
          <div>
            <DetailSubhead>Incoming · {incoming.length}</DetailSubhead>
            {incoming.length ? (
              <div className="border border-line-soft bg-panel px-2">
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
              <div className="border border-line-soft bg-panel px-2">
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
      </DetailBand>

      {bindings.length ? (
        <DetailBand
          concept="step"
          title="Bindings"
          question="Which record does this step produce?"
          meta={`${bindings.length}`}
        >
          <div className="grid gap-1">
            {bindings.slice(0, 16).map((binding) => (
              <div
                key={binding.index}
                className="flex items-baseline gap-2 border-b border-line-soft py-1 font-mono text-[9.5px] last:border-b-0"
              >
                <span className="w-12 shrink-0 text-faint">
                  #{binding.index}
                </span>
                <span className="min-w-0 flex-1 truncate text-text">
                  {binding.component}
                </span>
                <span className="shrink-0 text-faint">
                  {binding.binding.name ?? binding.kind}
                </span>
              </div>
            ))}
            {bindings.length > 16 ? (
              <p className="font-mono text-[8.5px] text-faint">
                showing 16 of {bindings.length}
              </p>
            ) : null}
          </div>
        </DetailBand>
      ) : null}
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
        concept="step"
        kicker="Design · step"
        title="Step unavailable"
        subtitle="This step is not present in the workflow plan."
      >
        <DetailBand concept="step" title="Overview" question="What is this step?">
          <p className="text-[10.5px] leading-relaxed text-faint">
            The selected workflow step could not be resolved from the snapshot.
          </p>
        </DetailBand>
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

  const {
    containerRef,
    size,
    view,
    fitView,
    zoomBy,
    onPointerDown,
    shouldSuppressClick,
  } = useGraphViewport({
    width: activeScene.width,
    height: activeScene.height,
  });

  const [menu, setMenu] = useState<
    | {
        x: number;
        y: number;
        label: string;
        items: Array<{ label: string; hint?: string; run(): void }>;
      }
    | undefined
  >(undefined);

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
            if (shouldSuppressClick()) return;
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
                if (shouldSuppressClick()) return;
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
