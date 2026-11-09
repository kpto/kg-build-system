import type { DiagnosisInput } from "@/shared/model/builders";
import type { CampaignView, Grouping } from "@/shared/model/campaign";
import type { AuditFinding, Severity } from "@/lib/reviewTypes";
import type { StepId, ViewerIndex, WorkflowStep } from "@/lib/types";
import { stepKey } from "@/lib/indexes";
import {
  buildStepAuditMap,
  summarizeGroupAudit,
  subjectSteps,
  type StepAuditSummary,
} from "@/diagnosis/execution/model/stepAudit";
import { subjectFromSelection } from "@/diagnosis/model/selection";
import type {
  ExecutionAuditModel,
  ExecutionConnectionModel,
  ExecutionGroupModel,
  ExecutionLegendItem,
  ExecutionModel,
  ExecutionSocketModel,
  ExecutionStepDetailModel,
  ExecutionStepModel,
  ExecutionTraceState,
} from "@/diagnosis/execution/model/ExecutionModel";

const HINT_TEXT =
  "pan or use the Outliner to follow the flow · click a step to inspect";

const AUDIT_LEGEND: ExecutionLegendItem[] = [
  { severity: "critical", label: "critical" },
  { severity: "high", label: "high" },
  { severity: "medium", label: "medium" },
  { severity: "low", label: "low" },
  { severity: "info", label: "info" },
];

const EMPTY_AUDIT: ExecutionAuditModel = { count: 0, findings: [] };

interface GroupEntry {
  key: string;
  label: string;
  steps: WorkflowStep[];
}

function groupOf(
  step: WorkflowStep,
  mode: Grouping,
): { key: string; label: string } {
  if (mode === "component") {
    return { key: `component:${step.id[0]}`, label: step.id[0] };
  }
  const emitter = step.instruction.kind.join(":");
  return { key: `emitter:${emitter}`, label: emitter };
}

function buildGroups(index: ViewerIndex, mode: Grouping): GroupEntry[] {
  const groups = new Map<string, GroupEntry>();
  for (const step of index.steps) {
    const group = groupOf(step, mode);
    const existing = groups.get(group.key) ?? { ...group, steps: [] };
    existing.steps.push(step);
    groups.set(group.key, existing);
  }
  return [...groups.values()];
}

/** Every step whose output/input path touches the focused step. */
function traceStepKeys(index: ViewerIndex, focusStepId: StepId): Set<string> {
  const focusKey = stepKey(focusStepId);
  const visited = new Set<string>([focusKey]);
  const queue: StepId[] = [focusStepId];

  while (queue.length) {
    const id = queue.shift() as StepId;
    const key = stepKey(id);
    const neighbours: StepId[] = [
      ...(index.incomingByStepId.get(key) ?? []).map(
        (connection) => connection.outputStepId,
      ),
      ...(index.outgoingByStepId.get(key) ?? []).map(
        (connection) => connection.inputStepId,
      ),
    ];
    for (const neighbour of neighbours) {
      const neighbourKey = stepKey(neighbour);
      if (visited.has(neighbourKey)) continue;
      visited.add(neighbourKey);
      queue.push(neighbour);
    }
  }

  return visited;
}

function runtimeFieldText(field: string | Record<string, unknown>): string {
  if (typeof field === "string") return field;
  const key = typeof field.key === "string" ? field.key : "runtime field";
  const valueType =
    typeof field.value_type === "string" ? field.value_type : "unknown type";
  const required = field.required === true ? "required" : "optional";
  const description =
    typeof field.description === "string" && field.description.trim()
      ? `: ${field.description}`
      : "";
  return `${key} (${valueType}, ${required})${description}`;
}

function socketsFrom(
  openings: Array<{ opening_name?: string[]; type: string[] }> | undefined,
  direction: "input" | "output",
): ExecutionSocketModel[] {
  return (openings ?? []).map((opening) => {
    const localName = opening.opening_name?.join(".") || "opening";
    return {
      label: localName,
      title: `${direction} ${localName} — ${opening.type.join(".")}`,
    };
  });
}

