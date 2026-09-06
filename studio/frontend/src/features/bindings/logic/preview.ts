/**
 * The authoring-Python preview.
 *
 * A local renderer over the expression tree, following `docs/AUTHORING_IR_CONTRACT.md`
 * and mirroring `studio_backend/generate/expressions.py`. It exists so the stack
 * teaches the DSL — the UI shows the code the stack means — and it is labelled a
 * *preview* everywhere it appears: the backend generator remains the authority, and
 * this module deliberately renders no imports, no module layout and no anchors.
 *
 * The three rules that shape the output:
 *
 *   * **`pick` folds a path.** A `field` node whose path has several segments is one
 *     accessor chain with one `.pick` per segment, because that is what the framework
 *     compiled to produce it — no `struct_field` node exists for it. A `struct_field`
 *     node therefore renders as a `.pick` only above an operation.
 *   * **`prepend`/`append` are both `concat`.** The argument order says which method
 *     was written, so a literal in argument 0 renders as `.prepend(...)`.
 *   * **A stack ends at a `ValueExpression`.** `.expression` is written when the chain
 *     is still a selection, because the binding slots take expressions and a method
 *     argument such as `add(other)` refuses a bare selection.
 */

import type { Expression, JsonValue, LogicalType, OperationExpression, UnitName } from "@/lib/ir";
import { unwrapNullable } from "@/lib/ir";
import type { BindingContext } from "./context";
import { selectableByName, structByType, structMembers } from "./context";

export const INDENT = "    ";
export const LINE_WIDTH = 88;

const SELECTION_METHODS: Readonly<Record<string, string>> = { expand: "expand", where_present: "where_present" };
const SELECTION_ARGUMENT_METHODS: Readonly<Record<string, string>> = { coalesce: "default_to" };
const CALCULATION_METHODS: Readonly<Record<string, string>> = { text: "text", not: "not_" };
const CALCULATION_ARGUMENT_METHODS: Readonly<Record<string, string>> = {
  keep_if: "keep_if",
  add: "add",
  subtract: "sub",
  equals: "equals",
  and: "and_",
  or: "or_",
};
const ARRAY_METHODS: Readonly<Record<string, string>> = {
  without_nulls: "without_nulls",
  sorted: "sorted",
  distinct: "distinct",
  join: "join",
};
const SEPARATORS: Readonly<Record<string, { method: string; count: number }>> = {
  join: { method: "join", count: 1 },
  split_before: { method: "split_before", count: 1 },
  split_after: { method: "split_after", count: 1 },
  replaced: { method: "replaced", count: 2 },
};

export const SELECTION = "selection";
export const EXPRESSION = "expression";

export interface StackText {
  readonly parts: readonly string[];
  readonly mode: typeof SELECTION | typeof EXPRESSION;
}

const stack = (parts: readonly string[], mode: StackText["mode"] = SELECTION): StackText => ({ parts, mode });

/**
 * The chain as source text: one line when it fits, parenthesised inside a method-call
 * break when it does not — the way the reference project breaks a long `pick` chain.
 */
export function stackText(value: StackText, options: { readonly indent?: string; readonly asExpression?: boolean } = {}): string {
  const indent = options.indent ?? "";
  const asExpression = options.asExpression ?? true;
  const parts = [...value.parts];
  if (asExpression && value.mode === SELECTION) parts.push(".expression");
  const flat = parts.join("");
  if (indent.length + flat.length <= LINE_WIDTH) return flat;
  const inner = `${indent}${INDENT}`;
  // The reference project breaks a long chain inside parentheses, one dotted method
  // per line, exactly as `Stack.text` renders it.
  return `(\n${parts.map((part) => `${inner}${part}`).join("\n")}\n${indent})`;
}

/* -------------------------------------------------------------------------- naming */

