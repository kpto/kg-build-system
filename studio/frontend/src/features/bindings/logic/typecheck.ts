/**
 * The logical-type derivation the composer runs locally.
 *
 * This is `studio/backend/studio_backend/ir/infer.py` restated in TypeScript over the
 * same JSON shapes: every rule here has the same consequence as the framework rule it
 * cites, and the backend remains the authority (`ir.normalize` recomputes every
 * `logical_type` on save). The composer needs it anyway — the seam between two blocks
 * *is* the derivation, and the palette is filtered against it.
 *
 * Two rules dominate, exactly as `docs/AUTHORING_IR_CONTRACT.md` states:
 *   * string / numeric / bool operations require a NON-NULL input — a nullable value
 *     must first be unwrapped by `where_present` (filters rows) or `coalesce`
 *     (`default_to`, keeps them);
 *   * `prepend` and `append` are both `concat`, and only the *argument order* records
 *     which was written, so this module reads the order back the same way.
 */

import type { Expression, JsonValue, LogicalType, NonNullableLogicalType, OperationExpression } from "@/lib/ir";
import { array, isNullable, nullable, unwrapNullable } from "@/lib/ir";
import type { BindingContext, InferResult } from "./context";
import { fail, nullableArray, ok, selectableByName, selectablePaths, structMembers, typeEquals } from "./context";

export const unitType = (name: string): LogicalType | null =>
  ["bool", "int", "float", "str", "date", "time", "timestamp", "uuid"].includes(name)
    ? { kind: "unit", name: name as "str" }
    : null;

const NUMERIC = new Set(["int", "float"]);

/** The shape token `matches_shape` compares against, for messages and filters. */
export function shapeOf(value: LogicalType | null): string {
  if (value == null) return "unknown";
  const base = unwrapNullable(value);
  if (base.kind === "array") {
    const item = unwrapNullable(base.item);
    if (item.kind === "struct") return "array_of_struct";
    if (item.kind === "unit" && item.name === "str") return "array_of_non_null_str";
    return "array";
  }
  if (base.kind === "struct") return "struct";
  if (base.kind === "unit") return `unit:${base.name}`;
  return "any";
}

/* ---------------------------------------------------------------------- operations */

/** The member name a `struct_field` / `map_items` node records in `parameters`. */
export function memberName(node: OperationExpression): string | null {
  const value = node.parameters?.["name"];
  return typeof value === "string" && value.length > 0 ? value : null;
}

function memberTypeOf(
  ctx: BindingContext,
  struct: { kind: "struct"; module: string; qualname: string },
  name: string,
): InferResult {
  const member = structMembers(ctx, struct).find((item) => item.name === name);
  if (!member) return failMember(struct.qualname, name);
  return { type: member.logical_type, error: null };
}

export function failMember(qualname: string, name: string): InferResult {
  return {
    type: null,
    error: `${qualname} has no member '${name}'; pick one it declares`,
  };
}

const withOperand = (
  node: OperationExpression,
  index: number,
): { type: LogicalType | null; error: string | null } =>
  ({ type: null, error: `operator ${node.operator} is missing argument ${index}` });

/**
 * The result type of one operation node, given its already-inferred arguments.
 * `infer.py::_RULES` is the source; each branch cites the framework file that enforces
 * it once the project is generated.
 */