function stepDetail(
  index: ViewerIndex,
  step: WorkflowStep,
  findings: AuditFinding[],
): ExecutionStepDetailModel {
  const key = stepKey(step.id);
  const component = index.componentsById.get(step.id[0]);
  const incoming = index.incomingByStepId.get(key) ?? [];
  const outgoing = index.outgoingByStepId.get(key) ?? [];
  const artifactTypes = [
    ...new Set([
      ...(step.inputs ?? []).map((input) => input.type.join(".")),
      ...(step.outputs ?? []).map((output) => output.type.join(".")),
    ]),
  ];

  return {
    stepId: step.id,
    ...(component?.version ? { componentVersion: String(component.version) } : {}),
    runtimeFields: (component?.runtime_fields ?? []).map(runtimeFieldText),
    instructionKind: step.instruction.kind.join(":"),
    producerCount: new Set(
      incoming.map((connection) => stepKey(connection.outputStepId)),
    ).size,
    consumerCount: new Set(
      outgoing.map((connection) => stepKey(connection.inputStepId)),
    ).size,
    artifactTypes,
    inputSockets: socketsFrom(step.inputs, "input"),
    outputSockets: socketsFrom(step.outputs, "output"),
    findings,
  };
}

function auditFrom(summary: StepAuditSummary | undefined): ExecutionAuditModel {
  if (!summary) return EMPTY_AUDIT;
  return {
    count: summary.count,
    ...(summary.severity ? { severity: summary.severity } : {}),
    findings: summary.findings,
  };
}

function resolveStep(
  index: ViewerIndex,
  step: WorkflowStep | StepId,
): WorkflowStep | undefined {
  return Array.isArray(step) ? index.stepsById.get(stepKey(step)) : step;
}

/**
 * Build the execution ViewModel from the campaign and the presentation input.
 *
 * Domain decisions live here: grouping, collapse, trace closure, selection,
 * audit evidence and every command. Layout and React Flow live in the view.
 */
