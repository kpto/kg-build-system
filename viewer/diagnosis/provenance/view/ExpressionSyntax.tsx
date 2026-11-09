"use client";

import type { ReactNode } from "react";
import type { Expression } from "@/lib/types";
import { renderExpressionText } from "@/diagnosis/provenance/model/ProvenanceModel";

function literalText(value: unknown): string {
  try {
    return JSON.stringify(value) ?? String(value);
  } catch {
    return String(value);
  }
}

function expressionNodes(
  expression: Expression | undefined,
  depth: number,
): ReactNode {
  if (!expression) return <span className="text-faint">—</span>;
  if (expression.kind === "field") {
    return (
      <span className="text-source" title={expression.field.join(".")}>
        {renderExpressionText(expression)}
      </span>
    );
  }
  if (expression.kind === "literal") {
    return (
      <span
        className="rounded-[2px] bg-target/10 px-1 text-target"
        title={literalText(expression.value)}
      >
        {literalText(expression.value)}
      </span>
    );
  }
  const name = expression.operator.at(-1) ?? "operation";
  if (depth > 6) {
    return <span className="font-semibold text-accent">{name}</span>;
  }
  return (
    <span>
      <span className="font-semibold text-accent">{name}</span>
      <span className="text-faint">(</span>
      {(expression.arguments ?? []).map((argument, index) => (
        <span key={`${depth}-${index}`}>
          {index > 0 ? <span className="text-faint">, </span> : null}
          {expressionNodes(argument, depth + 1)}
        </span>
      ))}
      <span className="text-faint">)</span>
    </span>
  );
}

/**
 * Expression as visual syntax: fields are source-coloured, operators amber and
 * literals emphasised, so a reviewer can read the transformation without
 * parsing a wall of monospace text.
 */
export function ExpressionSyntax({
  expression,
  className = "",
}: {
  expression: Expression | undefined;
  className?: string;
}) {
  return <span className={className}>{expressionNodes(expression, 0)}</span>;
}
