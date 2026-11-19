"use client";

import {
  useCallback,
  useMemo,
  useState,
  type MouseEvent as ReactMouseEvent,
  type ReactNode,
} from "react";
import { RotateCcw, Search } from "lucide-react";

import type { StepId, ViewerIndex, WorkflowStep } from "@/lib/types";
import { stepKey } from "@/lib/indexes";
import { DetailBand, DetailDocument } from "@/detail/view/DetailChrome";
import { Constitution } from "@/detail/view/Constitution";
import { stepBoundaryModel } from "@/detail/model/constitution";
import { ContextMenu } from "@/shared/ui/ContextMenu";
import { Empty, Field, Input, Select } from "@kbs/design";
import { useGraphViewport } from "@/shared/ui/GraphCanvas";
import { cx, groupPalette, theme } from "@kbs/design";
import {
  ViewportAction,
  ViewportFrame,
  ViewportHint,
  ViewportNav,
} from "@/shared/ui/Viewport";
import { activeDocument, type WorkspaceProps } from "@/workbench/types";
import { InvolvedSteps } from "@/detail/view/InvolvedSteps";
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
  WorkflowDagSceneView,
  buildCompositorScene,
  buildStepScene,
} from "@/shared/ui/WorkflowDag";
import { useWorkflowUi } from "./workflowUi";

function workflowModel(state: WorkspaceProps["state"]) {
  return buildWorkflowModel(state.index);
}

// ---------------------------------------------------------------------------
// Controls: one compact bar over the workflow canvas
// ---------------------------------------------------------------------------

/**
 * The Workflow view controls sit on the graph they narrow. Search is first
 * because it is the most frequent action; the two selects and the count are
 * the only other choices, so the bar stays a single row where space allows.
 */
