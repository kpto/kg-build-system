/**
 * Impact radius for a graph subject.
 *
 * A property impact is the union of the lineage branches for that property. A
 * node or edge impact is the union of its property impacts. A workflow subject
 * walks the connection graph transitively in both directions. The result answers
 * "if I change this, what is upstream and what breaks downstream?" without
 * executing the build.
 */

import type {
  EntityKind,
  IndexedBinding,
  StepId,
  ViewerIndex,
  WorkflowStep,
} from "./types";
import type { AuditSubject, Impact } from "./reviewTypes";
import {
  relationNamesFromRowSource,
  resolveAssetName,
  stepKey,
} from "./indexes";
import { collectFieldRefs, fieldRefKey } from "./expressions";
import { buildLineage, propertySelection } from "./lineage";

const TERMINAL_COMPONENTS = new Set(["file", "meta_graph", "neo4j"]);
const MAX_DEPTH = 40;

interface ImpactCore {
  upstream: Map<string, WorkflowStep>;
  downstream: Map<string, WorkflowStep>;
  artifacts: Set<string>;
  targets: Set<string>;
  nodes: Set<string>;
  edges: Set<string>;
}

function emptyCore(): ImpactCore {
  return {
    upstream: new Map(),
    downstream: new Map(),
    artifacts: new Set(),
    targets: new Set(),
    nodes: new Set(),
    edges: new Set(),
  };
}

function addStep(target: Map<string, WorkflowStep>, step: WorkflowStep): void {
  const key = stepKey(step.id);
  if (!target.has(key)) target.set(key, step);
}

function traverse(
  index: ViewerIndex,
  start: WorkflowStep,
  direction: "upstream" | "downstream",
): WorkflowStep[] {
  const visited = new Set<string>([stepKey(start.id)]);
  const result: WorkflowStep[] = [];
  const queue: Array<{ step: WorkflowStep; depth: number }> = [
    { step: start, depth: 0 },
  ];

  while (queue.length) {
    const current = queue.shift() as { step: WorkflowStep; depth: number };
    if (current.depth >= MAX_DEPTH) continue;
    const connections =
      direction === "upstream"
        ? index.incomingByStepId.get(stepKey(current.step.id)) ?? []
        : index.outgoingByStepId.get(stepKey(current.step.id)) ?? [];
    for (const connection of connections) {
      const nextId =
        direction === "upstream"
          ? connection.outputStepId
          : connection.inputStepId;
      const next = index.stepsById.get(stepKey(nextId));
      if (!next) continue;
      const key = stepKey(next.id);
      if (visited.has(key)) continue;
      visited.add(key);
      result.push(next);
      queue.push({ step: next, depth: current.depth + 1 });
    }
  }

  return result;
}

function recordStep(core: ImpactCore, step: WorkflowStep): void {
  for (const output of step.outputs ?? []) {
    core.artifacts.add(output.type.join("."));
  }
  if (
    TERMINAL_COMPONENTS.has(step.id[0]) ||
    (step.outputs ?? []).some((output) => TERMINAL_COMPONENTS.has(output.type[0]))
  ) {
    core.targets.add(step.id[0]);
  }
}

function includeBindingStep(
  index: ViewerIndex,
  core: ImpactCore,
  step: WorkflowStep,
): void {
  addStep(core.upstream, step);
  recordStep(core, step);
  for (const upstream of traverse(index, step, "upstream")) {
    addStep(core.upstream, upstream);
    recordStep(core, upstream);
  }
  for (const downstream of traverse(index, step, "downstream")) {
    addStep(core.downstream, downstream);
    recordStep(core, downstream);
  }
}

function addPropertyImpact(
  index: ViewerIndex,
  core: ImpactCore,
  kind: EntityKind,
  component: string,
  property: string,
): void {
  const graph = buildLineage(index, propertySelection(kind, component, property));
  for (const branch of graph.branches) {
    if (branch.bindingStep) includeBindingStep(index, core, branch.bindingStep);
    for (const step of branch.upstreamSteps) {
      addStep(core.upstream, step);
      recordStep(core, step);
    }
    for (const step of branch.downstreamSteps) {
      addStep(core.downstream, step);
      recordStep(core, step);
    }
    core.artifacts.add(branch.binding.outputArtifact.join("."));
  }
  if (kind === "node") core.nodes.add(component);
  else core.edges.add(component);
}

function ownerSources(index: ViewerIndex, owner: string): string[] {
  const projection = index.projectionByName.get(owner);
  if (projection) {
    const names = relationNamesFromRowSource(projection.row_source);
    if (names.length) return names;
  }
  return [owner];
}

function bindingReferencesName(
  index: ViewerIndex,
  binding: IndexedBinding,
  matches: (name: string) => boolean,
): boolean {
  for (const expression of Object.values(binding.binding.properties ?? {})) {
    for (const fieldRef of collectFieldRefs(expression)) {
      const owner = fieldRefKey(fieldRef).split(".")[0];
      if (!owner) continue;
      if (matches(owner)) return true;
      if (ownerSources(index, owner).some(matches)) return true;
    }
  }
  for (const relation of relationNamesFromRowSource(binding.binding.rows)) {
    if (matches(relation)) return true;
  }
  return false;
}

function addComponentBindings(
  index: ViewerIndex,
  core: ImpactCore,
  bindings: IndexedBinding[],
): void {
  for (const binding of bindings) {
    if (binding.kind === "node") core.nodes.add(binding.component);
    else core.edges.add(binding.component);
    if (binding.step) includeBindingStep(index, core, binding.step);
  }
}

