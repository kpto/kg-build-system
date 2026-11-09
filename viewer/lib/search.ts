import type {
  IndexedBinding,
  SearchOptions,
  SearchRecord,
  SearchResult,
  SearchSource,
  WorkflowStep,
} from "./types";
import { refKey } from "./expressions";

function tokenize(value: string): string[] {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9_.:/#-]+/g, " ")
    .split(/\s+/)
    .filter(Boolean);
}

function tokensOf(...values: Array<string | undefined | null>): string[] {
  const unique = new Set<string>();
  for (const value of values) {
    if (typeof value !== "string" || !value) continue;
    for (const token of tokenize(value)) unique.add(token);
  }
  return [...unique];
}

function artifactText(parts: string[] | undefined): string {
  return parts ? parts.join(".") : "";
}

function makeRecord(record: Omit<SearchRecord, "tokens"> & { tokens: string[] }): SearchRecord {
  return record;
}

function bindingRecord(binding: IndexedBinding): SearchRecord {
  const propertyNames = Object.keys(binding.binding.properties ?? {});
  const body = [
    binding.component,
    binding.kind,
    `binding ${binding.index}`,
    ...propertyNames,
    artifactText(binding.outputArtifact),
  ];
  return makeRecord({
    id: `binding:${binding.component}:${binding.index}`,
    kind: "binding",
    name: `${binding.component}[${binding.index}]`,
    label: `${binding.kind} binding · ${binding.component}`,
    detail: `${binding.kind} · properties: ${propertyNames.join(", ") || "none"}`,
    tokens: tokensOf(...body, "binding", String(binding.index)),
    component: binding.component,
    entityKind: binding.kind,
    bindingIndex: binding.index,
    ref: binding.componentRef,
  });
}

function stepRecord(step: WorkflowStep): SearchRecord {
  const [component, name] = step.id;
  const [operation, engine] = step.instruction.kind;
  const inputs = (step.inputs ?? []).map((input) => input.type);
  const outputs = (step.outputs ?? []).map((output) => output.type);
  return makeRecord({
    id: `step:${refKey(step.id)}`,
    kind: "step",
    name: `${component}/${name}`,
    label: name,
    detail: `${operation}:${engine} · ${outputs.map(artifactText).join(", ")}`,
    tokens: tokensOf(
      component,
      name,
      operation,
      engine,
      `${operation}:${engine}`,
      ...Object.keys(step.instruction.payload ?? {}),
      ...inputs.map(artifactText),
      ...outputs.map(artifactText),
      "step",
    ),
    stepId: step.id,
    component,
    instructionKind: step.instruction.kind,
  });
}

