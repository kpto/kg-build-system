/**
 * TypeScript mirror of `studio_backend.ir.document`.
 *
 * Field names, discriminant values and optionality are identical to the pydantic
 * models, so a document round-trips through `PUT /api/document` unchanged. Every
 * pydantic model is `frozen=True` with `extra="forbid"`, which is mirrored here by
 * `readonly` fields and `readonly` arrays: edits are expressed by rebuilding the
 * part that changed, never by mutating in place.
 *
 * Two subsections are framework IR verbatim: `LogicalType` and `Expression`.
 * `logical_type` on an expression is derived by the backend and must never be
 * trusted from the UI, so renderers read it but nothing here computes it.
 */

import { buildRef, parseRef } from "./ids";

/** JSON payloads inside the document (`annotations[].arguments`, `parameters`, …). */
export type JsonValue =
  | string
  | number
  | boolean
  | null
  | readonly JsonValue[]
  | { readonly [key: string]: JsonValue };

export type JsonObject = { [key: string]: JsonValue };

export const SCHEMA_VERSION = 1 as const;

export type RefKind =
  | "table"
  | "struct"
  | "projection"
  | "component"
  | "binding"
  | "source"
  | "module"
  | "annotation_type";

export type UnitName = "bool" | "int" | "float" | "str" | "date" | "time" | "timestamp" | "uuid";

export const UNIT_NAMES: readonly UnitName[] = [
  "bool",
  "int",
  "float",
  "str",
  "date",
  "time",
  "timestamp",
  "uuid",
];

/* ------------------------------------------------------------------ logical types */

export interface UnitType {
  readonly kind: "unit";
  readonly name: UnitName;
}

export interface ArrayType {
  readonly kind: "array";
  readonly item: LogicalType;
}

/** A reference to a struct declaration, addressed by its generated location. */
export interface StructType {
  readonly kind: "struct";
  readonly module: string;
  readonly qualname: string;
}

export interface NullableType {
  readonly kind: "nullable";
  readonly value: NonNullableLogicalType;
}

export type NonNullableLogicalType = UnitType | ArrayType | StructType;

export type LogicalType = NonNullableLogicalType | NullableType;

export const unit = (name: UnitName): UnitType => ({ kind: "unit", name });

export const array = (item: LogicalType): ArrayType => ({ kind: "array", item });

export const nullable = (value: NonNullableLogicalType): NullableType => ({
  kind: "nullable",
  value,
});

export const structRef = (module: string, qualname: string): StructType => ({
  kind: "struct",
  module,
  qualname,
});

export const isNullable = (value: LogicalType): value is NullableType =>
  value.kind === "nullable";

export const unwrapNullable = (value: LogicalType): NonNullableLogicalType =>
  value.kind === "nullable" ? value.value : value;

/**
 * The canonical rendering used everywhere in the UI: `str`, `str | None`,
 * `Array[int | None]`, `Array[Struct{PremisesStruct} | None] | None`.
 *
 * Nullish input yields `""` so callers can fall back with `||`; an unrecognised
 * kind yields `"unknown"` rather than throwing, because a document the backend has
 * not normalised yet must still render.
 */
export function typeLabel(value: LogicalType | null | undefined): string {
  if (value == null || typeof value !== "object" || typeof value.kind !== "string") {
    return "";
  }
  switch (value.kind) {
    case "unit":
      return value.name ?? "unknown";
    case "array":
      return `Array[${typeLabel(value.item) || "unknown"}]`;
    case "struct":
      return `Struct{${value.qualname || "?"}}`;
    case "nullable":
      return `${typeLabel(value.value) || "unknown"} | None`;
    default:
      return "unknown";
  }
}

/* -------------------------------------------------------------------- annotations */

/**
 * One annotation instance. Exactly one of `annotation_type` (a document-owned
 * `AnnotationType`) or `import_module` + `class_name` (a framework annotation such
 * as `NodeLabel`) is set; the backend rejects both or neither.
 */
export interface Annotation {
  readonly annotation_type?: string | null;
  readonly import_module?: string | null;
  readonly class_name?: string | null;
  readonly arguments?: JsonObject;
}

