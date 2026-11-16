import type {
  ArtifactType,
  AssetProfileDTO,
  BindingDTO,
  BlueprintDTO,
  EntityKind,
  FieldLocation,
  GraphDeclarationDTO,
  IndexedBinding,
  NormalizedConnection,
  OpeningRef,
  ProjectionDTO,
  PropertyLookupEntry,
  Ref,
  RelationDTO,
  SearchRecord,
  SemanticSubject,
  SemanticSubjectKind,
  SemanticsDTO,
  StepId,
  StructDTO,
  TopologyEdge,
  TopologyNode,
  TopologyProperty,
  ViewerIndex,
  ViewerSnapshot,
  ViewerStats,
  WorkflowComponent,
  WorkflowPlan,
  WorkflowStep,
} from "./types";
import { buildMetaGraphIndex } from "./annotations";
import { collectFieldRefs, fieldRefKey, refKey } from "./expressions";
import { buildSearchRecords } from "./search";

/** Stable key for a workflow step identity. */
export function stepKey(id: StepId | readonly string[]): string {
  return refKey(id);
}

/** Stable key for a blueprint artifact type. */
export function artifactKey(type: ArtifactType | readonly string[] | undefined): string {
  return refKey(type);
}

/** Stable key for a topology property ref. */
export function propertyRefKey(ref: Ref | readonly string[] | undefined): string {
  return refKey(ref);
}

export function propertySelectionKey(
  kind: EntityKind,
  component: string,
  property: string,
): string {
  return `${kind}\u0000${component}\u0000${property}`;
}

/**
 * Deterministic viewer-side key for a semantic subject.
 *
 * The key is not a framework claim reference: it only identifies the subject
 * whose attached units are being read.
 */
export function semanticSubjectKey(
  kind: SemanticSubjectKind,
  ...segments: Array<string | number>
): string {
  return [kind, ...segments.map((segment) => String(segment))].join("\u0000");
}

/** Human-readable artifact type, e.g. `core.data.table.surveys`. */
export function artifactDisplay(type: ArtifactType | readonly string[] | undefined): string {
  return type ? type.join(".") : "";
}

function openingRef(parts: readonly string[]): OpeningRef {
  const raw = [...parts];
  const component = raw[0] ?? "";
  const step = raw[1] ?? "";
  const direction = raw[2] ?? "";
  const opening = raw.slice(3);
  const stepId: StepId = [component, step];
  return {
    raw,
    component,
    step,
    direction,
    opening,
    openingName: opening.join("."),
    key: refKey(raw),
    stepId,
    stepKey: stepKey(stepId),
  };
}

/** Normalize a raw workflow connection's input and output opening tuples. */
export function normalizeConnection(
  connection: { input: string[]; output: string[] },
  index: number,
): NormalizedConnection {
  const input = openingRef(connection.input);
  const output = openingRef(connection.output);
  return {
    id: `connection:${index}`,
    input,
    output,
    inputStepId: input.stepId,
    outputStepId: output.stepId,
    inputKey: input.key,
    outputKey: output.key,
  };
}

/**
 * Match a normalized connection opening against a step-local opening.
 *
 * A step declares only its local opening name (for example `["output"]` or
 * `["projection.defect"]`). A connection carries the full prefix
 * `[component, step, direction, ...opening_name]`. Matching therefore compares
 * component, step and direction exactly, then treats the step opening as a
 * prefix of the connection opening. A single producer can therefore feed many
 * consumers whose input openings carry different type suffixes.
 */
export function openingMatchesStep(
  opening: OpeningRef,
  stepId: StepId,
  direction: "input" | "output",
  localOpening: readonly string[] = [],
): boolean {
  if (
    opening.component !== stepId[0] ||
    opening.step !== stepId[1] ||
    opening.direction !== direction
  ) {
    return false;
  }
  return (
    localOpening.length <= opening.opening.length &&
    localOpening.every((value, index) => value === opening.opening[index])
  );
}

/** Connections entering a step, optionally restricted to one declared opening. */
export function stepInputConnections(
  index: ViewerIndex,
  stepId: StepId,
  localOpening?: readonly string[],
): NormalizedConnection[] {
  const connections = index.incomingByStepId.get(stepKey(stepId)) ?? [];
  if (!localOpening) return connections;
  return connections.filter((connection) =>
    openingMatchesStep(connection.input, stepId, "input", localOpening),
  );
}

