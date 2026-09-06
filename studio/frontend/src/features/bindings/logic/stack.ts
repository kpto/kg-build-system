/**
 * The stack model: a vertical list of blocks ⇄ one IR expression.
 *
 * A stack is always `head` (a field reference or a literal) followed by operations
 * applied to the value its predecessor produced, which is exactly what
 * DESIGN.md §5 draws. Converting to and from the IR tree is where the contract's
 * two codegen rules become code:
 *
 *   * `pick` **folds** — adding a member above a plain field reference extends that
 *     reference's `path` instead of emitting a `struct_field` node; a `struct_field`
 *     node only appears above an operation (`AUTHORING_IR_CONTRACT.md`).
 *   * `prepend` and `append` are both `concat` — the *argument order* records which
 *     method was written, so a block carries a `side` and the fold reads it back.
 *
 * Blocks never store a `logical_type`: the seam is derived (`typecheck.ts`), and the
 * backend recomputes every type on save.
 */

import type {
  Expression,
  FieldExpression,
  JsonObject,
  JsonValue,
  LogicalType,
  NonNullableLogicalType,
  OperationExpression,
} from "@/lib/ir";
import type { OperatorEntry } from "@/lib/types";
import type { BindingContext } from "./context";
import { structMembers } from "./context";
import { inferExpression, memberName } from "./typecheck";

export type Operand =
  | { readonly slot: number; readonly kind: "literal"; readonly value: JsonValue; readonly type: LogicalType }
  | { readonly slot: number; readonly kind: "field"; readonly source: string; readonly path: readonly string[] }
  | { readonly slot: number; readonly kind: "passthrough"; readonly expression: Expression };

export interface SourceBlock {
  readonly id: string;
  readonly role: "head";
  readonly kind: "source";
  readonly source: string;
  readonly path: readonly string[];
}

export interface LiteralBlock {
  readonly id: string;
  readonly role: "head";
  readonly kind: "literal";
  readonly value: JsonValue;
  readonly type: LogicalType;
}

export interface OperationBlock {
  readonly id: string;
  readonly role: "step";
  readonly kind: "operation";
  readonly operator: string;
  /** `concat` only: which side the written value lands on. */
  readonly side?: "prepend" | "append";
  readonly parameters: JsonObject;
  readonly operands: readonly Operand[];
}

export type Block = SourceBlock | LiteralBlock | OperationBlock;

export interface Seams {
  /** One entry per block: the logical type that block hands to the next one. */
  readonly types: readonly (LogicalType | null)[];
  /** The first block whose operation the framework would reject, if any. */
  readonly broken: { readonly index: number; readonly message: string } | null;
}

export const ARITIES: Readonly<Record<string, number>> = {
  expand: 1,
  keep_if: 2,
  coalesce: 2,
  struct_field: 1,
  map_items: 1,
  without_nulls: 1,
  sorted: 1,
  distinct: 1,
  join: 2,
  add: 2,
  subtract: 2,
  text: 1,
  concat: 2,
  equals: 2,
  split_before: 2,
  split_after: 2,
  replaced: 3,
  not: 1,
  and: 2,
  or: 2,
  where_present: 1,
};

export const arityOf = (operator: string, entry?: OperatorEntry): number =>
  entry?.arity ?? ARITIES[operator] ?? 1;

/**
 * Block ids are stable across a reorder (the parse numbers them before the move), so
 * they can key the drag list.
 */
function parseId(expression: Expression, index: number): string {
  if (expression.kind === "literal") return `head-${expression.kind}-${index}`;
  if (expression.kind === "field") return `head-${expression.source}-${(expression.path ?? []).join(".")}-${index}`;
  const subject = (expression.arguments ?? [])[0];
  return subject && subject.kind === "operation" ? parseId(subject, index + 1) : `head-${expression.kind}-${index}`;
}

/** `concat` keeps the chain on argument 1 when the value was written in front. */
export function subjectIndex(block: OperationBlock): number {
  return block.operator === "concat" && block.side === "prepend" ? 1 : 0;
}

/* ------------------------------------------------------------------------- parse */

function isPlainField(expression: Expression | undefined): expression is FieldExpression {
  return !!expression && expression.kind === "field";
}

/**
 * An IR tree down to a stack. The walk follows the *subject* of each operation — the
 * argument the stack flows through — which for a written `prepend` is argument 1.
 * Anything else the author wrote as an operand is kept beside the block.
 */