/** `studio_backend/generate/render.py::python_name`, restated. */
export function pythonName(value: string): string {
  const cleaned = value
    .trim()
    .replace(/[^0-9A-Za-z_]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "")
    .toLowerCase();
  const safe = cleaned.length === 0 ? "item" : /^[0-9]/.test(cleaned) ? `_${cleaned}` : cleaned;
  return KEYWORDS.has(safe) ? `${safe}_` : safe;
}

const KEYWORDS: ReadonlySet<string> = new Set([
  "class", "def", "for", "from", "if", "import", "in", "is", "lambda", "None", "not", "or", "and",
  "return", "try", "while", "with", "as", "pass", "raise", "yield", "global", "nonlocal", "del",
  "assert", "break", "continue", "else", "except", "finally", "True", "False", "async", "await",
]);

/** `render.py::member_name`: `options` keeps the framework's escape hatch. */
export function memberNameOf(name: string): string {
  const attribute = pythonName(name);
  return attribute === "options" ? "options_" : attribute;
}

/** The class an expression source is written as: `sites` → `SitesTable`. */
export function sourceClass(ctx: BindingContext, source: string): string {
  const entry = selectableByName(ctx, source);
  if (entry) return entry.declaration_name;
  const table = (ctx.document.tables ?? []).find((item) => item.name === source || item.id === source);
  if (table) return table.declaration_name;
  const projection = (ctx.document.projections ?? []).find((item) => item.name === source || item.id === source);
  if (projection) return projection.declaration_name;
  return `${source
    .split(/[^A-Za-z0-9]+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join("")}Table`;
}

/* ------------------------------------------------------------------------ literals */

const TEXT_CANONICAL: readonly UnitName[] = ["date", "time", "timestamp", "uuid"];
const UNIT_SINGLETONS: Readonly<Record<string, string>> = {
  bool: "BOOL",
  int: "INT",
  float: "FLOAT",
  str: "STR",
  date: "DATE",
  time: "TIME",
  timestamp: "TIMESTAMP",
  uuid: "UUID",
};
const REPRESENTATIVES: Readonly<Record<string, string>> = { date: "Date", time: "Time", timestamp: "Timestamp", uuid: "Uuid" };