export function operationResult(
  ctx: BindingContext,
  node: OperationExpression,
  argumentTypes: readonly (LogicalType | null)[],
): InferResult {
  const subject = argumentTypes[0] ?? null;
  const operand = (index: number): LogicalType | null => argumentTypes[index] ?? null;
  const missing = (index: number): InferResult => withOperand(node, index);

  switch (node.operator) {
    // expressions/selections.py — one level of an array, outer nullability dropped.
    case "expand": {
      if (subject == null) return missing(0);
      const base = unwrapNullable(subject);
      if (base.kind !== "array") return { type: null, error: "making one row per item works on a list" };
      return { type: base.item, error: null };
    }
    // expressions/nullable.py — the unwrap the palette must force before any calculation.
    case "where_present": {
      if (subject == null) return missing(0);
      if (!isNullable(subject)) {
        return { type: null, error: "keeping rows where the value is present only applies to a value that might be missing" };
      }
      return { type: unwrapNullable(subject), error: null };
    }
    case "coalesce": {
      if (subject == null) return missing(0);
      if (!isNullable(subject)) {
        return { type: null, error: "using a value when one is missing only applies to a value that might be missing" };
      }
      const inner = unwrapNullable(subject);
      const fallback = operand(1);
      if (fallback == null) return missing(1);
      if (!typeEquals(inner, fallback) && !typeEquals(nullable(inner), fallback)) {
        return {
          type: null,
          error: `using a value when one is missing needs ${describe(inner)} here, and what it is given is ${describe(fallback)}`,
        };
      }
      return { type: inner, error: null };
    }
    // expressions/values.py — the predicate is a plain non-null bool.
    case "keep_if": {
      const predicate = operand(1);
      if (predicate == null) return missing(1);
      if (predicate.kind !== "unit" || predicate.name !== "bool") {
        return { type: null, error: "keeping rows where a test holds needs a true-or-false test that is never missing" };
      }
      return { type: subject, error: null };
    }
    // expressions/selections.py — a member of a record, nullability propagated through it.
    case "struct_field": {
      if (subject == null) return missing(0);
      const base = unwrapNullable(subject);
      if (base.kind !== "struct") {
        return { type: null, error: "taking one member reads a member of a nested record" };
      }
      const name = memberName(node);
      if (!name) return { type: null, error: "taking one member has to be told which member to read" };
      const member = memberTypeOf(ctx, base, name);
      if (member.error || member.type == null) return member;
      const memberType = member.type;
      const madeNullable = isNullable(subject) && !isNullable(memberType);
      return {
        type: madeNullable ? nullable(memberType as NonNullableLogicalType) : memberType,
        error: null,
      };
    }
    case "map_items": {
      if (subject == null) return missing(0);
      const base = unwrapNullable(subject);
      if (base.kind !== "array") return { type: null, error: "taking one member from every item works on a list" };
      const element = base.item;
      const elementStruct = unwrapNullable(element);
      if (elementStruct.kind !== "struct") {
        return { type: null, error: `this list holds ${describe(element)}, which has no member to read` };
      }
      const name = memberName(node);
      if (!name) return { type: null, error: "taking one member from every item has to be told which member to read" };
      const member = memberTypeOf(ctx, elementStruct, name);
      if (member.error || member.type == null) return member;
      const memberType = member.type;
      const item =
        isNullable(element) && !isNullable(memberType)
          ? nullable(memberType as NonNullableLogicalType)
          : memberType;
      return { type: nullableArray(item, subject), error: null };
    }
    // expressions/arrays.py — item nullability only.
    case "without_nulls": {
      if (subject == null) return missing(0);
      const base = unwrapNullable(subject);
      if (base.kind !== "array") return { type: null, error: "dropping missing items works on a list" };
      if (!isNullable(base.item)) {
        return {
          type: null,
          error: `dropping missing items has nothing to drop: every item of ${describe(subject)} already has a value`,
        };
      }
      return { type: nullableArray(unwrapNullable(base.item), subject), error: null };
    }
    case "sorted":
    case "distinct": {
      if (subject == null) return missing(0);
      if (unwrapNullable(subject).kind !== "array") {
        return { type: null, error: `${node.operator === "sorted" ? "sorting" : "deduplicating"} the items works on a list` };
      }
      return { type: subject, error: null };
    }
    case "join": {
      if (subject == null) return missing(0);
      const base = unwrapNullable(subject);
      if (base.kind !== "array") return { type: null, error: "joining the items into one text works on a list" };
      if (!typeEquals(base.item, { kind: "unit", name: "str" })) {
        return {
          type: null,
          error: `joining the items into one text joins a list of text that is always there, and this list holds ${describe(base.item)}`,
        };
      }
      const separator = operand(1);
      if (separator == null) return missing(1);
      if (!typeEquals(separator, { kind: "unit", name: "str" })) {
        return { type: null, error: "join needs the text to write between the items" };
      }
      const str: LogicalType = { kind: "unit", name: "str" };
      return { type: isNullable(subject) ? nullable(str as NonNullableLogicalType) : str, error: null };
    }
    case "add":
    case "subtract": {
      if (subject == null) return missing(0);
      const base = unwrapNullable(subject);
      if (isNullable(subject) || base.kind !== "unit" || !NUMERIC.has(base.name)) {
        return {
          type: null,
          error: `arithmetic works on a number that is never missing, and what it is given is ${describe(subject)}`,
        };
      }
      const other = operand(1);
      if (other == null) return missing(1);
      if (!typeEquals(base, other)) {
        return {
          type: null,
          error: `arithmetic needs ${describe(base)} here, and what it is given is ${describe(other)}`,
        };
      }
      return { type: base, error: null };
    }
    // expressions/numeric.py — only IntExpression answers `text()`.
    case "text": {
      if (subject == null) return missing(0);
      if (!typeEquals(subject, { kind: "unit", name: "int" })) {
        return { type: null, error: "writing a number as text works on a whole number" };
      }
      return { type: { kind: "unit", name: "str" }, error: null };
    }
    // expressions/text.py — every text operation needs text that is never missing.
    case "concat": {
      const str: LogicalType = { kind: "unit", name: "str" };
      if (subject == null) return missing(0);
      if (!typeEquals(subject, str)) {
        return {
          type: null,
          error: `putting text in front of or behind other text needs text that is never missing, and what it is given is ${describe(subject)}`,
        };
      }
      const other = operand(1);
      if (other == null) return missing(1);
      if (!typeEquals(other, str)) {
        return { type: null, error: "concat needs the other piece of text to be text that is never missing" };
      }
      return { type: str, error: null };
    }
    case "split_before":
    case "split_after": {
      const str: LogicalType = { kind: "unit", name: "str" };
      if (subject == null) return missing(0);
      if (!typeEquals(subject, str)) {
        return { type: null, error: "cutting text works on text that is never missing" };
      }
      const marker = operand(1);
      if (marker == null) return missing(1);
      if (!typeEquals(marker, str)) return { type: null, error: "the marker to cut the text at must be text" };
      return { type: str, error: null };
    }
    case "replaced": {
      const str: LogicalType = { kind: "unit", name: "str" };
      if (subject == null) return missing(0);
      if (!typeEquals(subject, str)) return { type: null, error: "replacing text works on text that is never missing" };
      for (const index of [1, 2]) {
        const value = operand(index);
        if (value == null) return missing(index);
        if (!typeEquals(value, str)) return { type: null, error: "replace takes two pieces of text" };
      }
      return { type: str, error: null };
    }
    case "equals": {
      const str: LogicalType = { kind: "unit", name: "str" };
      if (subject == null) return missing(0);
      if (!typeEquals(subject, str)) {
        return { type: null, error: `comparing text needs text that is never missing, and what it is given is ${describe(subject)}` };
      }
      const other = operand(1);
      if (other == null) return missing(1);
      if (!typeEquals(other, str)) return { type: null, error: "comparing text needs the text to compare against" };
      return { type: { kind: "unit", name: "bool" }, error: null };
    }
    // expressions/boolean.py
    case "not": {
      if (subject == null) return missing(0);
      if (!typeEquals(subject, { kind: "unit", name: "bool" })) {
        return { type: null, error: "flipping true and false works on a true-or-false answer" };
      }
      return { type: { kind: "unit", name: "bool" }, error: null };
    }
    case "and":
    case "or": {
      const bool: LogicalType = { kind: "unit", name: "bool" };
      if (subject == null) return missing(0);
      if (!typeEquals(subject, bool)) return { type: null, error: "combining tests needs a true-or-false answer" };
      const other = operand(1);
      if (other == null) return missing(1);
      if (!typeEquals(other, bool)) return { type: null, error: "combining tests needs another true-or-false answer" };
      return { type: bool, error: null };
    }
    default:
      return {
        type: null,
        error: `'${node.operator}' is not an operation of this framework`,
      };
  }
}