export interface AnnotationField {
  readonly name: string;
  readonly logical_type: LogicalType;
  readonly description?: string | null;
}

/** A project-owned `Annotation` subclass generated into `<pkg>/annotations.py`. */
export interface AnnotationType {
  readonly id: string;
  readonly declaration_name: string;
  readonly namespace: string;
  readonly annotation_id: string;
  readonly description?: string | null;
  readonly fields?: readonly AnnotationField[];
}

/* -------------------------------------------------------------------- expressions */

export interface LiteralExpression {
  readonly kind: "literal";
  readonly value: JsonValue;
  readonly logical_type: LogicalType;
}

export interface FieldExpression {
  readonly kind: "field";
  /** A table, projection or group-qualified table name. */
  readonly source: string;
  readonly path: readonly string[];
  readonly logical_type: LogicalType;
}

export interface OperationExpression {
  readonly kind: "operation";
  readonly operator: string;
  readonly arguments?: readonly Expression[];
  readonly parameters?: JsonObject;
  readonly logical_type: LogicalType;
}

export type Expression = LiteralExpression | FieldExpression | OperationExpression;

/** Operators whose trailing argument or parameter reads better as a labelled verb. */
const OPERATOR_VERB: Readonly<Record<string, string>> = {
  struct_field: "pick",
  map_items: "map items",
  join: "join",
  split_before: "split before",
  split_after: "split after",
  replaced: "replace",
  keep_if: "keep if",
  coalesce: "default to",
  equals: "equals",
  concat: "concat",
  add: "add",
  subtract: "subtract",
  without_nulls: "drop null items",
  where_present: "where present",
};

function literalText(value: JsonValue): string {
  if (value === null) return "null";
  if (typeof value === "string") return JSON.stringify(value);
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) {
    const items = value.slice(0, 3).map(literalText).join(", ");
    return `[${items}${value.length > 3 ? ", …" : ""}]`;
  }
  return "{…}";
}

function renderExpression(expr: Expression | null | undefined, depth: number): string {
  if (expr == null || typeof expr !== "object" || typeof expr.kind !== "string") return "?";
  switch (expr.kind) {
    case "literal":
      return literalText(expr.value ?? null);
    case "field":
      return `${expr.source ?? "?"}.${(expr.path ?? []).join(".")}`;
    case "operation": {
      const args = expr.arguments ?? [];
      const operator = expr.operator ?? "operation";
      const verb = OPERATOR_VERB[operator] ?? operator;
      // Beyond three levels the string stops being readable; the inspector shows the
      // full tree, so summarising truncates rather than lying.
      const ellipsis = depth >= 3;
      const first = ellipsis ? "…" : renderExpression(args[0], depth + 1);
      if (args.length === 0) return operator;
      const named = expr.parameters?.name;
      if (args.length === 1) {
        return typeof named === "string" ? `${first} → ${verb}(${named})` : `${first} → ${verb}`;
      }
      const rest = args
        .slice(1)
        .map((arg) =>
          arg?.kind === "literal"
            ? literalText(arg.value ?? null)
            : ellipsis
              ? "…"
              : renderExpression(arg, depth + 1),
        )
        .join(", ");
      return `${first} → ${verb}(${rest})`;
    }
    default:
      return "?";
  }
}

/**
 * A short human string for an expression stack, e.g.
 * `sites.site_id → where present` or `sites.site_name → default to("Unnamed site")`.
 */
export function expressionSummary(expr: Expression | null | undefined): string {
  const text = renderExpression(expr, 0);
  return text.length > 96 ? `${text.slice(0, 93)}…` : text;
}

/* -------------------------------------------------------------------------- table */

export type NullabilityTrust = "declared" | "enforced" | "defaulted";

/** One table or struct member: the unified `Field[T]` descriptor. */
export interface DataField {
  readonly name: string;
  readonly logical_type: LogicalType;
  readonly description?: string | null;
  readonly external_name?: string | null;
  /** How far a non-nullability is trusted. */
  readonly nullability?: NullabilityTrust;
  /** The physical schema path the member was inferred from. */
  readonly schema_path?: string;
  readonly annotations?: readonly Annotation[];
}

