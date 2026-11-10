import type { StepId, ViewerIndex, WorkflowStep } from "@/lib/types";
import { stepKey } from "@/lib/indexes";

export interface WorkflowFilters {
  query: string;
  /** A component id, or `all`. */
  component: string;
  /** A rendered instruction kind, or `all`. */
  kind: string;
}

export const DEFAULT_WORKFLOW_FILTERS: WorkflowFilters = {
  query: "",
  component: "all",
  kind: "all",
};

export interface WorkflowStepRow {
  key: string;
  id: StepId;
  component: string;
  name: string;
  kind: string[] | undefined;
  kindKey: string;
  kindLabel: string;
  inputs: number;
  outputs: number;
  connections: number;
}

export interface WorkflowKindOption {
  key: string;
  label: string;
  count: number;
}

export interface WorkflowGroup {
  component: string;
  rows: WorkflowStepRow[];
}

export interface WorkflowModel {
  rows: WorkflowStepRow[];
  components: string[];
  kinds: WorkflowKindOption[];
  steps: number;
  connections: number;
}

export function instructionKindLabel(kind: string[] | undefined): string {
  return kind?.length ? kind.join(":") : "unknown";
}

function rowFor(
  index: ViewerIndex,
  step: WorkflowStep,
): WorkflowStepRow {
  const key = stepKey(step.id);
  const kind = step.instruction.kind;
  return {
    key,
    id: step.id,
    component: step.id[0],
    name: step.id[1],
    kind,
    kindKey: instructionKindLabel(kind),
    kindLabel: instructionKindLabel(kind),
    inputs: step.inputs?.length ?? 0,
    outputs: step.outputs?.length ?? 0,
    connections:
      (index.incomingByStepId.get(key)?.length ?? 0) +
      (index.outgoingByStepId.get(key)?.length ?? 0),
  };
}

/** Build the immutable step catalogue for one snapshot. */
export function buildWorkflowModel(index: ViewerIndex): WorkflowModel {
  const rows = (index.workflow.steps ?? []).map((step) => rowFor(index, step));

  const components: string[] = [];
  const seenComponents = new Set<string>();
  for (const component of index.workflow.components ?? []) {
    if (seenComponents.has(component.id)) continue;
    seenComponents.add(component.id);
    components.push(component.id);
  }
  for (const row of rows) {
    if (seenComponents.has(row.component)) continue;
    seenComponents.add(row.component);
    components.push(row.component);
  }

  const kindCounts = new Map<string, number>();
  for (const row of rows) {
    kindCounts.set(row.kindKey, (kindCounts.get(row.kindKey) ?? 0) + 1);
  }
  const kinds = [...kindCounts.entries()]
    .map(([key, count]) => ({ key, label: key, count }))
    .sort((left, right) => left.label.localeCompare(right.label));

  return {
    rows,
    components,
    kinds,
    steps: index.workflow.steps?.length ?? 0,
    connections: index.workflow.connections?.length ?? 0,
  };
}

export function filterWorkflowRows(
  rows: WorkflowStepRow[],
  filters: WorkflowFilters,
): WorkflowStepRow[] {
  const query = filters.query.trim().toLowerCase();
  return rows.filter((row) => {
    if (filters.component !== "all" && row.component !== filters.component) {
      return false;
    }
    if (filters.kind !== "all" && row.kindKey !== filters.kind) return false;
    if (!query) return true;
    return (
      row.name.toLowerCase().includes(query) ||
      row.component.toLowerCase().includes(query) ||
      row.kindLabel.toLowerCase().includes(query)
    );
  });
}

/** Preserve snapshot order while grouping the visible rows by component. */
export function groupWorkflowRows(rows: WorkflowStepRow[]): WorkflowGroup[] {
  const groups = new Map<string, WorkflowStepRow[]>();
  for (const row of rows) {
    const group = groups.get(row.component) ?? [];
    group.push(row);
    groups.set(row.component, group);
  }
  return [...groups.entries()].map(([component, groupRows]) => ({
    component,
    rows: groupRows,
  }));
}

export function formatStepId(id: StepId): string {
  return id.join(" / ");
}

export function formatOpening(opening: string[] | undefined): string {
  return opening?.length ? opening.join(".") : "—";
}

export function formatArtifactType(type: string[] | undefined): string {
  return type?.length ? type.join(":") : "—";
}