/** Build search records for every indexed name and kind. */
export function buildSearchRecords(source: SearchSource): SearchRecord[] {
  const records: SearchRecord[] = [];

  for (const node of source.topologyNodes) {
    const propertyNames = (node.properties ?? []).map((property) => property.name);
    records.push(
      makeRecord({
        id: `topology:node:${node.name}`,
        kind: "topology-node",
        name: node.name,
        label: `Node · ${node.name}`,
        detail: node.description ?? (node.labels ?? []).join(", "),
        tokens: tokensOf(
          node.name,
          ...(node.labels ?? []),
          node.description,
          ...propertyNames,
          "node topology entity",
        ),
        component: node.name,
        entityKind: "node",
        ref: ["topology", "node", node.name],
      }),
    );
    for (const property of node.properties ?? []) {
      records.push(
        makeRecord({
          id: `property:${refKey(property.ref)}`,
          kind: "property",
          name: `${node.name}.${property.name}`,
          label: `Property · ${node.name}.${property.name}`,
          detail: property.description ?? property.logical_type.name ?? property.logical_type.kind,
          tokens: tokensOf(
            node.name,
            property.name,
            `${node.name}.${property.name}`,
            property.description,
            property.logical_type.name,
            property.logical_type.kind,
            "property node",
          ),
          component: node.name,
          property: property.name,
          entityKind: "node",
          ref: property.ref,
        }),
      );
    }
  }

  for (const edge of source.topologyEdges) {
    const propertyNames = (edge.properties ?? []).map((property) => property.name);
    records.push(
      makeRecord({
        id: `topology:edge:${edge.name}`,
        kind: "topology-edge",
        name: edge.name,
        label: `Edge · ${edge.name}`,
        detail: edge.description ?? (edge.labels ?? []).join(", "),
        tokens: tokensOf(
          edge.name,
          ...(edge.labels ?? []),
          edge.description,
          ...propertyNames,
          "edge topology relationship",
        ),
        component: edge.name,
        entityKind: "edge",
        ref: ["topology", "edge", edge.name],
      }),
    );
    for (const property of edge.properties ?? []) {
      records.push(
        makeRecord({
          id: `property:${refKey(property.ref)}`,
          kind: "property",
          name: `${edge.name}.${property.name}`,
          label: `Property · ${edge.name}.${property.name}`,
          detail: property.description ?? property.logical_type.name ?? property.logical_type.kind,
          tokens: tokensOf(
            edge.name,
            property.name,
            `${edge.name}.${property.name}`,
            property.description,
            property.logical_type.name,
            property.logical_type.kind,
            "property edge relationship",
          ),
          component: edge.name,
          property: property.name,
          entityKind: "edge",
          ref: property.ref,
        }),
      );
    }
  }

  for (const relation of source.relations) {
    records.push(
      makeRecord({
        id: `relation:${relation.name}`,
        kind: "relation",
        name: relation.name,
        label: `Relation · ${relation.name}`,
        detail: relation.description ?? artifactText(relation.asset),
        tokens: tokensOf(
          relation.name,
          relation.description,
          ...relation.columns.map((column) => column.name),
          "relation table",
        ),
        ref: ["data", "relation", relation.name],
      }),
    );
  }

  for (const projection of source.projections) {
    records.push(
      makeRecord({
        id: `projection:${projection.name}`,
        kind: "projection",
        name: projection.name,
        label: `Projection · ${projection.name}`,
        detail: projection.description ?? projection.row_source.kind,
        tokens: tokensOf(
          projection.name,
          projection.description,
          projection.row_source.kind,
          ...projection.columns.map((column) => column.name),
          "projection transformation",
        ),
        ref: ["data", "projection", projection.name],
      }),
    );
  }

  for (const struct of source.structs) {
    records.push(
      makeRecord({
        id: `struct:${struct.name}`,
        kind: "struct",
        name: struct.name,
        label: `Struct · ${struct.name}`,
        detail: (struct.columns ?? []).map((column) => column.name).join(", "),
        tokens: tokensOf(
          struct.name,
          ...(struct.columns ?? []).map((column) => column.name),
          "struct type",
        ),
        ref: ["data", "struct", struct.name],
      }),
    );
  }

  for (const field of source.fields) {
    records.push(
      makeRecord({
        id: `field:${field.key}`,
        kind: "field",
        name: field.key,
        label: `Field · ${field.key}`,
        detail: `${field.ownerKind} · ${field.field.logical_type.name ?? field.field.logical_type.kind}`,
        tokens: tokensOf(
          field.key,
          field.ownerName,
          field.field.name,
          field.field.logical_type.name,
          field.field.logical_type.kind,
          field.ownerKind,
          "field column",
        ),
        ref: field.field.ref,
      }),
    );
  }

  for (const asset of source.assets) {
    const members = Object.entries(asset.layout?.members ?? {});
    records.push(
      makeRecord({
        id: `asset:${asset.name}`,
        kind: "asset",
        name: asset.name,
        label: `Asset · ${asset.name}`,
        detail:
          asset.semantics?.subject ??
          asset.layout?.locator ??
          asset.layout?.kind ??
          "asset",
        tokens: tokensOf(
          asset.name,
          asset.semantics?.subject,
          asset.semantics?.coverage,
          asset.semantics?.basis,
          asset.layout?.kind,
          asset.layout?.locator,
          ...members.flatMap(([name, location]) => [name, location]),
          ...(asset.semantics?.claims ?? []),
          "asset",
        ),
        ref: ["asset", "asset", asset.name],
      }),
    );
  }

  for (const binding of source.bindings) {
    records.push(bindingRecord(binding));
  }

  for (const step of source.steps) {
    records.push(stepRecord(step));
  }

  const instructionKinds = new Map<string, WorkflowStep>();
  for (const step of source.steps) {
    instructionKinds.set(refKey(step.instruction.kind), step);
  }
  for (const [key, step] of instructionKinds) {
    const [operation, engine] = step.instruction.kind;
    records.push(
      makeRecord({
        id: `instruction:${key}`,
        kind: "instruction",
        name: `${operation}:${engine}`,
        label: `Instruction · ${operation}:${engine}`,
        detail: `Instruction kind used by ${source.steps.filter((candidate) => refKey(candidate.instruction.kind) === key).length} step(s)`,
        tokens: tokensOf(operation, engine, `${operation}:${engine}`, "instruction kind"),
        instructionKind: step.instruction.kind,
      }),
    );
  }

  for (const component of source.workflowComponents) {
    const steps = source.steps.filter((step) => step.id[0] === component.id);
    records.push(
      makeRecord({
        id: `workflow-component:${component.id}`,
        kind: "workflow-component",
        name: component.id,
        label: `Component · ${component.id}`,
        detail: `version ${component.version ?? "—"} · ${steps.length} step(s)`,
        tokens: tokensOf(
          component.id,
          component.version,
          ...(component.runtime_fields ?? []).flatMap((field) =>
            typeof field === "string"
              ? [field]
              : typeof field === "object" && field !== null && "key" in field
                ? [String((field as { key?: unknown }).key ?? ""), String((field as { description?: unknown }).description ?? "")]
                : [],
          ),
          ...steps.map((step) => step.id[1]),
          "component workflow",
        ),
        component: component.id,
      }),
    );
  }

  return records;
}

