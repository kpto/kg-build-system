import type {
  AssetProfileDTO,
  ColumnDTO,
  DefinitionDTO,
  MeaningDTO,
} from "./types";

/** The one display reading of an attached meaning. */
export function meaningText(meaning?: MeaningDTO): string | undefined {
  if (!meaning) return undefined;
  return (
    meaning.purpose?.text ??
    meaning.claims?.[0]?.text ??
    meaning.frames?.[0]?.text
  );
}

/** A relation definition as display text; grain, then identity. */
export function definitionText(
  definition?: DefinitionDTO,
): string | undefined {
  if (!definition) return undefined;
  const identity = definition.identity?.length
    ? `identity ${definition.identity.join(", ")}`
    : undefined;
  return identity ? `${definition.grain} · ${identity}` : definition.grain;
}

/** A record's display summary: meaning first, then its definition. */
export function recordSummary(value: {
  meaning?: MeaningDTO;
  semantics?: MeaningDTO;
  definition?: DefinitionDTO;
  description?: string;
}): string | undefined {
  return (
    meaningText(value.meaning ?? value.semantics) ??
    definitionText(value.definition) ??
    value.description
  );
}

/** A column's display summary: its field definition first, then its meaning. */
export function fieldSummary(field: ColumnDTO): string | undefined {
  return (
    field.definition?.value ??
    meaningText(field.meaning ?? field.semantics) ??
    field.description ??
    field.logical_type?.name ??
    field.logical_type?.kind
  );
}

/** A column's declaration text only: no type fallback, suitable for a table. */
export function fieldDescription(field: ColumnDTO): string {
  return (
    field.definition?.value ??
    meaningText(field.meaning ?? field.semantics) ??
    field.description ??
    "—"
  );
}

/** A field's unit and null meaning, when the definition states them. */
export function fieldDefinitionDetail(field: ColumnDTO): string {
  const definition = field.definition;
  if (!definition) return "—";
  return [
    definition.value,
    definition.unit ? `unit ${definition.unit}` : undefined,
    definition.null_meaning ? `null: ${definition.null_meaning}` : undefined,
  ]
    .filter(Boolean)
    .join(" · ");
}

/** An asset profile summary without relying on the retired description. */
export function profileSummary(
  profile?: AssetProfileDTO,
): string | undefined {
  if (!profile) return undefined;
  return (
    profile.title ??
    profile.subject ??
    profile.basis ??
    profile.description
  );
}

/** The author-facing label for a workbench or search kind. */
export function subjectKindLabel(kind?: string): string {
  switch (kind) {
    case "relation":
    case "table":
      return "source relation";
    case "projection":
      return "derived relation";
    case "topology-node":
      return "node";
    case "topology-edge":
      return "edge";
    case "workflow-component":
      return "workflow component";
    default:
      return kind?.replaceAll("-", " ") ?? "document";
  }
}