export interface TableGroupMember {
  readonly python_name: string;
  /** A table id for a member, or a group id for a nested group. */
  readonly ref: string;
}

export interface Struct {
  readonly id: string;
  readonly declaration_name: string;
  readonly name: string;
  readonly description?: string | null;
  readonly fields?: readonly DataField[];
  readonly annotations?: readonly Annotation[];
}

export interface Table {
  readonly id: string;
  readonly declaration_name: string;
  readonly name: string;
  readonly description?: string | null;
  readonly fields?: readonly DataField[];
  /** Non-empty for a `TableGroup`. */
  readonly members?: readonly TableGroupMember[];
  readonly annotations?: readonly Annotation[];
  /** The parent group id when this table is a member of a group. */
  readonly group?: string | null;
}

export interface ProjectionField {
  readonly name: string;
  readonly expression: Expression;
  readonly description?: string | null;
}

export interface Projection {
  readonly id: string;
  readonly declaration_name: string;
  readonly name: string;
  readonly description?: string | null;
  readonly fields?: readonly ProjectionField[];
  readonly annotations?: readonly Annotation[];
}

/* ----------------------------------------------------------------------- topology */

/** One `PropertySlot[T]` declaration. */
export interface Property {
  readonly name: string;
  readonly logical_type: LogicalType;
  readonly description?: string | null;
  /** A binding may leave this slot unfilled. */
  readonly optional?: boolean;
  readonly annotations?: readonly Annotation[];
}

export type ComponentTier = "template" | "category" | "concrete";
export type ComponentKind = "node" | "edge";

export interface Component {
  readonly id: string;
  readonly kind: ComponentKind;
  readonly tier: ComponentTier;
  readonly declaration_name: string;
  readonly name: string;
  readonly description?: string | null;
  /** Sugar for the target-neutral `NodeLabel`/`EdgeLabel` annotation. */
  readonly label?: string | null;
  readonly parent?: string | null;
  readonly mixins?: readonly string[];
  readonly source?: string | null;
  readonly target?: string | null;
  readonly properties?: readonly Property[];
  readonly annotations?: readonly Annotation[];
}

/* ------------------------------------------------------------------------ bindings */

export interface PropertyBinding {
  readonly name: string;
  readonly expression: Expression;
}

export interface Binding {
  readonly id: string;
  readonly kind: ComponentKind;
  readonly component: string;
  readonly debug_name?: string | null;
  readonly build_key: Expression;
  readonly source_build_key?: Expression | null;
  readonly target_build_key?: Expression | null;
  /** Endpoint tokens, required exactly when the component declares a category. */
  readonly source?: string | null;
  readonly target?: string | null;
  readonly properties?: readonly PropertyBinding[];
  readonly annotations?: readonly Annotation[];
}

/* -------------------------------------------------------------------- sources … */

export type SourceFormat = "csv" | "json" | "parquet";

/** A `bind_source`: the physical location behind a table or table group. */
export interface Source {
  readonly id: string;
  readonly table: string;
  /** Relative to the project root. */
  readonly location: string;
  readonly format: SourceFormat;
  /** Group sources template `{group_path}` and `{table_name}`. */
  readonly layout?: string | null;
  readonly version?: string | null;
  readonly credential_reference?: string | null;
  readonly annotations?: readonly Annotation[];
}

/** A configured workflow module, resolved through the backend module catalogue. */
export interface Module {
  readonly id: string;
  readonly configuration?: JsonObject | null;
  readonly enabled?: boolean;
}

/* -------------------------------------------------------------- views … project */

export interface Point {
  readonly x: number;
  readonly y: number;
}

export interface Views {
  /** Canvas positions keyed by IR ref; the plan view is always auto-laid-out. */
  readonly topology?: Record<string, Point>;
}

export interface Project {
  readonly name: string;
  readonly package: string;
  readonly description?: string | null;
  /** Data files live here and are inputs the studio never owns. */
  readonly data_directory: string;
}