/** Connections leaving a step, optionally restricted to one declared opening. */
export function stepOutputConnections(
  index: ViewerIndex,
  stepId: StepId,
  localOpening?: readonly string[],
): NormalizedConnection[] {
  const connections = index.outgoingByStepId.get(stepKey(stepId)) ?? [];
  if (!localOpening) return connections;
  return connections.filter((connection) =>
    openingMatchesStep(connection.output, stepId, "output", localOpening),
  );
}

function buildWorkflowIndexes(
  workflow: WorkflowPlan,
  steps: WorkflowStep[],
): Pick<
  ViewerIndex,
  | "stepsById"
  | "stepIdByKey"
  | "componentsById"
  | "stepsByComponent"
  | "stepsByEmitter"
  | "connections"
  | "incomingByStepId"
  | "outgoingByStepId"
  | "producersByArtifactKey"
  | "producerByArtifactKey"
> {
  const stepsById = new Map<string, WorkflowStep>();
  const stepIdByKey = new Map<string, StepId>();
  const componentsById = new Map<string, WorkflowComponent>();
  const stepsByComponent = new Map<string, WorkflowStep[]>();
  const stepsByEmitter = new Map<string, WorkflowStep[]>();
  const producersByArtifactKey = new Map<string, WorkflowStep[]>();
  const producerByArtifactKey = new Map<string, WorkflowStep>();

  for (const component of workflow.components ?? []) {
    componentsById.set(component.id, component);
    if (!stepsByComponent.has(component.id)) stepsByComponent.set(component.id, []);
  }

  for (const step of steps) {
    const key = stepKey(step.id);
    stepsById.set(key, step);
    stepIdByKey.set(key, step.id);

    const componentSteps = stepsByComponent.get(step.id[0]) ?? [];
    componentSteps.push(step);
    stepsByComponent.set(step.id[0], componentSteps);

    const emitter = (step.instruction.kind ?? []).join(":");
    const emitterSteps = stepsByEmitter.get(emitter) ?? [];
    emitterSteps.push(step);
    stepsByEmitter.set(emitter, emitterSteps);

    for (const output of step.outputs ?? []) {
      const keyForArtifact = artifactKey(output.type);
      const producers = producersByArtifactKey.get(keyForArtifact) ?? [];
      producers.push(step);
      producersByArtifactKey.set(keyForArtifact, producers);
      if (!producerByArtifactKey.has(keyForArtifact)) {
        producerByArtifactKey.set(keyForArtifact, step);
      }
    }
  }

  const connections = (workflow.connections ?? []).map((connection, index) =>
    normalizeConnection(connection, index),
  );
  const incomingByStepId = new Map<string, NormalizedConnection[]>();
  const outgoingByStepId = new Map<string, NormalizedConnection[]>();

  for (const connection of connections) {
    const targetKey = stepKey(connection.inputStepId);
    const sourceKey = stepKey(connection.outputStepId);
    const incoming = incomingByStepId.get(targetKey) ?? [];
    incoming.push(connection);
    incomingByStepId.set(targetKey, incoming);

    const outgoing = outgoingByStepId.get(sourceKey) ?? [];
    outgoing.push(connection);
    outgoingByStepId.set(sourceKey, outgoing);
  }

  return {
    stepsById,
    stepIdByKey,
    componentsById,
    stepsByComponent,
    stepsByEmitter,
    connections,
    incomingByStepId,
    outgoingByStepId,
    producersByArtifactKey,
    producerByArtifactKey,
  };
}

function resolveBindingStep(
  index: number,
  component: string,
  steps: WorkflowStep[],
  producerByArtifactKey: Map<string, WorkflowStep>,
): WorkflowStep | undefined {
  const expected: ArtifactType = ["core", "binding", component, String(index)];
  const exact = producerByArtifactKey.get(artifactKey(expected));
  if (exact) return exact;

  // Some producers emit a component-scoped binding artifact without the
  // global binding index. Prefer it over a name-only fallback.
  const componentArtifacts = steps.filter((step) =>
    step.outputs?.some(
      (output) =>
        output.type[0] === "core" &&
        output.type[1] === "binding" &&
        output.type[2] === component,
    ),
  );
  if (componentArtifacts.length === 1) return componentArtifacts[0];
  if (componentArtifacts.length > 1) {
    return (
      componentArtifacts.find((step) => step.id[1] === `binding.${index}`) ??
      componentArtifacts[0]
    );
  }

  return (
    steps.find(
      (step) => step.id[0] === "core" && step.id[1] === `binding.${index}`,
    ) ??
    steps.find((step) => step.id[0] === component && step.id[1].includes("binding"))
  );
}