function bindingForSubject(
  index: ViewerIndex,
  subject: AuditSubject,
): IndexedBinding | undefined {
  if (typeof subject.bindingIndex === "number") {
    return index.bindings.find((binding) => binding.index === subject.bindingIndex);
  }
  const component = subject.component ?? subject.name;
  return index.bindingByComponent.get(component)?.[0];
}

function resolveStep(
  index: ViewerIndex,
  subject: AuditSubject,
): WorkflowStep | undefined {
  if (subject.stepId) {
    const exact = index.stepsById.get(stepKey(subject.stepId));
    if (exact) return exact;
  }
  const slash = subject.name.indexOf("/");
  if (slash >= 0) {
    const id: StepId = [
      subject.name.slice(0, slash),
      subject.name.slice(slash + 1),
    ];
    const exact = index.stepsById.get(stepKey(id));
    if (exact) return exact;
  }
  if (subject.component) {
    const exact = index.stepsById.get(
      stepKey([subject.component, subject.name]),
    );
    if (exact) return exact;
  }
  return index.workflow.steps.find((step) => step.id[1] === subject.name);
}

function recordsFor(
  index: ViewerIndex,
  name: string,
  kind?: EntityKind,
): number | undefined {
  const exact = kind
    ? index.metaGraph.byKey.get(`${kind}\u0000${name}`)
    : undefined;
  const component =
    exact ??
    index.metaGraph.byName.get(name)?.find((candidate) => !kind || candidate.kind === kind) ??
    index.metaGraph.byName.get(name)?.[0];
  const records = component?.counts?.records ?? component?.counts?.inclusive_records;
  return typeof records === "number" ? records : undefined;
}

function finish(core: ImpactCore, subject: AuditSubject, records?: number): Impact {
  const upstream = [...core.upstream.values()]
    .sort((left, right) => stepKey(left.id).localeCompare(stepKey(right.id)))
    .map((step) => [step.id[0], step.id[1]] as StepId);
  const downstream = [...core.downstream.values()]
    .sort((left, right) => stepKey(left.id).localeCompare(stepKey(right.id)))
    .map((step) => [step.id[0], step.id[1]] as StepId);

  return {
    subject,
    upstream,
    downstream,
    artifacts: [...core.artifacts].sort(),
    nodes: [...core.nodes].sort(),
    edges: [...core.edges].sort(),
    targets: [...core.targets].sort(),
    ...(typeof records === "number" ? { records } : {}),
  };
}

const impactCache = new WeakMap<ViewerIndex, Map<string, Impact>>();

function impactKey(subject: AuditSubject): string {
  return [
    subject.kind,
    subject.name,
    subject.component ?? "",
    subject.property ?? "",
    subject.entityKind ?? "",
    subject.bindingIndex ?? "",
    subject.stepId?.join("/") ?? "",
  ].join("\u0000");
}

function computeImpactCore(index: ViewerIndex, subject: AuditSubject): Impact {
  const core = emptyCore();
  const component = subject.component ?? subject.name;

  if (subject.kind === "property") {
    const kind = subject.entityKind ?? "node";
    const property = subject.property ?? subject.name;
    addPropertyImpact(index, core, kind, component, property);
    return finish(core, subject, recordsFor(index, component, kind));
  }

  if (subject.kind === "node" || subject.kind === "edge") {
    const kind: EntityKind = subject.kind;
    const entity =
      kind === "node"
        ? index.topologyNodesByName.get(component)
        : index.topologyEdgesByName.get(component);
    const properties = entity?.properties ?? [];
    if (properties.length) {
      for (const property of properties) {
        addPropertyImpact(index, core, kind, component, property.name);
      }
    } else {
      addComponentBindings(
        index,
        core,
        index.bindingByComponent.get(component) ?? [],
      );
    }
    if (kind === "node") core.nodes.add(component);
    else core.edges.add(component);
    return finish(core, subject, recordsFor(index, component, kind));
  }

  if (subject.kind === "step") {
    const step = resolveStep(index, subject);
    if (step) includeBindingStep(index, core, step);
    return finish(core, subject, recordsFor(index, subject.name));
  }

  if (subject.kind === "binding") {
    const binding = bindingForSubject(index, subject);
    if (binding) addComponentBindings(index, core, [binding]);
    return finish(core, subject, recordsFor(index, binding?.component ?? component));
  }

  if (subject.kind === "asset") {
    const bindings = index.bindings.filter((binding) =>
      bindingReferencesName(
        index,
        binding,
        (name) => resolveAssetName(index, name) === component || name === component,
      ),
    );
    addComponentBindings(index, core, bindings);
    return finish(core, subject, recordsFor(index, component));
  }

  // relation and projection
  const bindings = index.bindings.filter((binding) =>
    bindingReferencesName(
      index,
      binding,
      (name) => name === component || name === subject.name,
    ),
  );
  addComponentBindings(index, core, bindings);
  return finish(core, subject, recordsFor(index, component));
}

/**
 * Memoised impact query.
 *
 * A blueprint card renders one badge per property; without this cache the same
 * component is traversed hundreds of times on first paint. The viewer index and
 * its snapshot are immutable, so an Impact value is safe to reuse.
 */
export function computeImpact(index: ViewerIndex, subject: AuditSubject): Impact {
  let cache = impactCache.get(index);
  if (!cache) {
    cache = new Map();
    impactCache.set(index, cache);
  }
  const key = impactKey(subject);
  const hit = cache.get(key);
  if (hit) return hit;
  const result = computeImpactCore(index, subject);
  cache.set(key, result);
  return result;
}

/** Component-level impact used by dense property rows. */
export function componentImpact(
  index: ViewerIndex,
  kind: EntityKind,
  component: string,
): Impact {
  return computeImpact(index, {
    kind,
    name: component,
    component,
    entityKind: kind,
  });
}