/** The whole project; the single source of truth the studio edits. */
export interface ProjectDocument {
  readonly schema_version: 1;
  /** Backend-owned; incremented on every accepted patch. */
  readonly revision: number;
  readonly project: Project;
  readonly annotation_types?: readonly AnnotationType[];
  readonly structs?: readonly Struct[];
  readonly tables?: readonly Table[];
  readonly projections?: readonly Projection[];
  readonly components?: readonly Component[];
  readonly bindings?: readonly Binding[];
  readonly sources?: readonly Source[];
  readonly modules?: readonly Module[];
  readonly views?: Views;
}

/* -------------------------------------------------------------- document lookups */

export type DocumentSection =
  | "annotation_types"
  | "structs"
  | "tables"
  | "projections"
  | "components"
  | "bindings"
  | "sources"
  | "modules";

export const SECTION_BY_KIND: Readonly<Record<RefKind, DocumentSection>> = {
  table: "tables",
  struct: "structs",
  projection: "projections",
  component: "components",
  binding: "bindings",
  source: "sources",
  module: "modules",
  annotation_type: "annotation_types",
};

/** The item type of one document section. */
export type SectionItem<K extends DocumentSection> = NonNullable<ProjectDocument>[K] extends
  | readonly (infer I)[]
  | undefined
  ? I
  : never;

/**
 * `document.tables` and friends, always array-shaped even for a partial payload: a
 * half-built backend may omit a section, and the UI must render rather than crash.
 */
export function sectionItems<K extends DocumentSection>(
  document: ProjectDocument | null | undefined,
  section: K,
): readonly SectionItem<K>[] {
  const value = document?.[section];
  return (Array.isArray(value) ? value : []) as readonly SectionItem<K>[];
}

export interface Identified {
  readonly id: string;
}

export function findInSection(
  document: ProjectDocument | null | undefined,
  section: DocumentSection,
  id: string,
): Identified | null {
  for (const item of sectionItems(document, section)) {
    if (item && (item as Identified).id === id) return item as Identified;
  }
  return null;
}

/** Replace or append one item in a section, mirroring `ProjectDocument.replaced`. */
export function replaced<D extends ProjectDocument, I extends Identified>(
  document: D,
  section: DocumentSection,
  item: I,
): D {
  const items = [...sectionItems(document, section)] as I[];
  const index = items.findIndex((existing) => existing.id === item.id);
  if (index >= 0) items[index] = item;
  else items.push(item);
  return { ...document, [section]: items } as D;
}

/** Drop one item by id, mirroring `ProjectDocument.removed`. */
export function removed<D extends ProjectDocument>(
  document: D,
  section: DocumentSection,
  id: string,
): D {
  const items = sectionItems(document, section).filter(
    (item) => (item as Identified).id !== id,
  );
  return { ...document, [section]: items } as D;
}

export const emptyDocument = (name = "project", pkg = "kg_project"): ProjectDocument => ({
  schema_version: SCHEMA_VERSION,
  revision: 0,
  project: { name, package: pkg, description: null, data_directory: "data" },
  annotation_types: [],
  structs: [],
  tables: [],
  projections: [],
  components: [],
  bindings: [],
  sources: [],
  modules: [],
  views: { topology: {} },
});

/* ------------------------------------------------------------ entity descriptors */

interface EntityLike extends Identified {
  readonly name?: string;
  readonly declaration_name?: string;
  readonly description?: string | null;
}

const SECTION_LABEL: Record<DocumentSection, string> = {
  tables: "table",
  structs: "struct",
  projections: "projection",
  components: "component",
  bindings: "binding",
  sources: "source",
  modules: "module",
  annotation_types: "annotation type",
};

/** The kind spelled out for badges and titles: `node concrete`, `table group`, … */
export function entityLabel(entity: EntityLike | null, section: DocumentSection): string {
  if (!entity) return "unknown";
  switch (section) {
    case "components": {
      const component = entity as unknown as Component;
      return `${component.kind} ${component.tier}`;
    }
    case "tables":
      return (entity as unknown as Table).members?.length ? "table group" : "table";
    case "bindings":
      return `${(entity as unknown as Binding).kind} binding`;
    case "sources":
      return `${(entity as unknown as Source).format} source`;
    case "modules":
      return (entity as unknown as Module).enabled === false ? "module (off)" : "module";
    default:
      return SECTION_LABEL[section].toLowerCase();
  }
}

