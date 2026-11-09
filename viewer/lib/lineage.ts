import type {
  AnnotationDTO,
  ArtifactType,
  EntityKind,
  EnrichedAnnotation,
  LineageBranch,
  LineageEdge,
  LineageGraph,
  LineageLane,
  LineageNode,
  LineageNodeKind,
  LineageNodeMetadata,
  PropertySelection,
  Ref,
  RowSource,
  ViewerIndex,
  WorkflowStep,
} from "./types";
import { LINEAGE_LANES } from "./types";
import { enrichAnnotations } from "./annotations";
import {
  collectFieldRefs,
  fieldRefKey,
  refKey,
  stepSqlPreview,
} from "./expressions";
import {
  artifactDisplay,
  findComponentPropertyBindings,
  resolveAssetName,
  stepKey,
} from "./indexes";

const MAX_TRAVERSAL_DEPTH = 40;

interface TraversedStep {
  step: WorkflowStep;
  depth: number;
}

function semanticNodeId(kind: string, name: string): string {
  return `semantic:${kind}:${name}`;
}

export function lineageStepNodeId(step: WorkflowStep): string {
  return `step:${step.id[0]}/${step.id[1]}`;
}

function targetNodeId(step: WorkflowStep): string {
  return `target:${step.id[0]}/${step.id[1]}`;
}

function propertyNodeId(selection: PropertySelection): string {
  return `property:${selection.component}.${selection.property}`;
}

function traverse(
  index: ViewerIndex,
  start: WorkflowStep,
  direction: "upstream" | "downstream",
): TraversedStep[] {
  const visited = new Set<string>([stepKey(start.id)]);
  const result: TraversedStep[] = [];
  const queue: TraversedStep[] = [{ step: start, depth: 0 }];

  while (queue.length) {
    const current = queue.shift() as TraversedStep;
    if (current.depth >= MAX_TRAVERSAL_DEPTH) continue;
    const key = stepKey(current.step.id);
    const connections =
      direction === "upstream"
        ? index.incomingByStepId.get(key) ?? []
        : index.outgoingByStepId.get(key) ?? [];
    for (const connection of connections) {
      const next = index.stepsById.get(
        stepKey(direction === "upstream" ? connection.outputStepId : connection.inputStepId),
      );
      if (!next) continue;
      const nextKey = stepKey(next.id);
      if (visited.has(nextKey)) continue;
      visited.add(nextKey);
      result.push({ step: next, depth: current.depth + 1 });
      queue.push({ step: next, depth: current.depth + 1 });
    }
  }

  return result;
}

function classifyStep(step: WorkflowStep): {
  lane: LineageLane;
  kind: LineageNodeKind;
} {
  const operation = step.instruction.kind[0];
  const targetArtifact = step.outputs?.some((output) =>
    ["file", "meta_graph", "neo4j"].includes(output.type[0]),
  );

  if (operation === "source_relation") return { lane: "source", kind: "table" };
  if (operation === "sql") return { lane: "transformation", kind: "projection" };
  if (operation === "aggregate") return { lane: "post", kind: "aggregate" };
  if (operation === "deduplication") return { lane: "post", kind: "deduplication" };
  if (operation === "merging") return { lane: "post", kind: "merging" };
  if (operation === "conflict_validation") return { lane: "post", kind: "conflict" };
  if (operation === "file" || operation === "meta_graph" || operation === "neo4j" || targetArtifact) {
    return { lane: "target", kind: "target" };
  }
  return { lane: "post", kind: "step" };
}

function componentAnnotations(
  index: ViewerIndex,
  kind: EntityKind,
  component: string,
  property?: string,
): {
  annotations: AnnotationDTO[];
  views: EnrichedAnnotation[];
} {
  const entity =
    kind === "node"
      ? index.topologyNodesByName.get(component)
      : index.topologyEdgesByName.get(component);
  const propertyDTO = entity?.properties?.find((candidate) => candidate.name === property);
  const annotations = [
    ...(entity?.annotations ?? []),
    ...(propertyDTO?.annotations ?? []),
  ];
  return {
    annotations,
    views: enrichAnnotations(annotations, { kind, component, property }, index.metaGraph),
  };
}

