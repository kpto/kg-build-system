/**
 * Which blocks may follow the current stack tip, and which heads may start one.
 *
 * The list is `index.operators` — never a frontend copy of the operator table —
 * filtered against the tip's logical type the way `ir/infer.py::available_operations`
 * filters it. Each entry answers with its reason, so a disabled block can say *why*
 * and what to add instead; that is the composer's whole value: what the framework
 * would reject cannot be clicked.
 *
 * The rules this enforces, each cited to the module that enforces it once the project
 * is generated:
 *   `expressions/nullable.py`   string / numeric / bool operations need a non-null tip —
 *                               unwrap with `where_present` or `default_to` first.
 *   `expressions/text.py`       `equals`, `split_*`, `replaced` and `concat` are
 *                               `StrExpression` only; `text()` is `IntExpression` only.
 *   `expressions/numeric.py`    `add`/`subtract` are numeric and never nullable.
 *   `expressions/boolean.py`    `not`/`and_`/`or_` need a plain non-null bool.
 *   `expressions/arrays.py`     `join` needs `Array[str]` with non-null items, so
 *                               `without_nulls` must come first; `without_nulls` is
 *                               itself refused when the items are already non-null,
 *                               because the framework records no node for it then.
 *   `expressions/selections.py` `expand` needs a list, `pick` needs a declared struct
 *                               with a member to name, `map_items` needs a list of them.
 *   `relational/planner.py`     arity — an operator is offered only with the argument
 *                               count it accepts.
 */

import type { LogicalType, NonNullableLogicalType } from "@/lib/ir";
import type { OperatorEntry } from "@/lib/types";
import { isNullable, nullable, unit, unwrapNullable } from "@/lib/ir";
import type { BindingContext } from "./context";
import { selectablePaths, selectables, structMembers } from "./context";
import { shapeOf } from "./typecheck";
import { checkHead, type HeadTarget } from "./rules";
import { GROUP_ORDER, type Block, type Operand, type OperationBlock } from "./stack";
import type { JsonValue } from "@/lib/ir";

export interface PaletteEntry {
  readonly operator: string;
  readonly label: string;
  readonly group: string;
  readonly docs: string | null;
  readonly arity: number;
  /** `concat` splits into two palette entries; both emit `concat`. */
  readonly side?: "prepend" | "append";
  readonly enabled: boolean;
  /** Why it is unavailable, or what has to be added first. */
  readonly reason: string | null;
  readonly fix: { readonly operator: string; readonly label: string } | null;
  /** Set on a row that starts a stack: the head it writes, in place of an operator. */
  readonly head?: HeadEntry;
}

/** The two heads the stack model has, as a palette choice. */
export type HeadEntry =
  | { readonly kind: "source"; readonly source: string; readonly path: readonly string[] }
  | { readonly kind: "literal"; readonly value: JsonValue; readonly type: LogicalType };

interface Guard {
  readonly shape: string;
  readonly units?: readonly string[];
  readonly items?: string;
  readonly members?: boolean;
}

const requiresOf = (entry: OperatorEntry): Guard => {
  const requires = (entry.requires ?? {}) as Partial<Guard>;
  const shape = requires.shape ?? "any";
  const guard: Guard = {
    shape,
    units: requires.units,
    // `without_nulls` records no IR node when the items are already non-null
    // (`expressions/arrays.py`), so it is never offered then. The catalogue declares
    // this as `items: "nullable"`; an index entry that omits it still gets the rule.
    items: requires.items ?? (entry.operator === "without_nulls" ? "nullable" : undefined),
    // `pick` and `map_items` need a declared member to name, and the composer can only
    // list members the document declares (`ir/infer.py::_requires_member_list`).
    members: requires.members ?? (entry.operator === "struct_field" || entry.operator === "map_items"),
  };
  // `expressions/numeric.py` gives `add`/`subtract` to both numeric families; an index
  // entry narrowed to one unit (`unit:float`) must not hide the other. `text()` keeps
  // its int-only guard — Float has no `text()` (`AUTHORING_IR_CONTRACT.md`).
  if (NUMERIC_OPERATORS.has(entry.operator) && (guard.shape === "unit:int" || guard.shape === "unit:float")) {
    return { ...guard, shape: "non_nullable", units: ["int", "float"] };
  }
  return guard;
};

const NUMERIC_OPERATORS: ReadonlySet<string> = new Set(["add", "subtract"]);