/** The label an entity row shows: its name, falling back to its declaration name. */
export const entityName = (entity: EntityLike | null): string =>
  entity?.name ?? entity?.declaration_name ?? entity?.id ?? "";

/** One addressable child of an entity: a field, slot, filled slot, member, argument. */
export interface ChildRef {
  readonly ref: string;
  readonly label: string;
  readonly detail: string;
  readonly kind: "field" | "property" | "expression" | "member" | "argument";
}

export interface EntitySummary {
  readonly ref: string;
  readonly section: DocumentSection;
  readonly id: string;
  readonly title: string;
  readonly kind: string;
  readonly description: string | null;
  /** Field/slot counts, endpoint ids, locations — one quiet line of substance. */
  readonly detail: string;
  readonly children: readonly ChildRef[];
}

/**
 * Everything the inspector, the palette and the problems panel need to say about a
 * ref, in one pass over the document. `null` when the ref dangles, which the caller
 * must render as "this no longer exists" rather than pretending.
 */
export function describeRef(
  document: ProjectDocument | null | undefined,
  ref: string | null | undefined,
): EntitySummary | null {
  const parsed = parseRef(ref);
  if (!document || !parsed) return null;
  const section = SECTION_BY_KIND[parsed.kind];
  const entity = findInSection(document, section, parsed.id) as EntityLike | null;
  if (!entity) return null;

  const refFor = (part: string, name?: string) => buildRef(parsed.kind, parsed.id, part, name);
  const children: ChildRef[] = [];
  let detail = "";

  switch (section) {
    case "tables":
    case "structs": {
      const item = entity as Table;
      const fields = item.fields ?? [];
      detail = `${fields.length} field${fields.length === 1 ? "" : "s"}`;
      for (const field of fields) {
        children.push({
          ref: refFor("field", field.name),
          label: field.name,
          detail: typeLabel(field.logical_type),
          kind: "field",
        });
      }
      // `members` and `group` exist only on Table; a Struct never has either.
      const members = section === "tables" ? item.members : undefined;
      if (members && members.length > 0) {
        detail += ` · ${members.length} member${members.length === 1 ? "" : "s"}`;
        for (const member of members) {
          children.push({
            ref: refFor("member", member.python_name),
            label: member.python_name,
            detail: member.ref,
            kind: "member",
          });
        }
      }
      if (section === "tables" && item.group) detail += ` · in group ${item.group}`;
      break;
    }
    case "projections": {
      const item = entity as unknown as Projection;
      const fields = item.fields ?? [];
      detail = `${fields.length} projection field${fields.length === 1 ? "" : "s"}`;
      for (const field of fields) {
        children.push({
          ref: refFor("field", field.name),
          label: field.name,
          detail: expressionSummary(field.expression),
          kind: "expression",
        });
      }
      break;
    }
    case "components": {
      const item = entity as unknown as Component;
      const properties = item.properties ?? [];
      detail = `${properties.length} slot${properties.length === 1 ? "" : "s"}`;
      if (item.label) detail += ` · label ${item.label}`;
      if (item.parent) detail += ` · parent ${item.parent}`;
      if (item.mixins?.length) detail += ` · mixins ${item.mixins.join(", ")}`;
      if (item.source || item.target) detail += ` · ${item.source ?? "?"} → ${item.target ?? "?"}`;
      for (const property of properties) {
        children.push({
          ref: refFor("property", property.name),
          label: property.name,
          detail: `${typeLabel(property.logical_type)}${property.optional ? " (optional)" : ""}`,
          kind: "property",
        });
      }
      break;
    }
    case "bindings": {
      const item = entity as unknown as Binding;
      const properties = item.properties ?? [];
      detail = `${properties.length} filled slot${properties.length === 1 ? "" : "s"} · component ${item.component}`;
      children.push({
        ref: refFor("build_key"),
        label: "build_key",
        detail: expressionSummary(item.build_key),
        kind: "expression",
      });
      for (const property of properties) {
        children.push({
          ref: refFor("property", property.name),
          label: property.name,
          detail: expressionSummary(property.expression),
          kind: "expression",
        });
      }
      break;
    }
    case "sources": {
      const item = entity as unknown as Source;
      detail = `${item.location} → table ${item.table}`;
      if (item.layout) detail += ` · layout ${item.layout}`;
      if (item.version) detail += ` · version ${item.version}`;
      break;
    }
    case "modules": {
      const item = entity as unknown as Module;
      const configuration = item.configuration;
      detail =
        configuration && Object.keys(configuration).length > 0
          ? JSON.stringify(configuration)
          : "default configuration";
      for (const [key, value] of Object.entries(configuration ?? {})) {
        children.push({
          ref: refFor("configuration", key),
          label: key,
          detail: typeof value === "string" ? value : JSON.stringify(value),
          kind: "argument",
        });
      }
      break;
    }
    case "annotation_types": {
      const item = entity as unknown as AnnotationType;
      const fields = item.fields ?? [];
      detail = `${fields.length} argument${fields.length === 1 ? "" : "s"} · ${item.namespace}.${item.annotation_id}`;
      for (const field of fields) {
        children.push({
          ref: refFor("field", field.name),
          label: field.name,
          detail: typeLabel(field.logical_type),
          kind: "field",
        });
      }
      break;
    }
  }

  return {
    ref: buildRef(parsed.kind, parsed.id),
    section,
    id: parsed.id,
    title: entityName(entity),
    kind: entityLabel(entity, section),
    description: entity.description ?? null,
    detail,
    children,
  };
}