function stepNodeMetadata(
  index: ViewerIndex,
  step: WorkflowStep,
  extraAnnotations: AnnotationDTO[] = [],
): LineageNodeMetadata {
  const artifacts: ArtifactType[] = (step.outputs ?? []).map((output) => output.type);
  const payload = step.instruction.payload;
  const annotationContext = {
    kind: "node" as const,
    component: step.id[1],
  };
  const annotations = [...extraAnnotations];
  return {
    artifacts,
    step,
    payload,
    annotations,
    annotationViews: enrichAnnotations(annotations, annotationContext, index.metaGraph),
    description:
      typeof payload?.description === "string" ? payload.description : undefined,
    sourceLocation:
      (typeof payload?.location === "string" && payload.location) ||
      (typeof payload?.directory === "string" && payload.directory) ||
      (typeof payload?.relative_path === "string" && payload.relative_path) ||
      undefined,
    sqlPreview: stepSqlPreview(step),
  };
}

function publishedLocation(index: ViewerIndex, step: WorkflowStep): string | undefined {
  for (const artifact of index.snapshot.report?.published_artifacts ?? []) {
    if (artifact.opening[0] !== step.id[0] || artifact.opening[1] !== step.id[1]) continue;
    for (const key of ["location", "directory", "script", "html_location"]) {
      const value = artifact.value?.[key];
      if (typeof value === "string") return value;
    }
  }
  return undefined;
}

function publishedValue(index: ViewerIndex, step: WorkflowStep): Record<string, unknown> | undefined {
  return index.snapshot.report?.published_artifacts?.find(
    (artifact) => artifact.opening[0] === step.id[0] && artifact.opening[1] === step.id[1],
  )?.value;
}

function addNode(
  nodes: Map<string, LineageNode>,
  node: LineageNode,
): void {
  if (!nodes.has(node.id)) nodes.set(node.id, node);
}

function addEdge(
  edges: Map<string, LineageEdge>,
  source: string,
  target: string,
  branchKey: string,
  label?: string,
): string {
  const id = `edge:${source}->${target}`;
  if (!edges.has(id)) {
    edges.set(id, { id, source, target, branchKey, label });
  }
  return id;
}

