import type { Expression, Ref, WorkflowStep } from "./types";

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

/** Field key from a data field ref: `relation.field`. */
export function fieldRefKey(ref: Ref | undefined): string {
  if (!ref) return "";
  const joined = ref[2];
  return typeof joined === "string" ? joined : "";
}