/** The counts behind the header's "7 components · 12 bindings" line. */
export const documentCounts = (document: ProjectDocument | null) => ({
  tables: sectionItems(document, "tables").length,
  structs: sectionItems(document, "structs").length,
  projections: sectionItems(document, "projections").length,
  components: sectionItems(document, "components").length,
  bindings: sectionItems(document, "bindings").length,
  sources: sectionItems(document, "sources").length,
  modules: sectionItems(document, "modules").length,
});

/**
 * Every IR entity in the document, as the command palette lists them: name, kind and
 * ref. Ordered by section so the palette reads like the document.
 */
export function documentEntities(
  document: ProjectDocument | null | undefined,
): readonly {
  ref: string;
  label: string;
  kind: string;
  detail: string;
  section: DocumentSection;
}[] {
  if (!document) return [];
  const out: {
    ref: string;
    label: string;
    kind: string;
    detail: string;
    section: DocumentSection;
  }[] = [];
  const sections: DocumentSection[] = [
    "components",
    "bindings",
    "tables",
    "structs",
    "projections",
    "sources",
    "modules",
    "annotation_types",
  ];
  const kindFor: Record<DocumentSection, RefKind> = {
    components: "component",
    bindings: "binding",
    tables: "table",
    structs: "struct",
    projections: "projection",
    sources: "source",
    modules: "module",
    annotation_types: "annotation_type",
  };
  for (const section of sections) {
    for (const item of sectionItems(document, section)) {
      const entity = item as EntityLike;
      out.push({
        ref: buildRef(kindFor[section], entity.id),
        label: entityName(entity) || entity.id,
        kind: entityLabel(entity, section),
        detail: entity.declaration_name ?? entity.id,
        section,
      });
    }
  }
  return out;
}

/**
 * A table and every group above it, nearest first.
 *
 * A `bind_source` may name a table or the group it belongs to — the framework fans a
 * group source out to its members — so "is this table bound, and by what?" has to walk
 * the same chain. Stops at a repeated id, so a cycle cannot spin here.
 */
export function tableAncestry(tables: readonly Table[], table: Table): Table[] {
  const chain: Table[] = [];
  const visited = new Set<string>();
  let walk: Table | undefined = table;
  while (walk && !visited.has(walk.id)) {
    visited.add(walk.id);
    chain.push(walk);
    const groupId: string | null | undefined = walk.group;
    walk = groupId
      ? tables.find((item) => item.id === groupId || item.name === groupId)
      : undefined;
  }
  return chain;
}

/** Whether a source names this table: by id or by its declared name. */
export function sourceBindsTable(source: { table?: string | null }, table: Table): boolean {
  return source.table === table.id || source.table === table.name;
}