export function blocksFromExpression(expression: Expression | null | undefined): Block[] {
  const blocks: Block[] = [];
  const rootId = expression ? parseId(expression, 0) : "head";
  let steps = 0;
  const walk = (node: Expression): void => {
    if (node.kind === "literal") {
      blocks.push({
        id: `${rootId}-literal`,
        role: "head",
        kind: "literal",
        value: node.value ?? null,
        type: node.logical_type ?? { kind: "unit", name: "str" },
      });
      return;
    }
    if (node.kind === "field") {
      blocks.push({
        id: `${rootId}-source`,
        role: "head",
        kind: "source",
        source: node.source,
        path: node.path ?? [],
      });
      return;
    }
    const arguments_ = node.arguments ?? [];
    // `value.prepend(x)` records `[x, value]` and `value.append(x)` records
    // `[value, x]`, so the order alone says which method was written: a value in
    // argument 0 is a prefix, anything else is an append. That is the same rule
    // `generate/expressions.py::_concat` reads back.
    const side: "prepend" | "append" | undefined =
      node.operator === "concat"
        ? arguments_[0]?.kind === "literal"
          ? "prepend"
          : "append"
        : undefined;
    const subjectIndexValue = side === "prepend" ? 1 : 0;
    const subject = arguments_[subjectIndexValue];
    // Where the chain for this block starts, so a fold can tell that the value under
    // it is still a plain field reference and not an operation.
    const chainStart = blocks.length;
    if (subject) walk(subject);

    // A member read straight off a field reference was folded into its path by the
    // framework, so it is not a block: the head already carries it. This is true
    // however many picks deep the chain is, because each one folds into the same node.
    if (node.operator === "struct_field" && blocks.length === chainStart + 1) {
      const head = blocks[chainStart];
      const name = memberName(node);
      if (head && head.kind === "source" && name) {
        blocks[chainStart] = { ...head, path: [...head.path, name] };
        return;
      }
    }

    steps += 1;
    const operands: Operand[] = [];
    arguments_.forEach((argument, index) => {
      if (index === subjectIndexValue) return;
      operands.push(operandFrom(index, argument));
    });
    const parameters: JsonObject = {};
    const name = memberName(node);
    if (name && (node.operator === "struct_field" || node.operator === "map_items")) {
      parameters["name"] = name;
    }
    blocks.push({
      id: `${rootId}-step-${node.operator}-${steps}`,
      role: "step",
      kind: "operation",
      operator: node.operator,
      ...(side ? { side } : {}),
      parameters,
      operands,
    });
  };
  if (expression) walk(expression);
  return blocks;
}

function operandFrom(slot: number, expression: Expression): Operand {
  if (expression.kind === "literal") {
    return {
      slot,
      kind: "literal",
      value: expression.value ?? null,
      type: expression.logical_type ?? { kind: "unit", name: "str" },
    };
  }
  if (expression.kind === "field") {
    return { slot, kind: "field", source: expression.source, path: expression.path ?? [] };
  }
  return { slot, kind: "passthrough", expression };
}

/* ------------------------------------------------------------------------ compose */

export function headExpression(block: Block | undefined): Expression | null {
  if (!block) return null;
  if (block.kind === "source") {
    // `logical_type` is written for the payload to satisfy the IR mirror; the backend
    // derives it (`ir.infer`) and overwrites whatever arrives.
    return { kind: "field", source: block.source, path: [...block.path], logical_type: null as unknown as LogicalType };
  }
  if (block.kind === "literal") {
    return { kind: "literal", value: block.value, logical_type: block.type };
  }
  return null;
}

function operandExpression(ctx: BindingContext, operand: Operand): Expression {
  if (operand.kind === "literal") {
    return { kind: "literal", value: operand.value, logical_type: operand.type };
  }
  if (operand.kind === "field") {
    const field: Expression = {
      kind: "field",
      source: operand.source,
      path: [...operand.path],
      logical_type: null as unknown as LogicalType,
    };
    // The mirror requires the key, so write what `ir.infer` would derive for it; the
    // backend recomputes and overwrites it on save either way.
    const type = inferExpression(ctx, field);
    return type.type == null ? field : { ...field, logical_type: type.type };
  }
  return operand.expression;
}

/**
 * The stack back to one IR expression, with every `logical_type` filled in from the
 * local derivation. A stack whose head has no path, or whose operation the framework
 * would reject, yields `null`: the composer keeps the previous expression rather than
 * writing a tree the generator cannot render.
 */