function buildBranch(
  index: ViewerIndex,
  selection: PropertySelection,
  entry: ReturnType<typeof findComponentPropertyBindings>[number],
  nodes: Map<string, LineageNode>,
  edges: Map<string, LineageEdge>,
  terminalNodeId: string,
): LineageBranch {
  const binding = entry.binding;
  const expression = entry.expression ?? binding.binding.properties?.[selection.property];
  const fieldRefs = collectFieldRefs(expression);
  const fieldKeys = fieldRefs.map(fieldRefKey).filter(Boolean);
  const relationNames = [...new Set(
    fieldKeys.map((key) => index.fieldsByKey.get(key)?.ownerName ?? key.split(".")[0]),
  )];
  const sourceRelations = [...new Set(
    relationNames.flatMap((name) => {
      const projection = index.projectionByName.get(name);
      if (projection) {
        const names = [
          projection.row_source?.relation?.[2],
          ...relationNamesFromProjection(projection),
        ].filter((candidate): candidate is string => Boolean(candidate));
        return names;
      }
      return [name];
    }),
  )];
  const assetNames = [...new Set(
    [...relationNames, ...sourceRelations]
      .map((name) => resolveAssetName(index, name))
      .filter((name): name is string => Boolean(name)),
  )];

  const branchKey = `${selection.kind}:${selection.component}.${selection.property}:binding-${binding.index}`;
  const nodeIds: string[] = [];
  const edgeIds: string[] = [];
  const rememberNode = (node: LineageNode) => {
    addNode(nodes, node);
    if (!nodeIds.includes(node.id)) nodeIds.push(node.id);
  };
  const connect = (source: string, target: string, label?: string) => {
    const id = addEdge(edges, source, target, branchKey, label);
    if (!edgeIds.includes(id)) edgeIds.push(id);
  };

  const bindingStep = binding.step;
  // A literal-only property has no source expression to trace. Its lineage is
  // the binding plus the downstream publication target, so upstream traversal
  // is intentionally skipped.
  const upstream =
    bindingStep && fieldRefs.length ? traverse(index, bindingStep, "upstream") : [];
  const downstream = bindingStep ? traverse(index, bindingStep, "downstream") : [];
  const sourceSteps = upstream
    .map(({ step }) => step)
    .filter((step) => classifyStep(step).lane === "source");
  const transformationSteps = upstream
    .map(({ step }) => step)
    .filter((step) => classifyStep(step).lane === "transformation");
  const postSteps = downstream
    .map(({ step }) => step)
    .filter((step) => classifyStep(step).lane === "post");
  const targetSteps = downstream
    .map(({ step }) => step)
    .filter((step) => classifyStep(step).lane === "target");

  const bindingAnnotations = [
    ...(binding.binding.annotations ?? []),
    ...componentAnnotations(index, selection.kind, selection.component, selection.property)
      .annotations,
  ];
  const bindingViews = enrichAnnotations(
    bindingAnnotations,
    { kind: selection.kind, component: selection.component, property: selection.property },
    index.metaGraph,
  );

  // Semantic source side. Literal-only properties skip this entirely; their
  // lineage is binding + downstream targets per the viewer contract.
  const semanticSourceByRelation = new Map<string, string>();

  for (const assetName of assetNames) {
    const asset = index.assetsByName.get(assetName);
    const nodeId = semanticNodeId("asset", assetName);
    rememberNode({
      id: nodeId,
      label: `Asset · ${assetName}`,
      lane: "asset",
      category: "semantic",
      kind: "asset",
      ref: ["asset", "asset", assetName],
      component: assetName,
      metadata: {
        artifacts: [["asset", "asset", assetName]],
        annotations: asset?.annotations ?? [],
        annotationViews: enrichAnnotations(asset?.annotations, {}, index.metaGraph),
        description:
          asset?.profile?.description ?? asset?.profile?.subject ?? undefined,
        sourceLocation: asset?.layout?.locator ?? undefined,
      },
    });
  }

  for (const relationName of sourceRelations) {
    const relation = index.relationByName.get(relationName);
    const projection = index.projectionByName.get(relationName);
    const isProjectionOwner = relationNames.includes(relationName) && Boolean(projection);
    const nodeKind: LineageNodeKind = isProjectionOwner ? "projection" : "table";
    const lane: LineageLane = isProjectionOwner ? "transformation" : "source";
    const nodeId = semanticNodeId(isProjectionOwner ? "projection" : "relation", relationName);
    rememberNode({
      id: nodeId,
      label: `${isProjectionOwner ? "Projection" : "Table"} · ${relationName}`,
      lane,
      category: "semantic",
      kind: nodeKind,
      component: relationName,
      ref: isProjectionOwner
        ? ["data", "projection", relationName]
        : ["data", "relation", relationName],
      metadata: {
        artifacts: [
          isProjectionOwner
            ? ["core", "data", "projection", relationName]
            : ["core", "data", "table", relationName],
        ],
        annotations: projection?.annotations ?? relation?.annotations ?? [],
        annotationViews: enrichAnnotations(
          projection?.annotations ?? relation?.annotations,
          {},
          index.metaGraph,
        ),
        description: projection?.description ?? relation?.description,
        expression: undefined,
      },
    });
    if (!isProjectionOwner) semanticSourceByRelation.set(relationName, nodeId);
  }

  // Field and transformation nodes carry the concrete expression path.
  const fieldNodeIds: string[] = [];
  for (const fieldRef of fieldRefs) {
    const key = fieldRefKey(fieldRef);
    const location = index.fieldsByKey.get(key);
    const ownerName = location?.ownerName ?? key.split(".")[0] ?? "field";
    const ownerProjection = index.projectionByName.get(ownerName);
    const ownerRelation = index.relationByName.get(ownerName);
    const fieldNodeId = semanticNodeId("field", key);
    fieldNodeIds.push(fieldNodeId);
    rememberNode({
      id: fieldNodeId,
      label: `Field · ${key}`,
      lane: ownerProjection ? "transformation" : "source",
      category: "semantic",
      kind: "field",
      component: ownerName,
      ref: fieldRef,
      metadata: {
        artifacts: [],
        annotations: location?.field.annotations ?? [],
        annotationViews: enrichAnnotations(location?.field.annotations, {}, index.metaGraph),
        description: location?.field.description,
        expression: location?.field.expression,
      },
    });

    const ownerNodeId = ownerProjection
      ? semanticNodeId("projection", ownerName)
      : semanticNodeId("relation", ownerName);
    // The owner node may not have been added when a projection has no direct
    // row-source relation in the source-relations pass.
    if (!nodes.has(ownerNodeId)) {
      rememberNode({
        id: ownerNodeId,
        label: `${ownerProjection ? "Projection" : "Table"} · ${ownerName}`,
        lane: ownerProjection ? "transformation" : "source",
        category: "semantic",
        kind: ownerProjection ? "projection" : "table",
        component: ownerName,
        ref: ownerProjection
          ? ["data", "projection", ownerName]
          : ["data", "relation", ownerName],
        metadata: {
          artifacts: [
            ownerProjection
              ? ["core", "data", "projection", ownerName]
              : ["core", "data", "table", ownerName],
          ],
          annotations: ownerProjection?.annotations ?? ownerRelation?.annotations ?? [],
          annotationViews: enrichAnnotations(
            ownerProjection?.annotations ?? ownerRelation?.annotations,
            {},
            index.metaGraph,
          ),
          description: ownerProjection?.description ?? ownerRelation?.description,
        },
      });
    }
    connect(ownerNodeId, fieldNodeId);
  }

  for (const step of sourceSteps) {
    const nodeId = lineageStepNodeId(step);
    const classification = classifyStep(step);
    rememberNode({
      id: nodeId,
      label: `Source · ${step.id[1]}`,
      lane: classification.lane,
      category: "workflow",
      kind: classification.kind,
      component: step.id[0],
      stepId: step.id,
      metadata: stepNodeMetadata(index, step),
    });
  }

  for (const step of transformationSteps) {
    const nodeId = lineageStepNodeId(step);
    const classification = classifyStep(step);
    rememberNode({
      id: nodeId,
      label: `Transform · ${step.id[1]}`,
      lane: classification.lane,
      category: "workflow",
      kind: classification.kind,
      component: step.id[0],
      stepId: step.id,
      metadata: stepNodeMetadata(index, step),
    });
  }

  // Asset -> relation path. A relation may be the owner of the field, while a
  // projection's row source is the relation that feeds it.
  for (const assetName of assetNames) {
    const assetNodeId = semanticNodeId("asset", assetName);
    for (const relationName of sourceRelations) {
      const relationNodeId = semanticNodeId("relation", relationName);
      const relation = index.relationByName.get(relationName);
      const targetAsset = resolveAssetName(index, relationName);
      if (targetAsset === assetName && relation) connect(assetNodeId, relationNodeId);
    }
  }

  // Connect sources into fields, then fields into the projection owner.
  for (const relationName of semanticSourceByRelation.keys()) {
    const relationNodeId = semanticSourceByRelation.get(relationName);
    if (!relationNodeId) continue;
    // There can be several source steps consuming the same table (for example
    // one step per projection); connect the first matching source step.
    const matchingSource = sourceSteps.find((step) =>
      step.outputs?.some((output) => output.type[2] === "table" && output.type[3] === relationName),
    );
    if (matchingSource) connect(relationNodeId, lineageStepNodeId(matchingSource));
  }

  for (const fieldNodeId of fieldNodeIds) {
    const fieldNode = nodes.get(fieldNodeId);
    if (!fieldNode) continue;
    const fieldKey = fieldNode.ref ? fieldRefKey(fieldNode.ref) : "";
    const location = index.fieldsByKey.get(fieldKey);
    if (location?.ownerKind === "projection") {
      const projectionNodeId = semanticNodeId("projection", location.ownerName);
      const matchingTransform = transformationSteps.find((step) =>
        step.outputs?.some(
          (output) =>
            output.type[2] === "projection" && output.type[3] === location.ownerName,
        ),
      );
      if (matchingTransform) {
        connect(fieldNodeId, projectionNodeId);
        connect(projectionNodeId, lineageStepNodeId(matchingTransform));
      } else {
        connect(fieldNodeId, projectionNodeId);
      }
    } else if (location?.ownerKind === "relation") {
      const matchingSource = sourceSteps.find((step) =>
        step.outputs?.some(
          (output) => output.type[2] === "table" && output.type[3] === location.ownerName,
        ),
      );
      if (matchingSource) connect(fieldNodeId, lineageStepNodeId(matchingSource));
    }
  }

  // If a projection row source has a source step, connect that source step to
  // the projection field nodes even when the field owner itself is a relation.
  for (const relationName of semanticSourceByRelation.keys()) {
    const relationNodeId = semanticSourceByRelation.get(relationName);
    if (!relationNodeId) continue;
    for (const fieldNodeId of fieldNodeIds) {
      const fieldNode = nodes.get(fieldNodeId);
      if (!fieldNode?.ref) continue;
      const location = index.fieldsByKey.get(fieldRefKey(fieldNode.ref));
      if (location?.ownerKind === "projection") {
        // Source step feeds the field through the projection row source.
        connect(relationNodeId, fieldNodeId);
      }
    }
  }

  const bindingNodeId = semanticNodeId("binding", `${selection.component}.${binding.index}`);
  rememberNode({
    id: bindingNodeId,
    label: `Binding · ${selection.component} [${binding.index}]`,
    lane: "binding",
    category: "semantic",
    kind: "binding",
    component: selection.component,
    property: selection.property,
    ref: binding.componentRef,
    metadata: {
      artifacts: [binding.outputArtifact],
      annotations: bindingAnnotations,
      annotationViews: bindingViews,
      expression,
      description: binding.binding.mode
        ? `${binding.kind} binding · ${binding.binding.mode}`
        : `${binding.kind} binding`,
    },
  });

  const bindingStepNodeId = bindingStep ? lineageStepNodeId(bindingStep) : undefined;
  if (bindingStep) {
    rememberNode({
      id: bindingStepNodeId as string,
      label: `Binding · ${bindingStep.id[1]}`,
      lane: "binding",
      category: "workflow",
      kind: "binding",
      component: bindingStep.id[0],
      stepId: bindingStep.id,
      metadata: stepNodeMetadata(index, bindingStep, bindingAnnotations),
    });
  }

  // Source transformation path converges on the semantic binding.
  const predecessorNodes = new Set<string>();
  for (const step of transformationSteps) predecessorNodes.add(lineageStepNodeId(step));
  for (const fieldNodeId of fieldNodeIds) predecessorNodes.add(fieldNodeId);
  if (!predecessorNodes.size) {
    for (const assetName of assetNames) predecessorNodes.add(semanticNodeId("asset", assetName));
    for (const step of sourceSteps) predecessorNodes.add(lineageStepNodeId(step));
  }
  for (const predecessor of predecessorNodes) {
    connect(predecessor, bindingNodeId);
  }
  if (bindingStepNodeId) connect(bindingNodeId, bindingStepNodeId);

  // Upstream workflow DAG. These are real connections, so the acceptance chain
  // source -> projection -> binding is visible on the lineage canvas rather
  // than only implied by semantic lane nodes.
  const activeUpstreamKeys = new Set<string>();
  if (bindingStep) activeUpstreamKeys.add(stepKey(bindingStep.id));
  for (const step of [...sourceSteps, ...transformationSteps]) {
    activeUpstreamKeys.add(stepKey(step.id));
  }
  for (const connection of index.connections) {
    const sourceKey = stepKey(connection.outputStepId);
    const targetKey = stepKey(connection.inputStepId);
    if (!activeUpstreamKeys.has(sourceKey) || !activeUpstreamKeys.has(targetKey)) continue;
    const sourceStep = index.stepsById.get(sourceKey);
    const targetStep = index.stepsById.get(targetKey);
    if (!sourceStep || !targetStep) continue;
    connect(
      lineageStepNodeId(sourceStep),
      lineageStepNodeId(targetStep),
      connection.output.openingName,
    );
  }

  // Downstream workflow DAG. Use real connections so aggregate -> dedup ->
  // target steps are represented faithfully.
  const downstreamStepNodes = new Map<string, string>();
  for (const { step } of downstream) {
    const nodeId = lineageStepNodeId(step);
    const classification = classifyStep(step);
    downstreamStepNodes.set(stepKey(step.id), nodeId);
    rememberNode({
      id: nodeId,
      label:
        classification.lane === "target"
          ? `Target · ${step.id[1]}`
          : `${step.id[1]}`,
      lane: classification.lane,
      category: "workflow",
      kind: classification.kind,
      component: step.id[0],
      stepId: step.id,
      metadata: stepNodeMetadata(index, step),
    });
  }

  const activeStepKeys = new Set<string>();
  if (bindingStep) activeStepKeys.add(stepKey(bindingStep.id));
  for (const { step } of downstream) activeStepKeys.add(stepKey(step.id));

  for (const connection of index.connections) {
    const sourceKey = stepKey(connection.outputStepId);
    const targetKey = stepKey(connection.inputStepId);
    if (!activeStepKeys.has(sourceKey) || !activeStepKeys.has(targetKey)) continue;
    const sourceNodeId =
      bindingStep && sourceKey === stepKey(bindingStep.id)
        ? bindingStepNodeId
        : downstreamStepNodes.get(sourceKey);
    const targetNodeId = downstreamStepNodes.get(targetKey);
    if (sourceNodeId && targetNodeId) {
      connect(sourceNodeId, targetNodeId, connection.output.openingName);
    }
  }

  // Terminal property node is linked from every target semantic node. If a
  // branch has no publication target, its last post step links directly.
  for (const step of targetSteps) {
    const targetId = targetNodeId(step);
    const value = publishedValue(index, step);
    const annotations = [
      ...componentAnnotations(index, selection.kind, selection.component, selection.property)
        .annotations,
    ];
    const artifacts: ArtifactType[] = (step.outputs ?? []).map((output) => output.type);
    rememberNode({
      id: targetId,
      label: `Target · ${artifacts.map(artifactDisplay).join(", ") || step.id[1]}`,
      lane: "target",
      category: "semantic",
      kind: "target",
      component: step.id[0],
      stepId: step.id,
      metadata: {
        artifacts,
        annotations,
        annotationViews: enrichAnnotations(
          annotations,
          { kind: selection.kind, component: selection.component, property: selection.property },
          index.metaGraph,
        ),
        description:
          value && typeof value === "object"
            ? Object.entries(value)
                .slice(0, 4)
                .map(([key, entry]) => `${key}: ${String(entry)}`)
                .join(" · ")
            : undefined,
        sourceLocation: publishedLocation(index, step),
        payload: value,
      },
    });
    connect(lineageStepNodeId(step), targetId);
    connect(targetId, terminalNodeId);
  }

  if (!targetSteps.length) {
    const lastSteps = downstream.filter(({ step }) => {
      const key = stepKey(step.id);
      return !(index.outgoingByStepId.get(key) ?? []).some((connection) =>
        activeStepKeys.has(stepKey(connection.inputStepId)),
      );
    });
    if (lastSteps.length) {
      for (const { step } of lastSteps) connect(lineageStepNodeId(step), terminalNodeId);
    } else if (bindingStepNodeId) {
      connect(bindingStepNodeId, terminalNodeId);
    } else {
      connect(bindingNodeId, terminalNodeId);
    }
  }

  return {
    key: branchKey,
    propertyRef: selection.propertyRef,
    propertyName: selection.property,
    binding,
    expression,
    fieldRefs,
    fieldKeys,
    relationNames,
    sourceRelations,
    assetNames,
    bindingStep,
    transformationSteps,
    sourceSteps,
    postSteps,
    targetSteps,
    upstreamSteps: upstream.map(({ step }) => step),
    downstreamSteps: downstream.map(({ step }) => step),
    nodeIds,
    edgeIds,
  };
}