function buildBindings(
  blueprint: BlueprintDTO,
  steps: WorkflowStep[],
  producerByArtifactKey: Map<string, WorkflowStep>,
): IndexedBinding[] {
  return (blueprint.bindings ?? []).map((binding, index) => {
    const componentRef: Ref =
      (binding.kind === "node" ? binding.node : binding.edge) ?? [];
    const component = componentRef[2] ?? "";
    const outputArtifact: ArtifactType = ["core", "binding", component, String(index)];
    return {
      index,
      binding,
      kind: binding.kind,
      component,
      componentRef,
      outputArtifact,
      outputArtifactKey: artifactKey(outputArtifact),
      step: resolveBindingStep(
        index,
        component,
        steps,
        producerByArtifactKey,
      ),
    };
  });
}

function buildFieldIndexes(
  blueprint: BlueprintDTO,
): { fields: FieldLocation[]; fieldsByKey: Map<string, FieldLocation> } {
  const fields: FieldLocation[] = [];
  const fieldsByKey = new Map<string, FieldLocation>();
  const collections: Array<{
    ownerKind: FieldLocation["ownerKind"];
    entries: Array<{ name: string; columns?: Array<FieldLocation["field"]> }>;
  }> = [
    { ownerKind: "relation", entries: blueprint.data?.relations ?? [] },
    { ownerKind: "projection", entries: blueprint.data?.projections ?? [] },
    { ownerKind: "struct", entries: blueprint.data?.structs ?? [] },
  ];

  for (const collection of collections) {
    for (const owner of collection.entries) {
      for (const field of owner.columns ?? []) {
        const key = fieldRefKey(field.ref) || `${owner.name}.${field.name}`;
        const location: FieldLocation = {
          key,
          ownerName: owner.name,
          ownerKind: collection.ownerKind,
          field,
        };
        fields.push(location);
        if (!fieldsByKey.has(key)) fieldsByKey.set(key, location);
      }
    }
  }

  return { fields, fieldsByKey };
}

function collectTopologyProperties(
  blueprint: BlueprintDTO,
): Array<{
  kind: EntityKind;
  component: string;
  property: TopologyProperty;
  componentObject: TopologyNode | TopologyEdge;
}> {
  const result: Array<{
    kind: EntityKind;
    component: string;
    property: TopologyProperty;
    componentObject: TopologyNode | TopologyEdge;
  }> = [];
  for (const node of blueprint.graph?.nodes ?? []) {
    for (const property of node.properties ?? []) {
      result.push({ kind: "node", component: node.name, property, componentObject: node });
    }
  }
  for (const edge of blueprint.graph?.edges ?? []) {
    for (const property of edge.properties ?? []) {
      result.push({ kind: "edge", component: edge.name, property, componentObject: edge });
    }
  }
  return result;
}