export function expressionFromBlocks(
  ctx: BindingContext,
  blocks: readonly Block[],
): { readonly expression: Expression | null; readonly error: string | null } {
  const seams = seamsFor(ctx, blocks);
  if (seams.broken) return { expression: null, error: seams.broken.message };
  let node: Expression | null = null;
  for (const block of blocks) {
    if (block.role === "head") {
      const head = headExpression(block);
      if (!head) return { expression: null, error: "the stack has no source yet" };
      if (head.kind === "field") {
        if (head.path.length === 0) return { expression: null, error: "pick a field to read" };
        const type = inferExpression(ctx, head);
        if (type.error || type.type == null) return { expression: null, error: type.error ?? "unknown type" };
        node = { ...head, logical_type: type.type };
      } else {
        node = head;
      }
      continue;
    }
    if (node == null) return { expression: null, error: "the stack has no source yet" };
    const arity = arityOf(block.operator);
    const arguments_: Expression[] = new Array<Expression>(arity);
    arguments_[subjectIndex(block)] = node;
    for (const operand of block.operands) {
      if (operand.slot >= 0 && operand.slot < arity) arguments_[operand.slot] = operandExpression(ctx, operand);
    }
    for (let slot = 0; slot < arity; slot += 1) {
      if (!arguments_[slot]) {
        return { expression: null, error: `this block is missing argument ${slot}` };
      }
    }
    const type = seams.types[blocks.indexOf(block)] ?? null;
    if (type == null) return { expression: null, error: "the resulting type cannot be derived" };
    const operation: OperationExpression = {
      kind: "operation",
      operator: block.operator,
      arguments: arguments_,
      parameters: { ...block.parameters },
      logical_type: type,
    };
    node = operation;
  }
  return { expression: node, error: null };
}

/* ---------------------------------------------------------------------- seams */

/** The type each block hands down the stack, plus the first block that breaks. */
export function seamsFor(ctx: BindingContext, blocks: readonly Block[]): Seams {
  const types: (LogicalType | null)[] = [];
  let broken: Seams["broken"] = null;
  let node: Expression | null = null;
  blocks.forEach((block, index) => {
    if (block.role === "head") {
      const head = headExpression(block);
      const result = head ? inferExpression(ctx, head) : { type: null, error: "no source yet" };
      types.push(result.type);
      if (result.error && !broken) broken = { index, message: result.error };
      node = head;
      return;
    }
    const arity = arityOf(block.operator);
    const arguments_: Expression[] = [];
    for (let slot = 0; slot < arity; slot += 1) {
      if (slot === subjectIndex(block)) {
        if (node) arguments_.push(node);
        continue;
      }
      const operand = block.operands.find((item) => item.slot === slot);
      if (operand) arguments_.push(operandExpression(ctx, operand));
    }
    if (arguments_.length !== arity) {
      types.push(null);
      if (!broken) broken = { index, message: `this block needs ${arity} argument(s)` };
      return;
    }
    const operation: OperationExpression = {
      kind: "operation",
      operator: block.operator,
      arguments: arguments_,
      parameters: { ...block.parameters },
      logical_type: null as unknown as LogicalType,
    };
    const result = inferExpression(ctx, operation);
    types.push(result.type);
    if (result.error && !broken) broken = { index, message: result.error };
    node = operation;
  });
  return { types, broken };
}

export const tipType = (ctx: BindingContext, blocks: readonly Block[]): LogicalType | null => {
  const seams = seamsFor(ctx, blocks);
  return seams.types[seams.types.length - 1] ?? null;
};

/* -------------------------------------------------------------------- block edits */

/** The struct a member-reading block reads from, given the value above it. */
export function membersFor(
  ctx: BindingContext,
  operator: string,
  valueAbove: LogicalType | null,
): readonly { name: string; label: string }[] {
  if (valueAbove == null) return [];
  const base = unwrap(valueAbove);
  const struct = base.kind === "struct" ? base : base.kind === "array" ? unwrap(base.item) : null;
  if (!struct || struct.kind !== "struct") return [];
  void operator;
  return structMembers(ctx, struct).map((member) => ({
    name: member.name,
    label: member.name,
  }));
}

const unwrap = (value: LogicalType): LogicalType & { kind: string } => {
  if (value.kind === "nullable") return value.value as LogicalType & { kind: string };
  return value as LogicalType & { kind: string };
};

export const nonNull = (value: LogicalType): NonNullableLogicalType =>
  value.kind === "nullable" ? value.value : value;

/**
 * Move a block to a new position, refusing orders the framework would reject.
 *
 * The stack is linear, so a move is legal exactly when every block still receives the
 * value its operation needs: the recomputed seams must stay unbroken and the head must
 * stay the head. That single rule is also what stops an effect block sliding below the
 * block that produces its input.
 */