function scoreRecord(record: SearchRecord, queryTokens: string[], rawQuery: string): number {
  const haystack = record.tokens.join(" ");
  if (!queryTokens.every((token) => haystack.includes(token))) return 0;

  const name = record.name.toLowerCase();
  const label = record.label.toLowerCase();
  const detail = record.detail.toLowerCase();
  const normalizedQuery = rawQuery.toLowerCase().trim();
  let score = 0;

  if (name === normalizedQuery) score += 120;
  else if (name.startsWith(normalizedQuery)) score += 70;
  else if (name.includes(normalizedQuery)) score += 35;

  if (label === normalizedQuery) score += 80;
  else if (label.includes(normalizedQuery)) score += 20;

  for (const token of queryTokens) {
    if (record.tokens.some((candidate) => candidate === token)) score += 18;
    else if (haystack.includes(token)) score += 8;
    if (name.includes(token)) score += 6;
    if (detail.includes(token)) score += 2;
  }

  // Prefer the exact entity over incidental matches on long descriptions.
  score -= Math.max(0, record.tokens.length - 30) * 0.1;
  return score;
}

/** Search all records. Multi-token queries require every token to match. */
export function searchIndex(
  records: readonly SearchRecord[],
  query: string,
  options: SearchOptions = {},
): SearchResult[] {
  const rawQuery = query.trim();
  if (!rawQuery) return [];
  const queryTokens = tokenize(rawQuery);
  if (!queryTokens.length) return [];
  const allowed = options.kinds ? new Set(options.kinds) : undefined;
  const limit = options.limit ?? 40;

  return records
    .filter((record) => !allowed || allowed.has(record.kind))
    .map((record) => ({ ...record, score: scoreRecord(record, queryTokens, rawQuery) }))
    .filter((record) => record.score > 0)
    .sort((left, right) => {
      if (right.score !== left.score) return right.score - left.score;
      if (left.kind !== right.kind) return left.kind.localeCompare(right.kind);
      return left.name.localeCompare(right.name);
    })
    .slice(0, limit);
}