/** `ir/infer.py::matches_shape`, over the tip type. */
export function matchesShape(value: LogicalType | null, shape: string): boolean {
  if (value == null) return false;
  const base = unwrapNullable(value);
  switch (shape) {
    case "any":
      return true;
    case "nullable":
      return isNullable(value);
    case "non_nullable":
      return !isNullable(value);
    case "array":
      return base.kind === "array";
    case "array_of_struct":
      return base.kind === "array" && unwrapNullable(base.item).kind === "struct";
    case "array_of_non_null_str":
      return base.kind === "array" && base.item.kind === "unit" && base.item.name === "str";
    case "struct":
      return base.kind === "struct";
    default:
      if (shape.startsWith("unit:")) {
        const name = shape.slice("unit:".length);
        return !isNullable(value) && base.kind === "unit" && base.name === name;
      }
      return false;
  }
}

/** Every guard the entry declares, checked one at a time so the reason is specific. */
function refusal(
  ctx: BindingContext,
  entry: OperatorEntry,
  tip: LogicalType | null,
  side?: "prepend" | "append",
): { reason: string; fix: PaletteEntry["fix"] } | null {
  const guard = requiresOf(entry);
  const shown = tip == null ? "nothing yet — pick a source first" : spell(tip);

  if (tip == null) return { reason: "a stack starts by picking a table or projection", fix: null };

  if (guard.items === "nullable") {
    const base = unwrapNullable(tip);
    if (base.kind !== "array") {
      return { reason: `works on a list; this tip is ${shown}`, fix: null };
    }
    if (!isNullable(base.item)) {
      return {
        reason: `every item already has a value, so there is nothing to drop — the framework records no block for it`,
        fix: null,
      };
    }
  }

  if (guard.members) {
    const struct = structUnder(tip);
    if (!struct) return { reason: `needs a nested record; this tip is ${shown}`, fix: null };
    if (structMembers(ctx, struct).length === 0) {
      return { reason: `${struct.qualname} declares no members to read`, fix: null };
    }
  }

  // `array_of_non_null_str` needs an explanation the shape vocabulary cannot carry:
  // over a list of nullable text it is the item nullability that is wrong, not the list.
  const joinGuard = guard.shape === "array_of_non_null_str" && !matchesShape(tip, guard.shape);
  if (joinGuard) {
    const base = unwrapNullable(tip);
    if (base.kind === "array" && isNullable(base.item)) {
      return {
        reason: `its items might be missing — add ${DROP_LABEL} first`,
        fix: { operator: "without_nulls", label: DROP_LABEL },
      };
    }
  }

  if (guard.shape !== "any" && !matchesShape(tip, guard.shape)) {
    return { reason: shapeRefusal(entry, guard, tip, shown, side), fix: fixFor(guard.shape, tip) };
  }

  if (guard.units && guard.units.length > 0) {
    const base = unwrapNullable(tip);
    const name = base.kind === "unit" ? base.name : "";
    if (!guard.units.includes(name)) {
      // Only suggest the unwrap when unwrapping would actually reach one of the units.
      const helps = isNullable(tip) && base.kind === "unit" && guard.units.includes(name);
      return {
        reason: `works on ${guard.units.join(" or ")}; this tip is ${shown}`,
        fix: helps ? UNWRAP_FIX : null,
      };
    }
  }

  return null;
}

function shapeRefusal(
  entry: OperatorEntry,
  guard: Guard,
  tip: LogicalType,
  shown: string,
  side?: "prepend" | "append",
): string {
  const name = entry.label.toLowerCase();
  const verb = guard.shape.startsWith("unit:") ? guard.shape.slice("unit:".length) : guard.shape;
  void entry;
  if (guard.shape === "nullable") {
    return `${name} only applies to a value that might be missing, and ${shown} never is`;
  }
  if (guard.shape === "non_nullable") {
    return `${name} needs a value that is never missing; this tip is ${shown}`;
  }
  // Only the unit families are blocked by nullability: `array`/`struct` shapes see
  // through a nullable in the backend, so a refusal there is about the kind, not the null.
  if (isNullable(tip) && guard.shape.startsWith("unit:") && matchesShape(unwrapNullable(tip), guard.shape)) {
    return `${name} needs a non-null ${verb} — add ${UNWRAP_HINTS} first (this tip is ${shown})`;
  }
  if (guard.shape === "array_of_struct") {
    return `${name} reads one member of every record in a list; this tip is ${shown}`;
  }
  if (guard.shape === "array_of_non_null_str") {
    const base = unwrapNullable(tip);
    if (base.kind === "array") {
      return `${name} joins a list of text that is always there, and this list holds ${spell(base.item)}`;
    }
    return `${side === "prepend" ? "Put in front" : name} needs a list of non-null text; this tip is ${shown}`;
  }
  if (guard.shape === "array") return `${name} works on a list; this tip is ${shown}`;
  if (guard.shape === "struct") return `${name} reads a member of a nested record; this tip is ${shown}`;
  return `${name} needs ${verb}; this tip is ${shown}`;
}