function buildPropertyIndex(
  blueprint: BlueprintDTO,
  bindings: IndexedBinding[],
  bindingByComponent: Map<string, IndexedBinding[]>,
): Map<string, PropertyLookupEntry[]> {
  const propertyIndex = new Map<string, PropertyLookupEntry[]>();
  const add = (entry: PropertyLookupEntry) => {
    const key = propertyRefKey(entry.propertyRef);
    const existing = propertyIndex.get(key) ?? [];
    if (
      existing.some(
        (candidate) =>
          candidate.binding.index === entry.binding.index &&
          candidate.component === entry.component,
      )
    ) {
      return;
    }
    existing.push(entry);
    propertyIndex.set(key, existing);
  };

  for (const item of collectTopologyProperties(blueprint)) {
    const componentBindings = bindingByComponent.get(item.component) ?? [];
    for (const binding of componentBindings) {
      const expression = binding.binding.properties?.[item.property.name];
      add({
        component: item.component,
        kind: item.kind,
        property: item.property.name,
        propertyRef: item.property.ref,
        binding,
        expression,
        fieldRefs: collectFieldRefs(expression),
      });
    }
  }

  // A binding may carry a property the topology DTO does not declare. It is
  // still selectable: the ref is synthesised from the topology component.
  for (const binding of bindings) {
    for (const propertyName of Object.keys(binding.binding.properties ?? {})) {
      const propertyRef: Ref = [
        "topology",
        "property",
        `${binding.component}.${propertyName}`,
      ];
      const key = propertyRefKey(propertyRef);
      const alreadyIndexed = (propertyIndex.get(key) ?? []).some(
        (candidate) => candidate.binding.index === binding.index,
      );
      if (alreadyIndexed) continue;
      const expression = binding.binding.properties?.[propertyName];
      add({
        component: binding.component,
        kind: binding.kind,
        property: propertyName,
        propertyRef,
        binding,
        expression,
        fieldRefs: collectFieldRefs(expression),
      });
    }
  }

  return propertyIndex;
}

function graphSemantics(
  declaration: GraphDeclarationDTO,
): SemanticsDTO | undefined {
  const purpose = declaration.semantics.purpose;
  const claims = declaration.semantics.claims;
  if (!purpose && !claims?.length) return undefined;
  return {
    ...(purpose ? { purpose } : {}),
    ...(claims?.length ? { claims } : {}),
  };
}

function buildSemanticIndexes(
  blueprint: BlueprintDTO,
  fields: FieldLocation[],
  bindings: IndexedBinding[],
): Pick<
  ViewerIndex,
  | "semanticSubjects"
  | "semanticsByKey"
  | "semanticsByKind"
  | "assetProfilesByName"
> {
  const semanticSubjects: SemanticSubject[] = [];
  const semanticsByKey = new Map<string, SemanticSubject>();
  const semanticsByKind = new Map<SemanticSubjectKind, SemanticSubject[]>();
  const assetProfilesByName = new Map<string, AssetProfileDTO>();

  const add = (subject: SemanticSubject): void => {
    semanticSubjects.push(subject);
    semanticsByKey.set(subject.key, subject);
    const group = semanticsByKind.get(subject.kind) ?? [];
    group.push(subject);
    semanticsByKind.set(subject.kind, group);
  };

  const declaration = blueprint.graph_declaration;
  if (declaration) {
    add({
      kind: "graph",
      key: semanticSubjectKey("graph", declaration.name),
      name: declaration.name,
      semantics: graphSemantics(declaration),
    });
  }

  for (const asset of blueprint.assets ?? []) {
    if (asset.profile) assetProfilesByName.set(asset.name, asset.profile);
    add({
      kind: "asset",
      key: semanticSubjectKey("asset", asset.name),
      name: asset.name,
      assetName: asset.name,
      semantics: asset.semantics,
    });
  }

  for (const relation of blueprint.data?.relations ?? []) {
    add({
      kind: "relation",
      key: semanticSubjectKey("relation", relation.name),
      name: relation.name,
      semantics: relation.semantics,
    });
  }

  for (const projection of blueprint.data?.projections ?? []) {
    add({
      kind: "projection",
      key: semanticSubjectKey("projection", projection.name),
      name: projection.name,
      semantics: projection.semantics,
    });
  }

  for (const struct of blueprint.data?.structs ?? []) {
    add({
      kind: "struct",
      key: semanticSubjectKey("struct", struct.name),
      name: struct.name,
      semantics: struct.semantics,
    });
  }

  for (const field of fields) {
    add({
      kind: "field",
      key: semanticSubjectKey(
        "field",
        field.ownerKind,
        field.ownerName,
        field.field.name,
      ),
      name: field.field.name,
      ownerName: field.ownerName,
      ref: field.field.ref,
      semantics: field.field.semantics,
    });
  }

  for (const node of blueprint.graph?.nodes ?? []) {
    add({
      kind: "node",
      key: semanticSubjectKey("node", node.name),
      name: node.name,
      ref: ["topology", "node", node.name],
      semantics: node.semantics,
    });
    for (const property of node.properties ?? []) {
      add({
        kind: "property",
        key: semanticSubjectKey("property", "node", node.name, property.name),
        name: property.name,
        ownerName: node.name,
        entityKind: "node",
        ref: property.ref,
        semantics: property.semantics,
      });
    }
  }

  for (const edge of blueprint.graph?.edges ?? []) {
    add({
      kind: "edge",
      key: semanticSubjectKey("edge", edge.name),
      name: edge.name,
      ref: ["topology", "edge", edge.name],
      semantics: edge.semantics,
    });
    for (const property of edge.properties ?? []) {
      add({
        kind: "property",
        key: semanticSubjectKey("property", "edge", edge.name, property.name),
        name: property.name,
        ownerName: edge.name,
        entityKind: "edge",
        ref: property.ref,
        semantics: property.semantics,
      });
    }
  }

  for (const binding of bindings) {
    add({
      kind: "binding",
      key: semanticSubjectKey("binding", binding.index),
      name:
        binding.binding.name ?? `${binding.component}[${binding.index}]`,
      ref: binding.componentRef,
      entityKind: binding.kind,
      bindingIndex: binding.index,
      semantics: binding.binding.semantics,
    });
  }

  return {
    semanticSubjects,
    semanticsByKey,
    semanticsByKind,
    assetProfilesByName,
  };
}

