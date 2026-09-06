/**
 * The document + index pair every pure binding rule reads.
 *
 * Nothing here mutates: the composer derives types and availability from these two
 * payloads, and the only way a value leaves the feature is through
 * `FeatureProps.apply`, which sends the whole document to the backend.
 *
 * Type reads prefer the index (the backend computed those types from the document, so
 * they cannot disagree with the generator) and fall back to walking the document,
 * which keeps a just-edited table field usable before `GET /api/index` is refreshed.
 */

import type { AuthoringIndex, ResolvedProperty, SelectableEntry } from "@/lib/types";
import type {
  ArrayType,
  LogicalType,
  NonNullableLogicalType,
  ProjectDocument,
  Struct,
  StructType,
} from "@/lib/ir";
import { array, isNullable, nullable, unwrapNullable } from "@/lib/ir";

export interface BindingContext {
  readonly document: ProjectDocument;
  readonly index: AuthoringIndex | null;
}

export interface InferResult {
  readonly type: LogicalType | null;
  /** A complete sentence naming the framework rule that stopped the derivation. */
  readonly error: string | null;
}

export const ok = (type: LogicalType): InferResult => ({ type, error: null });

export const fail = (error: string): InferResult => ({ type: null, error });

/** The one place the pair is built, so every read in the feature sees the same thing. */
export function buildBindingContext(document: ProjectDocument, index: AuthoringIndex | null): BindingContext {
  return { document, index };
}

/* ------------------------------------------------------------------ structural equality */

/** Logical types are plain JSON objects, so equality is structural and total. */
export function typeEquals(a: LogicalType | null, b: LogicalType | null): boolean {
  if (a === b) return true;
  if (a == null || b == null) return false;
  if (a.kind !== b.kind) return false;
  switch (a.kind) {
    case "unit":
      return a.name === (b as typeof a).name;
    case "struct":
      return a.qualname === (b as typeof a).qualname;
    case "array":
      return typeEquals(a.item, (b as ArrayType).item);
    case "nullable":
      return typeEquals(a.value, (b as { value: LogicalType }).value);
    default:
      return false;
  }
}

/**
 * `binding/factories.py::_compatible` — an exact match, or a non-null expression
 * given to a nullable slot. Nothing else is compatible: a nullable value never
 * satisfies a non-null slot, which is the whole reason the palette refuses to
 * calculate on a nullable tip.
 */
export function compatible(expected: LogicalType | null, actual: LogicalType | null): boolean {
  if (typeEquals(expected, actual)) return true;
  if (expected == null || actual == null) return false;
  return isNullable(expected) && typeEquals(unwrapNullable(expected), actual);
}

/* ------------------------------------------------------------------------- sources */

export function selectables(ctx: BindingContext): readonly SelectableEntry[] {
  return ctx.index?.selectable ?? [];
}

/** A selectable addressed by the logical name an expression stores in `source`. */
export function selectableByName(
  ctx: BindingContext,
  name: string | null | undefined,
): SelectableEntry | null {
  if (!name) return null;
  return selectables(ctx).find((entry) => entry.name === name || entry.id === name) ?? null;
}

/**
 * Every field a source offers, flattened. `index.selectable[].paths` is the
 * authoritative list (the backend flattens nested struct members into it); a
 * document-only source is walked locally so a fresh table is still usable.
 */
export function selectablePaths(ctx: BindingContext, entry: SelectableEntry) {
  if (entry.paths && entry.paths.length > 0) return entry.paths;
  const fields =
    ctx.document.tables?.find((table) => table.id === entry.id || table.name === entry.name)?.fields ??
    ctx.document.projections?.find((item) => item.id === entry.id)
      ?.fields?.map((field) => ({
        name: field.name,
        logical_type: field.expression?.logical_type ?? null,
        description: field.description ?? null,
      })) ??
    [];
  return fields
    .filter((field) => field.logical_type != null)
    .map((field) => ({
      path: [field.name] as string[],
      logical_type: field.logical_type as LogicalType,
      nullable: isNullable(field.logical_type as LogicalType),
      description: (field as { description?: string | null }).description ?? null,
    }));
}

/* ------------------------------------------------------------------------ structs */

export function structByType(ctx: BindingContext, reference: StructType): Struct | null {
  const matches = (ctx.document.structs ?? []).filter(
    (item) => item.declaration_name === reference.qualname,
  );
  if (matches.length === 1) return matches[0] ?? null;
  return null;
}

/** The members a struct offers, from the document then the index. */
export function structMembers(ctx: BindingContext, reference: StructType): readonly ResolvedProperty[] {
  const declared = structByType(ctx, reference);
  if (declared) return declared.fields ?? [];
  const fromIndex = (ctx.index?.structs ?? []).find(
    (item) => item.declaration_name === reference.qualname || item.id === reference.qualname,
  );
  return fromIndex?.fields ?? [];
}

/* ----------------------------------------------------------------- component slots */

export function componentEntry(ctx: BindingContext, id: string | null | undefined) {
  if (!id) return null;
  return (ctx.index?.components ?? []).find((entry) => entry.id === id) ?? null;
}

/** The document component, for the cases the index does not carry. */
export function documentComponent(ctx: BindingContext, id: string | null | undefined) {
  if (!id) return null;
  return (ctx.document.components ?? []).find((entry) => entry.id === id) ?? null;
}

/**
 * The effective slots a binding must fill.
 *
 * Their *types* come from the index — `index.components[].resolved_properties` is
 * what the task and `API.md` name as the slot declaration, and it already resolves
 * inheritance. Their *order* is the order the generated record has them (own slots,
 * then inherited), which the document's own lineage answers, so the two are merged:
 * index types in document-lineage order, with anything the index has not caught up
 * with appended.
 */
export function resolvedSlots(ctx: BindingContext, componentId: string): readonly ResolvedProperty[] {
  const entry = componentEntry(ctx, componentId);
  const declared = new Map<string, ResolvedProperty>();
  for (const slot of entry?.resolved_properties ?? []) declared.set(slot.name, slot);

  const component = documentComponent(ctx, componentId);
  const order: string[] = [];
  if (component) {
    const seen = new Set<string>();
    const visit = (id: string | null | undefined, guard = 0): void => {
      if (!id || seen.has(id) || guard > 32) return;
      seen.add(id);
      const target = documentComponent(ctx, id);
      if (!target) return;
      for (const mixin of target.mixins ?? []) visit(mixin, guard + 1);
      visit(target.parent, guard + 1);
      for (const slot of target.properties ?? []) {
        if (!declared.has(slot.name)) {
          declared.set(slot.name, {
            name: slot.name,
            logical_type: slot.logical_type,
            optional: slot.optional ?? false,
            declared_by: target.id,
          });
        }
      }
    };
    visit(componentId);
    order.push(...(component.properties ?? []).map((slot) => slot.name));
    order.push(...[...declared.keys()].filter((name) => !order.includes(name)));
  }
  const ordered = order.length > 0 ? order : [...declared.keys()];
  return ordered.filter((name) => declared.has(name)).map((name) => declared.get(name) as ResolvedProperty);
}

/* --------------------------------------------------------------------- array rules */

export function arrayItem(value: LogicalType | null): LogicalType | null {
  if (value == null) return null;
  const base = unwrapNullable(value);
  return base.kind === "array" ? base.item : null;
}

export const nullableArray = (item: LogicalType, subject: LogicalType): LogicalType => {
  const list: NonNullableLogicalType = array(item);
  return isNullable(subject) ? nullable(list) : list;
};
