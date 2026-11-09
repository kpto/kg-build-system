import type { Expression, LogicalType, Ref, WorkflowStep } from "./types";

/** Stable string key for a reference tuple. Exported for tests and indexing. */
export function refKey(parts: readonly string[] | undefined | null): string {
  return parts ? parts.join("\u0000") : "";
}

/** Human-readable reference, e.g. `data.field:defect.title`. */
export function displayRef(parts: readonly string[] | undefined | null): string {
  return parts ? parts.join(".") : "";
}

export function isExpression(value: unknown): value is Expression {
  if (!value || typeof value !== "object") return false;
  const kind = (value as { kind?: unknown }).kind;
  return kind === "field" || kind === "literal" || kind === "operation";
}

/** Depth-first walk over an expression tree. */
export function walkExpression(
  expression: Expression | undefined,
  visit: (expression: Expression) => void,
): void {
  if (!expression) return;
  visit(expression);
  if (expression.kind === "operation") {
    for (const argument of expression.arguments ?? []) {
      walkExpression(argument, visit);
    }
  }
}

/** All field refs in an expression, in traversal order, deduplicated. */
export function collectFieldRefs(expression: Expression | undefined): Ref[] {
  const result: Ref[] = [];
  const seen = new Set<string>();
  walkExpression(expression, (node) => {
    if (node.kind !== "field") return;
    const key = refKey(node.field);
    if (!key || seen.has(key)) return;
    seen.add(key);
    result.push([...node.field]);
  });
  return result;
}

/** The final segment of an operator tuple, e.g. `coalesce`. */
export function operationName(expression: Expression | undefined): string | undefined {
  if (!expression || expression.kind !== "operation") return undefined;
  return expression.operator.at(-1);
}

/** Short expression rendering used by the explorer and inspector. */
export function expressionPreview(expression: Expression | undefined, depth = 0): string {
  if (!expression) return "—";
  switch (expression.kind) {
    case "field": {
      const path = expression.path?.length ? `.${expression.path.join(".")}` : "";
      return `${expression.field.at(-1) ?? displayRef(expression.field)}${path}`;
    }
    case "literal":
      return JSON.stringify(expression.value);
    case "operation": {
      const name = operationName(expression) ?? "operation";
      if (depth > 5) return `${name}(…)`;
      const args = (expression.arguments ?? [])
        .map((argument) => expressionPreview(argument, depth + 1))
        .join(", ");
      return `${name}(${args})`;
    }
  }
}

/** Expression tree as indented lines for the inspector. */
export function expressionTree(expression: Expression | undefined): string[] {
  const lines: string[] = [];
  const visit = (node: Expression, depth: number) => {
    const indent = "  ".repeat(depth);
    if (node.kind === "operation") {
      lines.push(`${indent}${operationName(node) ?? "operation"}`);
      for (const argument of node.arguments ?? []) visit(argument, depth + 1);
      return;
    }
    lines.push(`${indent}${expressionPreview(node)}`);
  };
  if (expression) visit(expression, 0);
  return lines;
}

/** The SQL preview a step carries, if it has one. */
export function stepSqlPreview(step: WorkflowStep | undefined): string | undefined {
  const sql = step?.instruction.payload?.sql;
  return typeof sql === "string" ? sql : undefined;
}

/**
 * Render a canonical logical type.
 *
 * `Nullable[T]` is the one spelling for an optional value: `T | None` is the
 * same type and is not emitted a second time. Unknown kinds fall back to their
 * value or name so a new language type remains readable.
 */
export function logicalTypeName(type: LogicalType | undefined): string {
  if (!type) return "unknown";
  switch (type.kind) {
    case "unit":
      return type.name ?? "unit";
    case "nullable":
      return `Nullable[${logicalTypeName(type.value)}]`;
    case "array":
      return `${logicalTypeName(type.item)}[]`;
    default: {
      if (type.value) return `${type.kind}[${logicalTypeName(type.value)}]`;
      if (type.item) return `${type.kind}<${logicalTypeName(type.item)}>`;
      return type.name ?? type.kind;
    }
  }
}

/** The type with nullable wrappers removed, for compatibility checks. */
export function logicalTypeBase(type: LogicalType | undefined): string {
  if (!type) return "unknown";
  if (type.kind === "nullable") return logicalTypeBase(type.value);
  return logicalTypeName(type);
}

/**
 * Presence of a value: the top-level nullable wrapper, never a nested field.
 *
 * A source access and a binding expression may be nullable; a declared
 * topology property is present. The chain records both rather than collapsing
 * them into one value.
 */
export function logicalTypePresence(
  type: LogicalType | undefined,
): "present" | "nullable" | "unknown" {
  if (!type) return "unknown";
  return type.kind === "nullable" ? "nullable" : "present";
}

/** Operations in an expression tree, depth-first, with their result type. */
export function collectOperations(
  expression: Expression | undefined,
): Array<{ name: string; type?: LogicalType; depth: number }> {
  const operations: Array<{ name: string; type?: LogicalType; depth: number }> = [];
  const visit = (node: Expression, depth: number) => {
    if (node.kind === "operation") {
      operations.push({
        name: operationName(node) ?? "operation",
        type: node.logical_type,
        depth,
      });
      for (const argument of node.arguments ?? []) visit(argument, depth + 1);
    }
  };
  if (expression) visit(expression, 0);
  return operations;
}

/** Field key from a data field ref: `relation.field`. */
export function fieldRefKey(ref: Ref | undefined): string {
  if (!ref) return "";
  const joined = ref[2];
  return typeof joined === "string" ? joined : "";
}