function buildStats(
  blueprint: BlueprintDTO,
  workflow: WorkflowPlan,
  connections: number,
): ViewerStats {
  const topologyProperties = [...(blueprint.graph?.nodes ?? []), ...(blueprint.graph?.edges ?? [])]
    .reduce((total, component) => total + (component.properties?.length ?? 0), 0);
  return {
    assets: blueprint.assets?.length ?? 0,
    tables: blueprint.data?.relations?.length ?? 0,
    projections: blueprint.data?.projections?.length ?? 0,
    structs: blueprint.data?.structs?.length ?? 0,
    topologyNodes: blueprint.graph?.nodes?.length ?? 0,
    topologyEdges: blueprint.graph?.edges?.length ?? 0,
    topologyProperties,
    bindings: blueprint.bindings?.length ?? 0,
    components: workflow.components?.length ?? 0,
    steps: workflow.steps?.length ?? 0,
    connections,
  };
}

/**
 * Build all derived indexes. Every map is a read model over immutable snapshot
 * data; no artifact is mutated.
 */
export function buildViewerIndex(snapshot: ViewerSnapshot): ViewerIndex {
  const blueprint = snapshot.blueprint;
  const workflow = snapshot.workflow;
  const steps = workflow.steps ?? [];
  const workflowIndexes = buildWorkflowIndexes(workflow, steps);
  const bindings = buildBindings(blueprint, steps, workflowIndexes.producerByArtifactKey);

  const bindingByComponent = new Map<string, IndexedBinding[]>();
  const bindingByOutputArtifactKey = new Map<string, IndexedBinding>();
  for (const binding of bindings) {
    const componentBindings = bindingByComponent.get(binding.component) ?? [];
    componentBindings.push(binding);
    bindingByComponent.set(binding.component, componentBindings);
    bindingByOutputArtifactKey.set(binding.outputArtifactKey, binding);
  }

  const topologyNodesByName = new Map<string, TopologyNode>();
  const topologyEdgesByName = new Map<string, TopologyEdge>();
  const topologyComponentsByName = new Map<string, TopologyNode | TopologyEdge>();
  const topologyPropertyByName = new Map<string, TopologyProperty>();
  for (const node of blueprint.graph?.nodes ?? []) {
    topologyNodesByName.set(node.name, node);
    topologyComponentsByName.set(node.name, node);
  }
  for (const edge of blueprint.graph?.edges ?? []) {
    topologyEdgesByName.set(edge.name, edge);
    topologyComponentsByName.set(edge.name, edge);
  }
  for (const item of collectTopologyProperties(blueprint)) {
    topologyPropertyByName.set(item.property.name, item.property);
    topologyPropertyByName.set(`${item.component}.${item.property.name}`, item.property);
  }

  const relationByName = new Map(
    (blueprint.data?.relations ?? []).map((relation) => [relation.name, relation] as const),
  );
  const projectionByName = new Map(
    (blueprint.data?.projections ?? []).map((projection) => [projection.name, projection] as const),
  );
  const structByName = new Map(
    (blueprint.data?.structs ?? []).map((struct) => [struct.name, struct] as const),
  );
  const dataEntityByName = new Map<string, RelationDTO | ProjectionDTO | StructDTO>();
  for (const relation of blueprint.data?.relations ?? []) dataEntityByName.set(relation.name, relation);
  for (const projection of blueprint.data?.projections ?? []) dataEntityByName.set(projection.name, projection);
  for (const struct of blueprint.data?.structs ?? []) dataEntityByName.set(struct.name, struct);

  const { fields, fieldsByKey } = buildFieldIndexes(blueprint);
  const assetsByName = new Map(
    (blueprint.assets ?? []).map((asset) => [asset.name, asset] as const),
  );
  const semantics = buildSemanticIndexes(blueprint, fields, bindings);

  const propertyIndex = buildPropertyIndex(blueprint, bindings, bindingByComponent);
  const metaGraph = buildMetaGraphIndex(snapshot.metaGraph);

  const searchSource = {
    topologyNodes: blueprint.graph?.nodes ?? [],
    topologyEdges: blueprint.graph?.edges ?? [],
    relations: blueprint.data?.relations ?? [],
    projections: blueprint.data?.projections ?? [],
    structs: blueprint.data?.structs ?? [],
    fields,
    assets: blueprint.assets ?? [],
    bindings,
    steps,
    workflowComponents: workflow.components ?? [],
  };
  const searchRecords: SearchRecord[] = buildSearchRecords(searchSource);

  return {
    snapshot,
    blueprint,
    workflow,
    graphDeclaration: blueprint.graph_declaration,
    graphSemantics: blueprint.graph_declaration?.semantics,
    ...workflowIndexes,
    ...searchSource,
    ...semantics,
    bindings,
    bindingByComponent,
    bindingByOutputArtifactKey,
    topologyNodesByName,
    topologyEdgesByName,
    topologyComponentsByName,
    topologyPropertyByName,
    relationByName,
    projectionByName,
    structByName,
    dataEntityByName,
    fieldsByKey,
    assetsByName,
    propertyIndex,
    metaGraph,
    searchRecords,
    stats: buildStats(blueprint, workflow, workflowIndexes.connections.length),
  };
}