/** An authored-file string literal: double quotes, as the reference project writes them. */
export function textLiteral(value: string): string {
  return `"${value.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
}

/** The Python text for one literal value, with no type argument around it. */
export function literalValueText(value: JsonValue, type: LogicalType | null | undefined): string {
  const base = type ? unwrapNullable(type) : null;
  if (value === null) return "None";
  if (base && base.kind === "array") {
    const items = Array.isArray(value) ? value.map((item) => literalValueText(item, base.item)) : [];
    return `[${items.join(", ")}]`;
  }
  if (base && base.kind === "unit") {
    if (TEXT_CANONICAL.includes(base.name)) {
      const call = base.name === "uuid" ? REPRESENTATIVES[base.name] : `${REPRESENTATIVES[base.name]}.fromisoformat`;
      return `${call}(${textLiteral(String(value ?? ""))})`;
    }
    if (base.name === "float") return typeof value === "number" ? floatText(value) : String(value);
    if (base.name === "bool") return value ? "True" : "False";
    if (base.name === "int") return String(value);
    return textLiteral(String(value ?? ""));
  }
  if (typeof value === "string") return textLiteral(value);
  if (typeof value === "boolean") return value ? "True" : "False";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : floatText(value);
  if (Array.isArray(value)) return `[${value.map((item) => literalValueText(item, null)).join(", ")}]`;
  return String(value);
}

/** `repr(1.0)` keeps the `.0`, which is what tells Python this is a float. */
function floatText(value: number): string {
  return Number.isInteger(value) ? `${value.toFixed(1)}` : String(value);
}

/**
 * Whether `value_expression(x)` alone re-infers exactly this logical type: a null, an
 * empty or all-null array, and a JSON integer standing for a float all need the
 * explicit `logical_type=` argument (`expressions/literals.py`).
 */
export function literalIsInferable(value: JsonValue, type: LogicalType | null | undefined): boolean {
  if (type == null) return true;
  if (value === null) return false;
  const base = unwrapNullable(type);
  if (base.kind === "array") {
    const items = Array.isArray(value) ? value : [];
    if (items.length === 0) return false;
    if (items.every((item) => item === null)) return false;
    const itemNullable = items.some((item) => item === null);
    const declaredNullable = base.item.kind === "nullable";
    return itemNullable === declaredNullable;
  }
  if (base.kind === "unit" && base.name === "float") {
    return typeof value === "number" && !Number.isInteger(value);
  }
  return type.kind !== "nullable";
}

/** `value_expression(...)`, typed only where it must be. */
export function literalExpressionText(value: JsonValue, type: LogicalType | null | undefined): string {
  const text = literalValueText(value, type);
  if (literalIsInferable(value, type)) return `value_expression(${text})`;
  return `value_expression(${text}, logical_type=${typeObjectText(type)})`;
}

/** Constructor text for an explicit `logical_type=`, using the framework's names. */
export function typeObjectText(type: LogicalType | null | undefined): string {
  if (type == null) return "None";
  if (type.kind === "nullable") return `NullableType(${typeObjectText(type.value)})`;
  if (type.kind === "array") return `ArrayType(${typeObjectText(type.item)})`;
  if (type.kind === "unit") return UNIT_SINGLETONS[type.name] ?? "STR";
  return "STR";
}

/**
 * The plain-Python argument a value-taking authoring method accepts —
 * `default_to("Unnamed site")`, `add(1)` — or `null` when the value has no plain
 * spelling that survives inference, in which case the caller writes
 * `value_expression(...)`.
 */
export function scalarArgumentText(value: JsonValue, type: LogicalType | null | undefined): string | null {
  if (type == null) return null;
  const base = unwrapNullable(type);
  if (type.kind !== "nullable" && base.kind === "unit") return literalValueText(value, type);
  if (base.kind === "array" && Array.isArray(value) && value.length > 0) {
    if (base.item.kind === "unit" && base.item.name === "str" && value.every((item) => typeof item === "string")) {
      return literalValueText(value, type);
    }
  }
  return null;
}

/* ------------------------------------------------------------------------ rendering */

/**
 * Authoring Python for one expression, with the struct members it walks resolved from
 * the document so `.pick(lambda value: value.x)` names real attributes.
 */
export function renderPreview(ctx: BindingContext, expression: Expression | null | undefined): string {
  if (!expression) return "";
  return stackText(renderNode(ctx, expression), { asExpression: true });
}

function inline(ctx: BindingContext, expression: Expression): string {
  if (expression.kind === "literal") {
    const plain = scalarArgumentText(expression.value ?? null, expression.logical_type);
    if (plain !== null) return plain;
    return literalExpressionText(expression.value ?? null, expression.logical_type);
  }
  return stackText(renderNode(ctx, expression), { indent: INDENT });
}

function renderNode(ctx: BindingContext, node: Expression): StackText {
  if (node.kind === "literal") {
    return stack([literalExpressionText(node.value ?? null, node.logical_type)], EXPRESSION);
  }
  if (node.kind === "field") {
    return renderField(ctx, node.source, node.path ?? [], node.logical_type);
  }
  return renderOperation(ctx, node);
}

/** A field reference: one `.pick` per path segment after the column (`pick` folds). */
export function renderField(
  ctx: BindingContext,
  source: string,
  path: readonly string[],
  type?: LogicalType,
): StackText {
  if (path.length === 0) return stack([`${sourceClass(ctx, source)}.?`]);
  const parts = [`${sourceClass(ctx, source)}.${memberNameOf(path[0] as string)}`];
  let current: LogicalType | null = type ?? null;
  for (const segment of path.slice(1)) {
    const struct = current ? unwrapNullable(current) : null;
    if (struct && struct.kind === "struct") {
      const member = structMembers(ctx, struct).find((item) => item.name === segment);
      current = member?.logical_type ?? null;
    } else {
      current = null;
    }
    parts.push(`.pick(lambda value: value.${memberNameOf(segment)})`);
  }
  return stack(parts);
}

function renderOperation(ctx: BindingContext, node: OperationExpression): StackText {
  const arguments_ = node.arguments ?? [];
  const base = arguments_[0] ? renderNode(ctx, arguments_[0]) : stack(["?"]);
  const apply = (method: string, kind: "selection" | "calculation" | "either"): StackText => {
    if (kind === "selection") {
      if (base.mode === EXPRESSION) return stack([...base.parts, method], EXPRESSION);
      return stack([...base.parts, method], SELECTION);
    }
    if (kind === "either") return { parts: [...base.parts, method], mode: base.mode };
    const parts = [...base.parts];
    if (base.mode === SELECTION) parts.push(".expression");
    return stack([...parts, method], EXPRESSION);
  };

  if (node.operator === "struct_field") {
    const name = parameterName(node);
    return apply(`.pick(lambda value: value.${memberNameOf(name ?? "?")})`, "selection");
  }
  if (node.operator === "map_items") {
    const name = parameterName(node);
    return apply(`.map_items(lambda value: value.${memberNameOf(name ?? "?")})`, "either");
  }
  if (node.operator === "concat") return renderConcat(ctx, node);
  const selectionArgument = SELECTION_ARGUMENT_METHODS[node.operator];
  if (selectionArgument) {
    const argument = arguments_[1] ? inline(ctx, arguments_[1]) : "?";
    return apply(`.${selectionArgument}(${argument})`, "selection");
  }
  const separator = SEPARATORS[node.operator];
  if (separator) {
    const values = arguments_.slice(1).map((argument) => {
      if (argument.kind !== "literal") return "None";
      return textLiteral(String(argument.value ?? ""));
    });
    return apply(`.${separator.method}(${values.join(", ")})`, node.operator === "join" ? "either" : "calculation");
  }
  if (SELECTION_METHODS[node.operator]) return apply(`.${SELECTION_METHODS[node.operator]}()`, "selection");
  if (CALCULATION_METHODS[node.operator]) return apply(`.${CALCULATION_METHODS[node.operator]}()`, "calculation");
  if (ARRAY_METHODS[node.operator]) return apply(`.${ARRAY_METHODS[node.operator]}()`, "either");
  const calculation = CALCULATION_ARGUMENT_METHODS[node.operator];
  if (calculation) {
    const argument = arguments_[1] ? inline(ctx, arguments_[1]) : "?";
    return apply(`.${calculation}(${argument})`, "calculation");
  }
  return apply(`.${node.operator}()`, "calculation");
}

/**
 * `value.prepend(x)` records `[x, value]` and `value.append(x)` records `[value, x]`,
 * so the order *is* the rendering: a literal in argument 0 is a prefix.
 */
function renderConcat(ctx: BindingContext, node: OperationExpression): StackText {
  const [left, right] = node.arguments ?? [];
  if (left && left.kind === "literal" && right) {
    const base = renderNode(ctx, right);
    const parts = [...base.parts];
    if (base.mode === SELECTION) parts.push(".expression");
    return stack([...parts, `.prepend(${inline(ctx, left)})`], EXPRESSION);
  }
  const base = left ? renderNode(ctx, left) : stack(["?"]);
  const parts = [...base.parts];
  if (base.mode === SELECTION) parts.push(".expression");
  return stack([...parts, `.append(${right ? inline(ctx, right) : "?"})`], EXPRESSION);
}

function parameterName(node: OperationExpression): string | null {
  const value = node.parameters?.["name"];
  return typeof value === "string" && value.length > 0 ? value : null;
}

/** The struct a field path walks through, for the caller that wants to label a pick. */
export function structAt(ctx: BindingContext, type: LogicalType | null | undefined) {
  if (type == null) return null;
  const base = unwrapNullable(type);
  return base.kind === "struct" ? structByType(ctx, base) : null;
}