export function buildExecutionModel(
  campaign: CampaignView,
  input: DiagnosisInput,
): ExecutionModel {
  const index = campaign.record.index;
  const grouping = input.grouping;
  const groups = buildGroups(index, grouping);
  const stepAudit = buildStepAuditMap(index, campaign.record.audit ?? undefined);
  const subject = subjectFromSelection(campaign.selection, index);
  const subjectStepKeys = (() => {
    const steps = subjectSteps(index, subject);
    return steps.length
      ? new Set(steps.map((step) => stepKey(step.id)))
      : undefined;
  })();

  const traceKeys = input.focusStepId
    ? traceStepKeys(index, input.focusStepId)
    : undefined;
  const focusKey = input.focusStepId ? stepKey(input.focusStepId) : undefined;
  const selectedStepId =
    campaign.selection?.kind === "step" ? campaign.selection.step.id : undefined;
  const selectedStepKey = selectedStepId ? stepKey(selectedStepId) : undefined;

  const selectStep = (step: WorkflowStep | StepId) => {
    const resolved = resolveStep(index, step);
    if (resolved) campaign.commands.selectStep(resolved);
  };
  const traceStep = (step: WorkflowStep | StepId) => {
    const resolved = resolveStep(index, step);
    if (resolved) campaign.commands.focusStep(resolved);
  };
  const reviewStep = (step: WorkflowStep | StepId) => {
    const resolved = resolveStep(index, step);
    if (resolved) campaign.commands.openReviewForStep(resolved);
  };
  const clearTrace = () => campaign.commands.clearFocus();
  const setGrouping = (next: Grouping) => input.setGrouping(next);
  const toggleGroup = (key: string) => input.onToggleGroup(key);
  const collapseAll = () => input.onToggleAll(true);
  const expandAll = () => input.onToggleAll(false);

  const groupModels: ExecutionGroupModel[] = groups.map((group) => {
    const groupTouchesTrace = Boolean(
      traceKeys &&
        group.steps.some((step) => traceKeys.has(stepKey(step.id))),
    );
    const requestedCollapsed = input.collapsedGroups.has(group.key);
    const collapsed = requestedCollapsed && !groupTouchesTrace;
    const groupActive = Boolean(traceKeys && groupTouchesTrace);
    const groupDim = Boolean(traceKeys) && !groupActive;

    const steps: ExecutionStepModel[] = group.steps.map((step) => {
      const key = stepKey(step.id);
      const summary = stepAudit.get(key);
      const findings = summary?.findings ?? [];
      const traceState: ExecutionTraceState | undefined = traceKeys
        ? key === focusKey
          ? "focus"
          : traceKeys.has(key)
            ? "path"
            : "dim"
        : undefined;

      return {
        key,
        id: step.id,
        label: step.id[1],
        component: step.id[0],
        emitter: step.instruction.kind.join(":"),
        artifacts: (step.outputs ?? []).map((output) => output.type.join(".")),
        inputSockets: socketsFrom(step.inputs, "input"),
        outputSockets: socketsFrom(step.outputs, "output"),
        selected: key === selectedStepKey,
        subjectMatched: subjectStepKeys?.has(key) ?? false,
        ...(traceState ? { traceState } : {}),
        audit: auditFrom(summary),
        detail: stepDetail(index, step, findings),
        commands: {
          select: () => selectStep(step),
          trace: () => traceStep(step),
          review: () => reviewStep(step),
        },
      };
    });

    return {
      key: group.key,
      label: group.label,
      grouping,
      steps,
      count: group.steps.length,
      collapsed,
      requestedCollapsed,
      lockedOpen: requestedCollapsed && groupTouchesTrace,
      // The frame never claims focus; the trace state already dims inactive
      // groups. Keeping this false preserves the reference behaviour.
      focused: false,
      ...(groupDim ? { traceState: "dim" as const } : {}),
      audit: auditFrom(summarizeGroupAudit(stepAudit, group.steps)),
      commands: {
        toggle: () => toggleGroup(group.key),
      },
    };
  });

  const endpointIsActive = (stepId: StepId): boolean =>
    Boolean(traceKeys && traceKeys.has(stepKey(stepId)));

  const connectionMap = new Map<string, ExecutionConnectionModel>();
  for (const connection of index.connections) {
    const sourceKey = stepKey(connection.outputStepId);
    const targetKey = stepKey(connection.inputStepId);
    const id = `${sourceKey}->${targetKey}`;
    if (connectionMap.has(id)) continue;

    const active =
      (endpointIsActive(connection.outputStepId) &&
        endpointIsActive(connection.inputStepId)) ||
      Boolean(
        selectedStepKey &&
          (sourceKey === selectedStepKey || targetKey === selectedStepKey),
      );
    const dimmed = Boolean(traceKeys) && !active;

    connectionMap.set(id, {
      id,
      sourceStepId: connection.outputStepId,
      targetStepId: connection.inputStepId,
      sourceKey,
      targetKey,
      active,
      dimmed,
    });
  }

  const allCollapsed =
    groupModels.length > 0 &&
    groupModels.every((group) => {
      const touchesTrace = Boolean(
        traceKeys &&
          group.steps.some((step) => traceKeys.has(step.key)),
      );
      return group.requestedCollapsed && !touchesTrace;
    });

  const steps = groupModels.flatMap((group) => group.steps);

  return {
    id: "execution",
    title: "Execution",
    question: "what runs, in what order, and through which artifacts?",
    hint: HINT_TEXT,
    graph: {
      groups: groupModels,
      steps,
      connections: [...connectionMap.values()],
      grouping,
      ...(selectedStepId ? { selectedStepId } : {}),
      trace: {
        active: Boolean(traceKeys),
        ...(input.focusStepId ? { focusStepId: input.focusStepId } : {}),
        ...(focusKey ? { focusKey } : {}),
        stepKeys: traceKeys ?? new Set<string>(),
      },
      allCollapsed,
      commands: {
        selectStep,
        traceStep,
        reviewStep,
        clearTrace,
      },
    },
    overlay: {
      id: "execution-overlay",
      label: "Group by",
      grouping: {
        label: "Group by",
        ariaLabel: "Group execution graph by",
        options: [
          {
            id: "component",
            label: "Component",
            active: grouping === "component",
            command: () => setGrouping("component"),
          },
          {
            id: "emitter",
            label: "Instruction",
            active: grouping === "emitter",
            command: () => setGrouping("emitter"),
          },
        ],
      },
      actions: [
        {
          id: "collapse-all",
          label: "Collapse all",
          title: "Collapse all workflow groups",
          icon: "collapse",
          run: collapseAll,
        },
        {
          id: "expand-all",
          label: "Expand all",
          title: "Expand all workflow groups",
          icon: "expand",
          run: expandAll,
        },
      ],
    },
    auditLegend: AUDIT_LEGEND,
    commands: {
      selectStep,
      traceStep,
      reviewStep,
      clearTrace,
      setGrouping,
      toggleGroup,
      collapseAll,
      expandAll,
    },
  };
}
