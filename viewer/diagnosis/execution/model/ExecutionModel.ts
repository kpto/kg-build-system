import type { Grouping } from "@/shared/model/campaign";
import type { ActionModel } from "@/shared/model/hierarchy";
import type { AuditFinding, Severity } from "@/lib/reviewTypes";
import type { StepId, WorkflowStep } from "@/lib/types";

export { buildExecutionModel } from "@/diagnosis/execution/model/buildExecutionModel";

export type ExecutionTraceState = "focus" | "path" | "dim";

/** A named opening on a step card. The view decides whether to draw a handle. */
export interface ExecutionSocketModel {
  label: string;
  title: string;
}

/** The audit evidence attached to one step or one group. */
export interface ExecutionAuditModel {
  count: number;
  severity?: Severity;
  findings: AuditFinding[];
}

/** The detail popover's facts. Its commands live on the step model. */
export interface ExecutionStepDetailModel {
  stepId: StepId;
  componentVersion?: string;
  runtimeFields: string[];
  instructionKind: string;
  producerCount: number;
  consumerCount: number;
  artifactTypes: string[];
  inputSockets: ExecutionSocketModel[];
  outputSockets: ExecutionSocketModel[];
  findings: AuditFinding[];
}

/**
 * One workflow step in the execution projection.
 *
 * The model owns selection, trace state, audit evidence and the commands. A
 * view only decides how to draw the step and where to place it.
 */
export interface ExecutionStepModel {
  key: string;
  id: StepId;
  label: string;
  component: string;
  emitter: string;
  artifacts: string[];
  inputSockets: ExecutionSocketModel[];
  outputSockets: ExecutionSocketModel[];
  selected: boolean;
  subjectMatched: boolean;
  traceState?: ExecutionTraceState;
  audit: ExecutionAuditModel;
  detail: ExecutionStepDetailModel;
  commands: {
    select: () => void;
    trace: () => void;
    review: () => void;
  };
}

/**
 * One grouping bucket. `collapsed` is the effective state: a trace locks a
 * group open even when the author asked for it to be collapsed.
 */
export interface ExecutionGroupModel {
  key: string;
  label: string;
  grouping: Grouping;
  steps: ExecutionStepModel[];
  count: number;
  collapsed: boolean;
  requestedCollapsed: boolean;
  lockedOpen: boolean;
  focused: boolean;
  traceState?: ExecutionTraceState;
  audit: ExecutionAuditModel;
  commands: {
    toggle: () => void;
  };
}

/** One step-to-step connection, independent of the visible group shape. */
export interface ExecutionConnectionModel {
  id: string;
  sourceStepId: StepId;
  targetStepId: StepId;
  sourceKey: string;
  targetKey: string;
  active: boolean;
  dimmed: boolean;
}

export interface ExecutionTraceModel {
  active: boolean;
  focusStepId?: StepId;
  focusKey?: string;
  stepKeys: ReadonlySet<string>;
}

/** The workflow graph projection consumed by the execution canvas. */
export interface ExecutionGraphModel {
  groups: ExecutionGroupModel[];
  steps: ExecutionStepModel[];
  connections: ExecutionConnectionModel[];
  grouping: Grouping;
  selectedStepId?: StepId;
  trace: ExecutionTraceModel;
  allCollapsed: boolean;
  commands: {
    selectStep: (step: WorkflowStep | StepId) => void;
    traceStep: (step: WorkflowStep | StepId) => void;
    reviewStep: (step: WorkflowStep | StepId) => void;
    clearTrace: () => void;
  };
}

export interface ExecutionGroupingOptionModel {
  id: Grouping;
  label: string;
  active: boolean;
  command: () => void;
}

/** The controls drawn over the canvas: grouping and the collapse switch. */
export interface ExecutionOverlayModel {
  id: string;
  label: string;
  grouping: {
    label: string;
    ariaLabel: string;
    options: ExecutionGroupingOptionModel[];
  };
  actions: ActionModel[];
}

export interface ExecutionLegendItem {
  severity: Severity;
  label: string;
}

/** The framework-agnostic execution ViewModel. */
export interface ExecutionModel {
  id: "execution";
  title: "Execution";
  question: string;
  hint: string;
  graph: ExecutionGraphModel;
  overlay: ExecutionOverlayModel;
  auditLegend: ExecutionLegendItem[];
  commands: {
    selectStep: (step: WorkflowStep | StepId) => void;
    traceStep: (step: WorkflowStep | StepId) => void;
    reviewStep: (step: WorkflowStep | StepId) => void;
    clearTrace: () => void;
    setGrouping: (grouping: Grouping) => void;
    toggleGroup: (key: string) => void;
    collapseAll: () => void;
    expandAll: () => void;
  };
}
