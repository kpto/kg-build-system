import type {
  AnnotationContext,
  AnnotationDTO,
  EnrichedAnnotation,
  FlattenedAnnotation,
  MetaGraph,
  MetaGraphComponent,
  MetaGraphIndex,
  MetaGraphProperty,
} from "./types";

export function annotationKey(annotation: Pick<AnnotationDTO, "namespace" | "id">): string {
  return annotation.namespace ? `${annotation.namespace}:${annotation.id}` : annotation.id;
}

export function annotationLabel(annotation: Pick<AnnotationDTO, "namespace" | "id">): string {
  return annotation.namespace ? `${annotation.namespace}/${annotation.id}` : annotation.id;
}

function formatArgument(value: unknown): string {
  if (typeof value === "string") return value;
  if (value === null) return "null";
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

/** Flatten `AnnotationDTO`s to `namespace:id` keys plus ordered arguments. */
export function flattenAnnotations(
  annotations: readonly AnnotationDTO[] | undefined,
): FlattenedAnnotation[] {
  if (!annotations?.length) return [];
  return annotations.map((annotation) => {
    const args = annotation.arguments ?? {};
    const argumentList = Object.entries(args).map(([key, value]) => ({ key, value }));
    const suffix = argumentList.length
      ? `(${argumentList.map(({ key, value }) => `${key}=${formatArgument(value)}`).join(", ")})`
      : "";
    return {
      key: annotationKey(annotation),
      namespace: annotation.namespace,
      id: annotation.id,
      label: annotationLabel(annotation),
      arguments: { ...args },
      argumentList,
      text: `${annotationLabel(annotation)}${suffix}`,
      source: annotation,
    };
  });
}

export function metaGraphComponentKey(kind: string, name: string): string {
  return `${kind}\u0000${name}`;
}

/** Index the optional meta-graph by `kind:name` and by name. */
export function buildMetaGraphIndex(metaGraph?: MetaGraph): MetaGraphIndex {
  const byKey = new Map<string, MetaGraphComponent>();
  const byName = new Map<string, MetaGraphComponent[]>();
  const components = [...(metaGraph?.nodes ?? []), ...(metaGraph?.edges ?? [])];

  for (const component of components) {
    byKey.set(metaGraphComponentKey(component.kind, component.name), component);
    const existing = byName.get(component.name) ?? [];
    existing.push(component);
    byName.set(component.name, existing);
  }

  return { byKey, byName, components };
}

function isMetaGraphIndex(value: MetaGraphIndex | MetaGraph | undefined): value is MetaGraphIndex {
  return Boolean(value && "byKey" in value && value.byKey instanceof Map);
}

function resolveMetaGraphIndex(
  value: MetaGraphIndex | MetaGraph | undefined,
): MetaGraphIndex | undefined {
  if (!value) return undefined;
  return isMetaGraphIndex(value) ? value : buildMetaGraphIndex(value);
}

function findMetaComponent(
  index: MetaGraphIndex,
  context: AnnotationContext,
): MetaGraphComponent | undefined {
  if (!context.component) return undefined;
  if (context.kind) {
    const exact = index.byKey.get(metaGraphComponentKey(context.kind, context.component));
    if (exact) return exact;
  }
  const candidates = index.byName.get(context.component) ?? [];
  if (candidates.length === 1) return candidates[0];
  return candidates.find((candidate) => !context.kind || candidate.kind === context.kind);
}

function findMetaProperty(
  component: MetaGraphComponent | undefined,
  propertyName: string | undefined,
): MetaGraphProperty | undefined {
  if (!component || !propertyName) return undefined;
  return component.properties?.find((property) => property.name === propertyName);
}

/**
 * Enrich flattened annotations with meta-graph descriptions, examples and
 * cardinality counts. Component kind is used when available so a node and edge
 * with the same name do not collide.
 */
export function enrichAnnotations(
  annotations: readonly AnnotationDTO[] | undefined,
  context: AnnotationContext,
  metaGraph?: MetaGraphIndex | MetaGraph,
): EnrichedAnnotation[] {
  const metaIndex = resolveMetaGraphIndex(metaGraph);
  const metaComponent = metaIndex ? findMetaComponent(metaIndex, context) : undefined;
  const metaProperty = findMetaProperty(metaComponent, context.property);
  const description = metaProperty?.description ?? metaComponent?.description;
  const examples = metaProperty?.examples ?? [];

  return flattenAnnotations(annotations).map((annotation) => ({
    ...annotation,
    description,
    examples: [...examples],
    counts: metaComponent?.counts,
    metaComponent,
    metaProperty,
  }));
}

/** Flatten annotations and attach meta-graph context in one call. */
export function flattenAndEnrichAnnotations(
  annotations: readonly AnnotationDTO[] | undefined,
  context: AnnotationContext,
  metaGraph?: MetaGraphIndex | MetaGraph,
): EnrichedAnnotation[] {
  return enrichAnnotations(annotations, context, metaGraph);
}

/** Deduplicate flattened annotations by key and argument content. */
export function dedupeAnnotations(
  annotations: readonly FlattenedAnnotation[],
): FlattenedAnnotation[] {
  const seen = new Set<string>();
  const result: FlattenedAnnotation[] = [];
  for (const annotation of annotations) {
    const key = `${annotation.key}\u0000${JSON.stringify(annotation.arguments)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(annotation);
  }
  return result;
}

/** A compact, human-readable annotation summary for cards and popovers. */
export function annotationSummary(annotation: FlattenedAnnotation): string {
  return annotation.text;
}
