/**
 * Snapshot diff.
 *
 * The comparison is structural and order-independent: values are normalised to
 * sorted JSON, connections go through the same opening normalisation as the
 * index layer, and every emitted array is sorted so a review can be re-run and
 * compared byte for byte.
 */

import type {
  BindingDTO,
  StepId,
  ViewerSnapshot,
  WorkflowConnection,
  WorkflowStep,
} from "./types";
import type { SnapshotDiff } from "./reviewTypes";
import { normalizeConnection } from "./indexes";

function stableValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stableValue);
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    const sorted: Record<string, unknown> = {};
    for (const key of Object.keys(record).sort()) sorted[key] = stableValue(record[key]);
    return sorted;
  }
  return value;
}

function stableStringify(value: unknown): string {
  try {
    return JSON.stringify(stableValue(value));
  } catch {
    return String(value);
  }
}

function stepKey(step: StepId): string {
  return step.join("\u0000");
}

function sortSteps(steps: StepId[]): StepId[] {
  const byKey = new Map<string, StepId>();
  for (const step of steps) byKey.set(stepKey(step), [step[0], step[1]]);
  return [...byKey.values()].sort((left, right) =>
    stepKey(left).localeCompare(stepKey(right)),
  );
}

function stepMap(snapshot: ViewerSnapshot): Map<string, WorkflowStep> {
  const map = new Map<string, WorkflowStep>();
  for (const step of snapshot.workflow?.steps ?? []) map.set(stepKey(step.id), step);
  return map;
}

function connectionKey(connection: WorkflowConnection): string {
  const normalized = normalizeConnection(
    { input: connection.input, output: connection.output },
    0,
  );
  const output = [
    normalized.output.component,
    normalized.output.step,
    normalized.output.direction,
    normalized.output.openingName,
  ].join("/");
  const input = [
    normalized.input.component,
    normalized.input.step,
    normalized.input.direction,
    normalized.input.openingName,
  ].join("/");
  return `${output}->${input}`;
}

function topologyMap(snapshot: ViewerSnapshot): Map<string, string> {
  const map = new Map<string, string>();
  for (const node of snapshot.blueprint?.graph?.nodes ?? []) {
    map.set(`node:${node.name}`, stableStringify(node));
  }
  for (const edge of snapshot.blueprint?.graph?.edges ?? []) {
    map.set(`edge:${edge.name}`, stableStringify(edge));
  }
  return map;
}

function bindingComponent(binding: BindingDTO): string {
  const ref = binding.kind === "node" ? binding.node : binding.edge;
  return ref?.[2] ?? "";
}

function bindingKey(binding: BindingDTO, index: number): string {
  return `${binding.kind}:${bindingComponent(binding)}:${index}`;
}

function bindingMap(snapshot: ViewerSnapshot): Map<string, { index: number; binding: BindingDTO }> {
  const map = new Map<string, { index: number; binding: BindingDTO }>();
  (snapshot.blueprint?.bindings ?? []).forEach((binding, index) => {
    map.set(bindingKey(binding, index), { index, binding });
  });
  return map;
}

export function diffSnapshots(
  base: ViewerSnapshot,
  next: ViewerSnapshot,
): SnapshotDiff {
  // Steps -----------------------------------------------------------------
  const baseSteps = stepMap(base);
  const nextSteps = stepMap(next);
  const stepsAdded: StepId[] = [];
  const stepsRemoved: StepId[] = [];
  const stepsChanged: StepId[] = [];

  for (const [key, step] of nextSteps) {
    const before = baseSteps.get(key);
    if (!before) {
      stepsAdded.push(step.id);
    } else if (stableStringify(before) !== stableStringify(step)) {
      stepsChanged.push(step.id);
    }
  }
  for (const [key, step] of baseSteps) {
    if (!nextSteps.has(key)) stepsRemoved.push(step.id);
  }

  // Connections -----------------------------------------------------------
  const baseConnections = new Set(
    (base.workflow?.connections ?? []).map(connectionKey),
  );
  const nextConnections = new Set(
    (next.workflow?.connections ?? []).map(connectionKey),
  );
  const connectionsAdded = [...nextConnections]
    .filter((key) => !baseConnections.has(key))
    .sort();
  const connectionsRemoved = [...baseConnections]
    .filter((key) => !nextConnections.has(key))
    .sort();

  // Topology --------------------------------------------------------------
  const baseTopology = topologyMap(base);
  const nextTopology = topologyMap(next);
  const addedTopologyKeys = [...nextTopology.keys()].filter(
    (key) => !baseTopology.has(key),
  );
  const removedTopologyKeys = [...baseTopology.keys()].filter(
    (key) => !nextTopology.has(key),
  );
  // The summary distinguishes nodes from edges; the lists carry navigable
  // names so a UI can jump straight to the subject.
  const topologyName = (key: string) => key.slice(key.indexOf(":") + 1);
  const topologyAdded = [...new Set(addedTopologyKeys.map(topologyName))].sort();
  const topologyRemoved = [...new Set(removedTopologyKeys.map(topologyName))].sort();

  // Bindings --------------------------------------------------------------
  const baseBindings = bindingMap(base);
  const nextBindings = bindingMap(next);
  const bindingsAdded: number[] = [];
  const bindingsRemoved: number[] = [];
  const bindingsChanged: number[] = [];
  let propertiesChanged = 0;

  for (const [key, entry] of nextBindings) {
    const before = baseBindings.get(key);
    if (!before) {
      bindingsAdded.push(entry.index);
      continue;
    }
    if (stableStringify(before.binding) !== stableStringify(entry.binding)) {
      bindingsChanged.push(entry.index);
    }
    const beforeProperties = before.binding.properties ?? {};
    const nextProperties = entry.binding.properties ?? {};
    const propertyNames = new Set([
      ...Object.keys(beforeProperties),
      ...Object.keys(nextProperties),
    ]);
    for (const propertyName of propertyNames) {
      if (
        stableStringify(beforeProperties[propertyName]) !==
        stableStringify(nextProperties[propertyName])
      ) {
        propertiesChanged += 1;
      }
    }
  }
  for (const [key, entry] of baseBindings) {
    if (!nextBindings.has(key)) bindingsRemoved.push(entry.index);
  }

  const count = (keys: string[], prefix: string) =>
    keys.filter((key) => key.startsWith(prefix)).length;

  return {
    summary: {
      stepsAdded: stepsAdded.length,
      stepsRemoved: stepsRemoved.length,
      connectionsAdded: connectionsAdded.length,
      connectionsRemoved: connectionsRemoved.length,
      nodesAdded: count(addedTopologyKeys, "node:"),
      nodesRemoved: count(removedTopologyKeys, "node:"),
      edgesAdded: count(addedTopologyKeys, "edge:"),
      edgesRemoved: count(removedTopologyKeys, "edge:"),
      bindingsAdded: bindingsAdded.length,
      bindingsRemoved: bindingsRemoved.length,
      propertiesChanged,
    },
    steps: {
      added: sortSteps(stepsAdded),
      removed: sortSteps(stepsRemoved),
      changed: sortSteps(stepsChanged),
    },
    connections: {
      added: connectionsAdded,
      removed: connectionsRemoved,
    },
    topology: {
      added: topologyAdded,
      removed: topologyRemoved,
    },
    bindings: {
      added: bindingsAdded.sort((left, right) => left - right),
      removed: bindingsRemoved.sort((left, right) => left - right),
      changed: bindingsChanged.sort((left, right) => left - right),
    },
  };
}

export function hasChanges(diff: SnapshotDiff): boolean {
  return Object.values(diff.summary).some((value) => value > 0);
}
