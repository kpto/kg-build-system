import type { AuditFinding, AuditReport, Severity } from "@/lib/reviewTypes";
import type { EntityKind, Expression, ViewerIndex } from "@/lib/types";
import { collectFieldRefs, fieldRefKey, walkExpression } from "@/lib/expressions";
import {
  findComponentPropertyBindings,
  relationNamesFromRowSource,
} from "@/lib/indexes";
import { componentImpact } from "@/lib/impact";

const FALLBACK_OPERATORS = new Set(["coalesce", "default_to"]);
const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"];

export type PropertyBadgeTone =
  | "trace"
  | "literal"
  | "fallback"
  | "multi"
  | "risk"
  | "impact";

export interface PropertyBadgeModel {
  id: string;
  label: string;
  tone: PropertyBadgeTone;
  title: string;
  /** The strongest finding severity for a `risk` badge. */
  severity?: Severity;
}

export interface PropertySourceSummary {
  sources: string[];
  bindings: number[];
}

function resolvedSources(index: ViewerIndex, name: string): string[] {
  if (!name) return [];
  const projection = index.projectionByName.get(name);
  if (projection) {
    const sources = relationNamesFromRowSource(projection.row_source);
    if (sources.length) return sources;
  }
  return [name];
}

/**
 * Name the source relations and binding indexes that feed one property.
 *
 * A property expression references a field owned by a projection. The reviewer
 * needs the underlying table, not the projection, so a projection owner is
 * resolved through its row source.
 */
export function propertySourceSummary(
  index: ViewerIndex,
  kind: EntityKind,
  component: string,
  property: string,
): PropertySourceSummary {
  const entries = findComponentPropertyBindings(index, kind, component, property);
  const sources = new Set<string>();
  for (const entry of entries) {
    for (const ref of entry.fieldRefs) {
      const key = fieldRefKey(ref);
      const owner = index.fieldsByKey.get(key)?.ownerName ?? key.split(".")[0] ?? "";
      for (const source of resolvedSources(index, owner)) sources.add(source);
    }
    for (const relation of relationNamesFromRowSource(entry.binding.binding.rows)) {
      for (const source of resolvedSources(index, relation)) sources.add(source);
    }
  }
  return {
    sources: [...sources].filter(Boolean).sort(),
    bindings: entries.map((entry) => entry.binding.index),
  };
}

function expressionHasLiteral(expression: Expression | undefined): boolean {
  let found = false;
  walkExpression(expression, (node) => {
    if (node.kind === "literal") found = true;
  });
  return found;
}

function expressionHasFallback(expression: Expression | undefined): boolean {
  let found = false;
  walkExpression(expression, (node) => {
    if (
      node.kind === "operation" &&
      FALLBACK_OPERATORS.has(node.operator.at(-1) ?? "")
    ) {
      found = true;
    }
  });
  return found;
}

function propertyFindings(
  audit: AuditReport | undefined,
  component: string,
  property: string,
): AuditFinding[] {
  if (!audit) return [];
  return audit.findings.filter(
    (finding) =>
      finding.subject?.kind === "property" &&
      (finding.subject.component ?? finding.subject.name) === component &&
      finding.subject.property === property,
  );
}

/**
 * The audit badge vocabulary for one topology property.
 *
 * This is the pure model half of the old `PropertyAuditBadges` component: the
 * view receives labels, tone and title, and never traverses bindings, findings
 * or the impact graph itself.
 */
export function buildPropertyBadges(
  index: ViewerIndex,
  audit: AuditReport | undefined,
  kind: EntityKind,
  component: string,
  property: string,
): PropertyBadgeModel[] {
  const entries = findComponentPropertyBindings(index, kind, component, property);
  const sources = propertySourceSummary(index, kind, component, property);
  const findings = propertyFindings(audit, component, property);
  const impact = componentImpact(index, kind, component);

  const expressions = entries
    .map((entry) => entry.expression)
    .filter((expression): expression is Expression => Boolean(expression));
  const traced =
    entries.some((entry) => entry.fieldRefs.length > 0) ||
    expressions.some((expression) => collectFieldRefs(expression).length > 0);
  const literal = expressions.some(expressionHasLiteral);
  const fallback = expressions.some(expressionHasFallback);
  const multiSource = sources.sources.length > 1;
  const impactCount = impact.upstream.length + impact.downstream.length;
  const riskSeverity = SEVERITY_ORDER.find((severity) =>
    findings.some((finding) => finding.severity === severity),
  );

  const badges: PropertyBadgeModel[] = [];
  if (traced) {
    badges.push({
      id: "traced",
      label: "traced",
      tone: "trace",
      title: `${expressions.length} expression branch(es) reference a source field`,
    });
  }
  if (literal) {
    badges.push({
      id: "literal",
      label: "literal",
      tone: "literal",
      title: "The property expression contains a literal value",
    });
  }
  if (fallback) {
    badges.push({
      id: "fallback",
      label: "fallback",
      tone: "fallback",
      title: "The property expression falls back to a literal when the source is missing",
    });
  }
  if (multiSource) {
    badges.push({
      id: "multi-source",
      label: "multi-source",
      tone: "multi",
      title: `Branches read from ${sources.sources.join(", ")}`,
    });
  }
  if (audit && findings.length) {
    badges.push({
      id: "risk",
      label: `risk:${findings.length}`,
      tone: "risk",
      title: findings.map((finding) => finding.rule).join(", "),
      severity: riskSeverity,
    });
  }
  badges.push({
    id: "impact",
    label: `impact:${impactCount}`,
    tone: "impact",
    title: `${impact.upstream.length} upstream and ${impact.downstream.length} downstream steps; targets ${
      impact.targets.join(", ") || "not recorded"
    }`,
  });
  return badges;
}