/** The author-facing spelling of a type in a rejection sentence. */
export function describe(value: LogicalType | null): string {
  if (value == null) return "an unknown type";
  if (value.kind === "nullable") return `${describe(value.value)} | None`;
  if (value.kind === "array") return `Array[${describe(value.item)}]`;
  if (value.kind === "struct") return `Struct ${value.qualname}`;
  return value.name;
}

/* -------------------------------------------------------------------- field paths */

/**
 * The type of `<source>.<path>` as `ir/infer.py::field_path_type` computes it:
 * a declared field, then one struct member at a time, with nullability propagated
 * along the whole path (`a non-null member reached through a nullable record is
 * itself nullable`) and no stepping into a list (`pick` is not offered on an array
 * selection — `expand` or `map_items` owns that).
 */
export function fieldPathType(
  ctx: BindingContext,
  source: string,
  path: readonly string[],
): InferResult {
  if (path.length === 0) return fail(`${source} needs a field name after it`);
  const walked = walkFieldPath(ctx, source, path);
  if (!walked.error) return walked;
  // The document is the source of truth and the index a cache of it, so the declared
  // field types are read from the document; the index answers only for what the
  // document cannot say on its own (a derived projection output).
  const entry = selectableByName(ctx, source);
  const listed = entry
    ? selectablePaths(ctx, entry).find(
        (candidate) => candidate.path.join(".") === path.join("."),
      )
    : undefined;
  if (listed) return ok(listed.logical_type);
  return walked;
}