function relationNamesFromProjection(
  projection: { row_source?: RowSource } | undefined,
): string[] {
  if (!projection) return [];
  const rowSource = projection.row_source;
  const names = new Set<string>();
  const visit = (source: unknown) => {
    if (!source || typeof source !== "object") return;
    const value = source as { relation?: Ref; left?: unknown; right?: unknown; inputs?: unknown[] };
    if (value.relation?.[2]) names.add(value.relation[2]);
    if (value.left) visit(value.left);
    if (value.right) visit(value.right);
    for (const input of value.inputs ?? []) visit(input);
  };
  visit(rowSource);
  return [...names];
}

function terminalMetadata(
  index: ViewerIndex,
  selection: PropertySelection,
  branches: LineageBranch[],
): LineageNodeMetadata {
  const entity =
    selection.kind === "node"
      ? index.topologyNodesByName.get(selection.component)
      : index.topologyEdgesByName.get(selection.component);
  const property = entity?.properties?.find((candidate) => candidate.name === selection.property);
  const bindingAnnotations = branches.flatMap(
    (branch) => branch.binding.binding.annotations ?? [],
  );
  const annotations = [
    ...(property?.annotations ?? []),
    ...(entity?.annotations ?? []),
    ...bindingAnnotations,
  ];
  const metaComponent =
    index.metaGraph.byKey.get(`${selection.kind}\u0000${selection.component}`) ??
    index.metaGraph.byName.get(selection.component)?.find((candidate) => candidate.kind === selection.kind);
  const metaProperty = metaComponent?.properties?.find(
    (candidate) => candidate.name === selection.property,
  );
  return {
    artifacts: branches.map((branch) => branch.binding.outputArtifact),
    annotations,
    annotationViews: enrichAnnotations(
      annotations,
      { kind: selection.kind, component: selection.component, property: selection.property },
      index.metaGraph,
    ),
    description: metaProperty?.description ?? property?.description ?? metaComponent?.description,
    examples: metaProperty?.examples ?? [],
    counts: metaComponent?.counts,
    expression: branches.find((branch) => branch.expression)?.expression,
  };
}