export function moveBlocks(
  ctx: BindingContext,
  blocks: readonly Block[],
  from: number,
  to: number,
): { readonly blocks: readonly Block[]; readonly reason: string | null } {
  if (from === to) return { blocks, reason: null };
  if (from < 0 || to < 0 || from >= blocks.length || to >= blocks.length) {
    return { blocks, reason: "there is nothing at that position" };
  }
  if (blocks[from]?.role === "head") return { blocks, reason: "the source block stays at the top of the stack" };
  if (to === 0) return { blocks, reason: "every block sits below the source it reads" };
  const next = [...blocks];
  const [moved] = next.splice(from, 1);
  if (!moved) return { blocks, reason: "there is nothing to move" };
  next.splice(to, 0, moved);
  const seams = seamsFor(ctx, next);
  if (seams.broken) {
    const blocker = next[seams.broken.index];
    return {
      blocks,
      reason: `${labelFor(moved)} cannot move below ${labelFor(blocker)}: ${seams.broken.message}`,
    };
  }
  return { blocks: next, reason: null };
}

export function labelFor(block: Block | undefined): string {
  if (!block) return "that block";
  if (block.kind === "source") return `${block.source}${block.path.length ? `.${block.path.join(".")}` : ""}`;
  if (block.kind === "literal") return "the written value";
  return block.side === "prepend" ? "Put in front" : (OPERATOR_WORDS[block.operator] ?? block.operator);
}

const OPERATOR_WORDS: Readonly<Record<string, string>> = {
  struct_field: "Take one member",
  expand: "Make one row per item",
  map_items: "Take one member from every item",
  without_nulls: "Drop missing items",
  where_present: "Keep rows where present",
  coalesce: "Use a value when missing",
  keep_if: "Keep rows where a test holds",
  sorted: "Sort the items",
  distinct: "Keep each item once",
  join: "Join the items into one text",
  concat: "Put text behind",
  split_before: "Keep the text before a marker",
  split_after: "Keep the text after a marker",
  replaced: "Replace one piece of text",
  text: "Write it as text",
  add: "Add to it",
  subtract: "Subtract from it",
  equals: "Is it exactly this text?",
  not: "Flip true and false",
  and: "Both must hold",
  or: "One or the other must hold",
};

/**
 * Delete a block and report what the deletion takes with it.
 *
 * Removing a block re-seats the stack, and any block below that no longer receives
 * what it needs goes too — the UI must say so before the click, not after.
 */
export function removeBlock(
  ctx: BindingContext,
  blocks: readonly Block[],
  index: number,
): { readonly blocks: readonly Block[]; readonly removed: readonly Block[] } {
  const target = blocks[index];
  if (!target || target.role === "head") return { blocks, removed: [] };
  let next = blocks.filter((_block, position) => position !== index);
  const removed: Block[] = [target];
  // Cascade: keep dropping the first block that no longer type-checks.
  for (let guard = 0; guard < next.length + 1; guard += 1) {
    const seams = seamsFor(ctx, next);
    if (!seams.broken) break;
    const drop = seams.broken.index;
    if (drop === 0) break;
    const dropped = next[drop];
    if (!dropped || dropped.role === "head") break;
    removed.push(dropped);
    next = next.filter((_block, position) => position !== drop);
  }
  return { blocks: next, removed };
}

/**
 * Put a new head under an existing stack and report the blocks that no longer fit.
 *
 * Re-pointing a stack at another column is the same problem as deleting a block: the
 * blocks below receive a different value, and any that the framework would reject has
 * to go with a word about it. The head itself is never dropped.
 */
export function reseatHead(
  ctx: BindingContext,
  blocks: readonly Block[],
  head: Block,
): { readonly blocks: readonly Block[]; readonly dropped: readonly Block[] } {
  let next: Block[] = [head, ...blocks.slice(1)];
  const dropped: Block[] = [];
  for (let guard = 0; guard < next.length + 1; guard += 1) {
    const seams = seamsFor(ctx, next);
    if (!seams.broken) break;
    const drop = Math.max(1, seams.broken.index);
    const victim = next[drop];
    if (!victim || victim.role === "head") break;
    dropped.push(victim);
    next = next.filter((_block, position) => position !== drop);
  }
  return { blocks: next, dropped };
}

/** The operator catalogue's group, defaulted for operators the index omits. */
export const GROUP_ORDER: readonly string[] = [
  "navigate",
  "effect",
  "calculate",
  "aggregate",
  "compare",
  "logic",
];

export function groupOf(entry: OperatorEntry): string {
  const raw = (entry.group ?? "calculate").toLowerCase();
  if (raw === "navigation") return "navigate";
  if (raw === "calculation") return "calculate";
  return raw;
}