const DROP_LABEL = "Drop missing items";

const UNWRAP_HINTS = "Keep rows where present (drops the empty rows) or Default to a value (keeps them)";

/** The one block that turns a nullable value into the non-null one a slot or key wants. */
const UNWRAP_FIX: NonNullable<PaletteEntry["fix"]> = { operator: "where_present", label: "Keep rows where present" };

function fixFor(shape: string, tip: LogicalType | null = null): PaletteEntry["fix"] {
  if (shape === "array_of_non_null_str") {
    // Dropping item nulls only helps when the tip really is a list.
    const base = tip == null ? null : unwrapNullable(tip);
    if (base?.kind !== "array" || !isNullable(base.item)) return null;
    return { operator: "without_nulls", label: "Drop missing items" };
  }
  if (shape.startsWith("unit:") || shape === "non_nullable" || shape === "struct") {
    // Offer the unwrap only when nullability really is the only thing in the way.
    if (tip == null || !isNullable(tip) || !matchesShape(unwrapNullable(tip), shape)) return null;
    return UNWRAP_FIX;
  }
  return null;
}

function structUnder(tip: LogicalType | null) {
  if (tip == null) return null;
  const base = unwrapNullable(tip);
  if (base.kind === "struct") return base;
  if (base.kind === "array") {
    const item = unwrapNullable(base.item);
    return item.kind === "struct" ? item : null;
  }
  return null;
}

/** The tip's type in words, with the nullability said out loud. */
export function spell(value: LogicalType): string {
  const base = unwrapNullable(value);
  const core =
    base.kind === "unit"
      ? base.name
      : base.kind === "array"
        ? `Array[${spell(base.item)}]`
        : base.kind === "struct"
          ? `Struct{${base.qualname}}`
          : "unknown";
  return isNullable(value) ? `${core} | None` : core;
}

/**
 * The palette for one tip: every catalogue entry, each either clickable or explained.
 * `concat` arrives as one entry and leaves as two — the two authoring methods the
 * framework records with the same operator.
 */
export function paletteFor(ctx: BindingContext, operators: readonly OperatorEntry[], tip: LogicalType | null): PaletteEntry[] {
  const entries: PaletteEntry[] = [];
  for (const entry of operators) {
    const side = entry.operator === "concat" ? (["prepend", "append"] as const) : ([undefined] as const);
    for (const which of side) {
      const blocked = refusal(ctx, entry, tip, which);
      entries.push({
        operator: entry.operator,
        label: which === "prepend" ? "Put text in front" : which === "append" ? "Put text behind" : entry.label,
        group: groupOf(entry),
        docs: entry.docs ?? null,
        arity: entry.arity ?? 1,
        ...(which ? { side: which } : {}),
        enabled: blocked == null,
        reason: blocked?.reason ?? null,
        fix: blocked?.fix ?? null,
      });
    }
  }
  return entries.sort(
    (a, b) => GROUP_ORDER.indexOf(a.group) - GROUP_ORDER.indexOf(b.group) || Number(b.enabled) - Number(a.enabled),
  );
}

export function groupOf(entry: OperatorEntry): string {
  const raw = (entry.group ?? "calculate").toLowerCase();
  if (raw === "navigation") return "navigate";
  if (raw === "calculation") return "calculate";
  return raw;
}

/* ---------------------------------------------------------------------------- heads */

/** A key has no declared type to write into, and the framework's keys are text. */
const KEY_VALUE_TYPE: LogicalType = unit("str");

/**
 * The heads that can start a stack: every field the index flattens, and a written value.
 *
 * With no tip there is no operator to offer — `refusal` turns the whole catalogue down —
 * so this is the other half of the palette and the only way into an empty stack. Each
 * head is judged where the finished stack is judged (`rules.checkHead`): a column that
 * fills its slot only once the null is gone is offered with `where_present` named as the
 * block to add, and one that can never fill it is refused in the slot's own words. Heads
 * are grouped by the source they read, in the order the index publishes them.
 */