/** Look up the binding entries for a topology property ref. */
export function findPropertyBindings(
  index: ViewerIndex,
  propertyRef: Ref,
): PropertyLookupEntry[] {
  return index.propertyIndex.get(propertyRefKey(propertyRef)) ?? [];
}

/** Look up binding entries by component/property, used by the explorer. */
export function findComponentPropertyBindings(
  index: ViewerIndex,
  kind: EntityKind,
  component: string,
  property: string,
): PropertyLookupEntry[] {
  return findPropertyBindings(index, [
    "topology",
    "property",
    `${component}.${property}`,
  ]).filter((entry) => entry.kind === kind);
}

/** Resolve the blueprint asset for a relation/projection. */
export function resolveAssetName(index: ViewerIndex, relationName: string): string | undefined {
  const relation = index.relationByName.get(relationName);
  if (relation?.asset?.[2]) return relation.asset[2];
  const projection = index.projectionByName.get(relationName);
  if (projection?.asset?.[2]) return projection.asset[2];
  if (projection?.row_source?.relation?.[2]) {
    return index.relationByName.get(projection.row_source.relation[2])?.asset?.[2];
  }
  for (const asset of index.assets) {
    const members = Object.keys(asset.layout?.members ?? {});
    if (members.includes(relationName)) return asset.name;
  }
  return undefined;
}

/** All relation names reachable from a row source. */
export function relationNamesFromRowSource(
  rowSource: { kind?: string; relation?: Ref; left?: unknown; right?: unknown } | undefined,
): string[] {
  if (!rowSource) return [];
  const names = new Set<string>();
  const visit = (source: unknown) => {
    if (!source || typeof source !== "object") return;
    const value = source as {
      relation?: Ref;
      left?: unknown;
      right?: unknown;
      inputs?: unknown[];
    };
    if (value.relation?.[2]) names.add(value.relation[2]);
    if (value.left) visit(value.left);
    if (value.right) visit(value.right);
    for (const input of value.inputs ?? []) visit(input);
  };
  visit(rowSource);
  return [...names];
}