/**
 * Build the focused property lineage.
 *
 * The returned DAG always contains the selected property as a terminal semantic
 * node. Each branch corresponds to one blueprint binding; a property bound from
 * several sources (for example `reading.value` from temperature and vibration)
 * shows all source branches converging on the same terminal property.
 */
export function buildLineage(
  index: ViewerIndex,
  selection: PropertySelection,
): LineageGraph {
  const entries = findComponentPropertyBindings(
    index,
    selection.kind,
    selection.component,
    selection.property,
  );
  const uniqueEntries = entries.filter(
    (entry, position, all) =>
      all.findIndex((candidate) => candidate.binding.index === entry.binding.index) === position,
  );

  const nodes = new Map<string, LineageNode>();
  const edges = new Map<string, LineageEdge>();
  const terminal = propertyNodeId(selection);
  const entity =
    selection.kind === "node"
      ? index.topologyNodesByName.get(selection.component)
      : index.topologyEdgesByName.get(selection.component);
  const property = entity?.properties?.find((candidate) => candidate.name === selection.property);

  nodes.set(terminal, {
    id: terminal,
    label: `${selection.kind} · ${selection.component}.${selection.property}`,
    lane: "target",
    category: "semantic",
    kind: "property",
    component: selection.component,
    property: selection.property,
    ref: selection.propertyRef,
    metadata: {
      artifacts: [],
      annotations: property?.annotations ?? [],
      annotationViews: enrichAnnotations(
        property?.annotations,
        { kind: selection.kind, component: selection.component, property: selection.property },
        index.metaGraph,
      ),
      description: property?.description,
      expression: undefined,
    },
  });

  const branches = uniqueEntries.map((entry) =>
    buildBranch(index, selection, entry, nodes, edges, terminal),
  );

  const terminalNode = nodes.get(terminal);
  if (terminalNode) {
    terminalNode.metadata = terminalMetadata(index, selection, branches);
  }

  return {
    selection,
    branches,
    nodes: [...nodes.values()],
    edges: [...edges.values()],
    lanes: LINEAGE_LANES,
    terminalNodeId: terminal,
  };
}

/** Convenience constructor used by the explorer and tests. */
export function propertySelection(
  kind: EntityKind,
  component: string,
  property: string,
): PropertySelection {
  return {
    kind,
    component,
    property,
    propertyRef: ["topology", "property", `${component}.${property}`],
  };
}

export function lineageFieldRefKey(ref: Ref): string {
  return fieldRefKey(ref);
}

export function lineageRefKey(ref: Ref): string {
  return refKey(ref);
}