export function headsFor(ctx: BindingContext, target: HeadTarget): PaletteEntry[] {
  const heads: PaletteEntry[] = [];
  for (const source of selectables(ctx)) {
    for (const field of selectablePaths(ctx, source)) {
      const check = checkHead(field.logical_type, target);
      heads.push({
        operator: "field",
        label: field.path.join("."),
        group: source.group ? `${source.group}.${source.name}` : source.name,
        docs: check.unwrap ? `${spell(field.logical_type)} · needs ${UNWRAP_FIX.label.toLowerCase()}` : spell(field.logical_type),
        arity: 0,
        enabled: check.ok,
        reason: check.message,
        fix: check.unwrap ? UNWRAP_FIX : null,
        head: { kind: "source", source: source.name, path: [...field.path] },
      });
    }
  }
  // A written value is the other head the model has; it takes the slot's own type with
  // the null left off, which `_compatible` accepts for a nullable slot as well.
  const valueType = unwrapNullable(target.slot?.logical_type ?? KEY_VALUE_TYPE);
  if (writesAsLiteral(valueType)) {
    const check = checkHead(valueType, target);
    heads.push({
      operator: "literal",
      label: "Write a value",
      group: "written value",
      docs: check.ok ? spell(valueType) : null,
      arity: 0,
      enabled: check.ok,
      reason: check.message,
      fix: null,
      head: { kind: "literal", value: null, type: valueType },
    });
  }
  return heads;
}

/** `expressions/literals.py` will not build a literal that holds a record. */
function writesAsLiteral(type: NonNullableLogicalType): boolean {
  if (type.kind === "unit") return true;
  return type.kind === "array" && unwrapNullable(type.item).kind !== "struct";
}

/* ------------------------------------------------------------------- block factory */

/**
 * The block to insert for a palette choice, with the operand values a valid stack
 * needs filled in so the stack stays type-correct the moment it is added.
 *
 * The two defaults that must not be left blank are the ones the framework insists on:
 * `coalesce` needs a fallback of the *unwrapped* type, and any text/bool/number
 * operation needs its operand to match the tip exactly.
 */
export function blockFor(
  entry: PaletteEntry,
  tip: LogicalType | null,
  options: { readonly member?: string; readonly text?: string; readonly number?: number; readonly bool?: boolean } = {},
): Block {
  // A head row writes a head: the choice itself is the whole block, with no operands.
  if (entry.head) {
    const id = `head-${entry.head.kind}-${Math.random().toString(36).slice(2, 8)}`;
    return entry.head.kind === "source"
      ? { id, role: "head", kind: "source", source: entry.head.source, path: [...entry.head.path] }
      : { id, role: "head", kind: "literal", value: entry.head.value, type: entry.head.type };
  }
  const operands: Operand[] = [];
  const parameters: Record<string, JsonValue> = {};
  const unwrapped: NonNullableLogicalType = tip ? unwrapNullable(tip) : { kind: "unit", name: "str" };
  const literal = (slot: number, value: JsonValue, type: LogicalType): Operand => ({ slot, kind: "literal", value, type });
  const str: LogicalType = { kind: "unit", name: "str" };
  const bool: LogicalType = { kind: "unit", name: "bool" };

  switch (entry.operator) {
    case "coalesce":
      operands.push(literal(1, options.text ?? defaultFallback(unwrapped), unwrapped));
      break;
    case "concat":
      operands.push(literal(entry.side === "prepend" ? 0 : 1, options.text ?? "", str));
      break;
    case "join":
    case "split_before":
    case "split_after":
      operands.push(literal(1, options.text ?? ", ", str));
      break;
    case "replaced":
      operands.push(literal(1, options.text ?? "", str), literal(2, "", str));
      break;
    case "equals":
    case "and":
    case "or":
      operands.push(literal(1, entry.operator === "equals" ? (options.text ?? "") : true, entry.operator === "equals" ? str : bool));
      break;
    case "add":
    case "subtract":
      operands.push(literal(1, options.number ?? 0, tip ?? { kind: "unit", name: "int" }));
      break;
    case "keep_if":
      operands.push({ slot: 1, kind: "literal", value: true, type: bool });
      break;
    case "struct_field":
    case "map_items":
      if (options.member) parameters["name"] = options.member;
      break;
    default:
      break;
  }
  const block: OperationBlock = {
    id: `step-${entry.operator}-${entry.side ?? ""}-${Math.random().toString(36).slice(2, 8)}`,
    role: "step",
    kind: "operation",
    operator: entry.operator,
    ...(entry.side ? { side: entry.side } : {}),
    parameters,
    operands,
  };
  return block;
}

/** A fallback the author can see and change: never a value the type cannot hold. */
export function defaultFallback(type: NonNullableLogicalType): JsonValue {
  if (type.kind === "array") return [];
  if (type.kind === "struct") return null;
  switch (type.name) {
    case "bool":
      return false;
    case "int":
      return 0;
    case "float":
      return 0;
    case "str":
      return "";
    default:
      return null;
  }
}

/** Does the tip have to be made non-null before this entry can be used? */
export function needsUnwrap(entry: PaletteEntry, tip: LogicalType | null): boolean {
  return !entry.enabled && entry.fix?.operator === "where_present" && tip != null && isNullable(tip);
}

export { nullable };