function walkFieldPath(ctx: BindingContext, source: string, path: readonly string[]): InferResult {
  let current = firstFieldType(ctx, source, path[0] as string);
  if (current.error) return current;
  for (let index = 1; index < path.length && current.type != null; index += 1) {
    const segment = path[index] as string;
    const reached = `${source}.${path.slice(0, index).join(".")}`;
    const parentNullable = isNullable(current.type);
    const base = unwrapNullable(current.type);
    if (base.kind === "array") {
      return fail(
        `${reached} is a list, so '${segment}' is not something to read off it — make one row per item, or take that member from every item`,
      );
    }
    if (base.kind !== "struct") {
      return fail(`${reached} is ${base.kind}, which has no member '${segment}' to read`);
    }
    const member = structMembers(ctx, base).find((item) => item.name === segment);
    if (!member) {
      return fail(`${base.qualname} has no member '${segment}'`);
    }
    current = ok(
      parentNullable && !isNullable(member.logical_type)
        ? nullable(member.logical_type as NonNullableLogicalType)
        : member.logical_type,
    );
  }
  return current;
}

function firstFieldType(ctx: BindingContext, source: string, field: string): InferResult {
  // The document is the source of truth and the index is a cache of it, so the
  // declared field type is read from the document; the index answers only for a
  // source the document has not (yet) declared.
  if (ctx.document.tables?.some((table) => table.name === source || table.id === source)) {
    const table = ctx.document.tables.find(
      (item) => item.name === source || item.id === source,
    );
    const declared = (table?.fields ?? []).find((item) => item.name === field);
    return declared ? ok(declared.logical_type) : fail(`${source} declares no field '${field}'`);
  }
  const projection = (ctx.document.projections ?? []).find(
    (item) => item.name === source || item.id === source,
  );
  if (projection) {
    const output = (projection.fields ?? []).find((item) => item.name === field);
    // A projection output is typed by its implementation, which is exactly what the
    // index does (`ir/index.py::_projection_rows`); infer it here rather than trust
    // the stored type, which the client may have stale.
    if (!output) return fail(`projection ${source} declares no output '${field}'`);
    return inferExpression(ctx, output.expression);
  }
  const entry = selectableByName(ctx, source);
  if (entry) {
    const listed = selectablePaths(ctx, entry).find(
      (candidate) => candidate.path.length === 1 && candidate.path[0] === field,
    );
    if (listed) return ok(listed.logical_type);
  }
  return fail(`${source} is not a table or projection of this project`);
}

/* ------------------------------------------------------------------------- literals */

/**
 * A literal's type as `expressions/literals.py` would read it. Temporals and UUIDs
 * cross the JSON boundary already frozen as canonical text while the node keeps the
 * real unit, so the stored type is used when it is a text-canonical unit and a plain
 * string is otherwise inferred.
 */
export function literalType(value: JsonValue, declared?: LogicalType | null): LogicalType {
  if (declared != null) return declared;
  if (value === null) return nullable({ kind: "unit", name: "str" });
  if (typeof value === "boolean") return { kind: "unit", name: "bool" };
  if (typeof value === "number") {
    return { kind: "unit", name: Number.isInteger(value) ? "int" : "float" };
  }
  if (typeof value === "string") return { kind: "unit", name: "str" };
  if (Array.isArray(value)) {
    if (value.length === 0) return array(nullable({ kind: "unit", name: "str" }));
    const items = value.map((item) => literalType(item));
    const anyNullable = items.some(isNullable);
    const first = items[0] ?? { kind: "unit", name: "str" };
    const same = items.every((item) => typeEquals(item, first));
    const item = same ? first : nullable({ kind: "unit", name: "str" });
    return array(anyNullable && !isNullable(item) ? nullable(unwrapNullable(item)) : item);
  }
  return { kind: "unit", name: "str" };
}

/* --------------------------------------------------------------------- expression */

/** The type a whole expression resolves to, or the first rule it breaks. */
export function inferExpression(ctx: BindingContext, expression: Expression | null | undefined): InferResult {
  if (!expression || typeof expression !== "object") return { type: null, error: "no expression yet" };
  if (expression.kind === "literal") {
    return { type: expression.logical_type ?? literalType(expression.value ?? null), error: null };
  }
  if (expression.kind === "field") {
    return fieldPathType(ctx, expression.source, expression.path ?? []);
  }
  const argumentTypes = (expression.arguments ?? []).map((argument) => inferExpression(ctx, argument).type);
  const firstBroken = (expression.arguments ?? [])
    .map((argument) => inferExpression(ctx, argument))
    .find((result) => result.error);
  if (firstBroken) return firstBroken;
  if (argumentTypes.length !== (expression.arguments ?? []).length) {
    return { type: null, error: "an operation is missing an argument" };
  }
  return operationResult(ctx, expression, argumentTypes);
}