export function WorkflowControls({ state }: WorkspaceProps) {
  const model = useMemo(() => workflowModel(state), [state.index]);
  const { state: ui, store } = useWorkflowUi(state.snapshot.name);
  const rows = useMemo(
    () => filterWorkflowRows(model.rows, ui.filters),
    [model.rows, ui.filters],
  );
  const filtering =
    Boolean(ui.filters.query.trim()) ||
    ui.filters.component !== "all" ||
    ui.filters.kind !== "all";

  return (
    <div
      className="pointer-events-auto flex max-w-full flex-wrap items-center gap-1 rounded-[var(--radius-sm)] border border-line bg-panel/95 p-1 shadow-lg"
      data-testid="workflow-controls"
      onPointerDown={(event) => event.stopPropagation()}
    >
      <div className="relative flex items-center">
        <Search
          aria-hidden
          className="pointer-events-none absolute left-1.5 size-3 text-faint"
        />
        <Input
          value={ui.filters.query}
          onChange={(event) => store.setQuery(event.target.value)}
          placeholder="Filter steps"
          aria-label="Filter workflow steps"
          title="Filter workflow steps by name or component"
          spellCheck={false}
          className="h-6 w-[168px] py-0 pl-5 text-[length:var(--text-caption)]"
          data-testid="workflow-filter-query"
        />
      </div>

      <Select
        value={ui.filters.component}
        onChange={(event) => store.setComponent(event.target.value)}
        aria-label="Filter by component"
        title="Filter by component"
        className="h-6 w-[150px] py-0 text-[length:var(--text-caption)]"
        data-testid="workflow-filter-component"
      >
        <option value="all">All components · {model.components.length}</option>
        {model.components.map((component) => (
          <option key={component} value={component}>
            {component}
          </option>
        ))}
      </Select>

      <Select
        value={ui.filters.kind}
        onChange={(event) => store.setKind(event.target.value)}
        aria-label="Filter by instruction kind"
        title="Filter by instruction kind"
        className="h-6 w-[150px] py-0 text-[length:var(--text-caption)]"
        data-testid="workflow-filter-kind"
      >
        <option value="all">All instructions</option>
        {model.kinds.map((kind) => (
          <option key={kind.key} value={kind.key}>
            {kind.label} · {kind.count}
          </option>
        ))}
      </Select>

      <span className="px-0.5 font-mono text-[length:var(--text-caption)] text-faint">
        {rows.length}/{model.steps}
      </span>

      {filtering ? (
        <button
          type="button"
          onClick={() => store.resetFilters()}
          title="Reset workflow filters"
          aria-label="Reset workflow filters"
          data-testid="workflow-reset"
          className="inline-flex h-6 items-center gap-1 px-1.5 text-[length:var(--text-caption)] text-muted hover:bg-panel-soft hover:text-text"
        >
          <RotateCcw aria-hidden className="size-3" />
          Reset
        </button>
      ) : null}
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
  return <Field label={label} value={children} />;
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
      <Empty>This instruction carries no payload.</Empty>
    );
  }
  return (
    <div className="grid gap-1" data-testid="workflow-payload">
      {entries.map(([key, value]) => {
        const text = scalar(value);
        if (text) {
          return (
            <div key={key} className="flex items-baseline gap-2">
              <span className="w-40 shrink-0 truncate font-mono text-[length:var(--text-sm)] text-faint">
                {key}
              </span>
              <span
                className="min-w-0 flex-1 truncate font-mono text-[length:var(--text-base)] text-text"
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
          <details key={key} className="group rounded-[var(--radius-md)] border border-line-soft">
            <summary className="flex cursor-pointer list-none items-baseline gap-2 px-1.5 py-1 hover:bg-panel-soft/50">
              <span className="w-40 shrink-0 truncate font-mono text-[length:var(--text-sm)] text-faint">
                {key}
              </span>
              <span className="min-w-0 flex-1 truncate font-mono text-[length:var(--text-base)] text-muted">
                {label}
              </span>
            </summary>
            <pre className="thin-scrollbar max-h-56 overflow-auto border-t border-line-soft bg-inset p-2 font-mono text-[length:var(--text-sm)] leading-relaxed text-muted">
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
      <p className="text-[length:var(--text-base)] text-faint">No {direction}s are declared.</p>
    );
  }
  return (
    <div className="grid gap-1" data-testid={`workflow-${direction}s`}>
      {items.map((item, index) => (
        <div
          key={`${direction}:${index}:${formatOpening(item.opening_name)}`}
          className="flex min-w-0 items-baseline gap-2"
        >
          <span className="w-40 shrink-0 truncate font-mono text-[length:var(--text-sm)] text-muted">
            {formatOpening(item.opening_name)}
          </span>
          <span className="min-w-0 flex-1 truncate font-mono text-[length:var(--text-md)] text-text">
            {formatArtifactType(item.type)}
          </span>
        </div>
      ))}
    </div>
  );
}

function DetailSubhead({ children }: { children: ReactNode }) {
  return (
    <h3 className="mb-1.5 text-[length:var(--text-sm)] font-semibold tracking-[0.08em] text-faint uppercase">
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
  const subject = {
    level: "step",
    component: step.id[0],
    name: step.id[1],
    stepId: step.id,
  };
  const constitution = stepBoundaryModel(index, subject, "dependency");
  const contribution = stepBoundaryModel(index, subject, "contribution");

  return (
    <DetailDocument
      testId="workflow-step-detail"
      concept="step"
      kicker={`Step · ${step.id[0]}`}
      title={step.id[1]}
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
    >


      <DetailBand
        title="Constitution"
        question="Which steps produce what this step reads?"
        testId="step-constitution"
      >
        <Constitution model={constitution} />
      </DetailBand>

      <DetailBand
        title="Contribution"
        question="Which steps read what this step produces?"
        testId="step-contribution"
      >
        <Constitution model={contribution} label="Contribution" />
      </DetailBand>

      <DetailBand
        title="Ports"
        question="Which artifacts does this step open?"
      >
        <div className="grid gap-3 xl:grid-cols-2">
          <div>
            <DetailSubhead>Inputs</DetailSubhead>
            <Openings step={step} direction="input" />
          </div>
          <div>
            <DetailSubhead>Outputs</DetailSubhead>
            <Openings step={step} direction="output" />
          </div>
        </div>
      </DetailBand>

      <DetailBand
        title="Payload"
        question="Which instruction does this step execute?"
      >
        <PayloadFacts step={step} />
      </DetailBand>

      {bindings.length ? (
        <DetailBand
          title="Bindings"
          question="Which record does this step produce?"
        >
          <div className="grid gap-1">
            {bindings.slice(0, 16).map((binding) => (
              <div
                key={binding.index}
                className="flex items-baseline gap-2 border-b border-line-soft py-1 font-mono text-[length:var(--text-md)] last:border-b-0"
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
              <p className="font-mono text-[length:var(--text-xs)] text-faint">
                showing 16 of {bindings.length}
              </p>
            ) : null}
          </div>
        </DetailBand>
      ) : null}

      <InvolvedSteps
        index={index}
        selection={{
          kind: "step",
          component: step.id[0],
          name: step.id[1],
          stepId: step.id,
        }}
      />
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
        kicker="Step"
        title="Step unavailable"
        subtitle="This step is not present in the workflow plan."
      >
        {null}
      </DetailDocument>
    );
  }

  return (
    <div className="h-full" data-testid="workflow-step-editor">
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
        <p className="max-w-[42ch] text-center text-[length:var(--text-xl)] leading-relaxed text-muted">
          This snapshot has no workflow plan.
        </p>
      </div>
    );
  }

  const facts = inStepGroup && stepScene
    ? [
        { label: "Steps", value: `${stepScene.stats?.stepCount ?? 0}` },
        { label: "Boundary", value: `${stepScene.stats?.boundaryCount ?? 0}` },
      ]
    : [
        { label: "Steps", value: `${model.steps}` },
        { label: "Connections", value: `${model.connections}` },
        {
          label: "Components",
          value: `${activeComponents.size} / ${componentMap.nodes.length}`,
        },
      ];

  return (
    <ViewportFrame
      concept="workflow"
      kicker={inStepGroup ? "Workflow · Step group" : "Workflow"}
      title={inStepGroup ? (focusedNode?.id ?? "Step group") : "Compositor"}
      facts={facts}
      factsTestId={
        inStepGroup && stepScene ? "workflow-step-group-label" : undefined
      }
      testId="workflow-editor"
      actionsTestId="workflow-toolbar"
      bodyRef={containerRef}
      bodyTestId="workflow-canvas"
      bodyClassName="cursor-grab touch-none"
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
      nav={
        <ViewportNav
          zoom={view.scale}
          onZoomOut={() => zoomBy(1 / 1.25)}
          onZoomIn={() => zoomBy(1.25)}
          onFit={fitView}
          label="workflow"
          testIds={{
            out: "workflow-zoom-out",
            value: "workflow-zoom",
            in: "workflow-zoom-in",
            fit: "workflow-fit",
          }}
        />
      }
      actions={
        <>
          {inStepGroup && stepScene ? (
            <>
              {selectedStepRow ? (
                <ViewportAction
                  emphasis
                  onClick={() => openStepNode(selectedStepRow, false)}
                  data-testid="workflow-open-step"
                >
                  Open step →
                </ViewportAction>
              ) : selectedBoundaryNode?.component ? (
                <ViewportAction
                  emphasis
                  onClick={() =>
                    store.focusComponent(selectedBoundaryNode.component)
                  }
                  data-testid="workflow-open-step-group"
                >
                  Open {selectedBoundaryNode.component} step group →
                </ViewportAction>
              ) : null}
              <ViewportAction
                onClick={() => store.focusComponent(undefined)}
                data-testid="workflow-back-components"
              >
                ← Components
              </ViewportAction>
            </>
          ) : selectedNode ? (
            <ViewportAction
              emphasis
              onClick={() => store.focusComponent(selectedNode.id)}
              data-testid="workflow-open-step-group"
            >
              Open step group →
            </ViewportAction>
          ) : null}
        </>
      }
    >
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
            <WorkflowDagSceneView
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

        {inStepGroup && stepScene && (stepScene.stats?.stepCount ?? 0) === 0 ? (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <p className="border border-line-soft bg-panel/95 px-3 py-2 font-mono text-[length:var(--text-xl)] text-muted">
              No steps match the current query and instruction filters.
            </p>
          </div>
        ) : null}

        <div className="pointer-events-none absolute top-2 left-2 z-10 max-w-[calc(100%-16px)]">
          <WorkflowControls state={props.state} actions={props.actions} />
        </div>

        <ViewportHint className="pointer-events-none">
          {inStepGroup
            ? "drag to pan · wheel to zoom · double-click a step to open"
            : "drag to pan · wheel to zoom"}
        </ViewportHint>

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
    </ViewportFrame>
  );
}
