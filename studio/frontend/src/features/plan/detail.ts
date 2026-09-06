/**
 * Derivations that turn a plan step into what the node body says.
 *
 * The plan projection (`studio/backend/studio_backend/plan.py`) keeps the payload
 * lean: `label`, `kind`, `relation`, `action`, `notes` and `payload_keys` — the
 * payload *values* other than SQL are not lifted. Anything the canvas can only
 * infer is therefore derived here, from the notes and the lowered SQL, and each
 * rule is named so a wrong label is a one-line fix.
 */

import type { ProjectDocument } from "@/lib/ir";
import type { NodeFact, StepDetail, StepEdge, StepKind, StepNode } from "./types";
import { roleComponent, roleLabel } from "./roles";

/** What each step kind is called in the UI. */
export const KIND_LABEL: Record<StepKind, string> = {
  source: "source",
  table: "table",
  projection: "projection",
  binding: "binding",
  aggregate: "aggregate",
  operator: "operator",
  export: "export",
  publish: "publish",
  document: "document",
  script: "script",
  step: "step",
};

const OPERATOR_MEANING: Record<string, string> = {
  collapse_exact_duplicates: "drops rows identical to one already seen",
  merge_compatible_facts: "merges facts that agree on the build key",
  reject_conflicting_non_null_values: "fails the build on disagreeing non-null values",
};

/* ------------------------------------------------------------------ payload */

/** Payload fields can be lifted onto the node or nested under `payload`. */
export function payloadValue(node: StepNode, key: string): unknown {
  const nested = node.payload;
  if (nested && key in nested) return nested[key];
  const record = node as unknown as Record<string, unknown>;
  return record[key];
}

function stringField(node: StepNode, key: string): string | null {
  const value = payloadValue(node, key);
  return typeof value === "string" && value.length > 0 ? value : null;
}

function arrayLength(value: unknown): number | null {
  if (Array.isArray(value)) return value.length;
  if (typeof value === "number" && Number.isFinite(value)) return value;
  return null;
}

/** `← /abs/path/data/sites.json` in the notes is the only place a source records
 * where its bytes live. */
export function noteValue(notes: readonly string[] | undefined, marker: string): string | null {
  for (const note of notes ?? []) {
    if (note.startsWith(marker)) return note.slice(marker.length).trim();
  }
  return null;
}

export function isMaterialised(node: StepNode): boolean {
  if ((node.notes ?? []).includes("materialized")) return true;
  const flag = payloadValue(node, "materialize");
  return flag === true || flag === "true";
}

/* --------------------------------------------------------------------- SQL */

/** Column names the outermost `SELECT … AS "x"` list produces. */
export function selectedColumns(sql: string | null | undefined): string[] {
  if (!sql) return [];
  const text = sql.trim();
  const head = /^SELECT\b/i.exec(text);
  if (!head) return [];
  const from = findTopLevelFrom(text, head.index + head[0].length);
  const list = text.slice(head.index + head[0].length, from < 0 ? text.length : from);
  const names: string[] = [];
  const alias = /AS\s+"([^"]+)"/gi;
  let match: RegExpExecArray | null;
  while ((match = alias.exec(list)) !== null) {
    const name = match[1];
    if (name && !names.includes(name)) names.push(name);
  }
  if (names.length === 0) {
    const bare = /"([^"]+)"/g;
    while ((match = bare.exec(list)) !== null) {
      const name = match[1];
      if (name && !names.includes(name)) names.push(name);
    }
  }
  return names;
}

/** Index of the `FROM` that closes the outer select list, skipping quoted text. */
function findTopLevelFrom(text: string, from: number): number {
  let depth = 0;
  let quoted: string | null = null;
  for (let index = from; index < text.length; index += 1) {
    const char = text[index] as string;
    if (quoted) {
      if (char === quoted) quoted = null;
      continue;
    }
    if (char === '"' || char === "'" || char === "`") {
      quoted = char;
      continue;
    }
    if (char === "(") depth += 1;
    else if (char === ")") depth -= 1;
    else if (depth === 0 && (char === "f" || char === "F") && /^from\b/i.test(text.slice(index, index + 5))) {
      return index;
    }
  }
  return -1;
}

/**
 * Every column a binding step names.
 *
 * A lowered binding's outer select is `SELECT *, '…' AS _kg_binding_symbol FROM
 * (WITH _kg_named AS (SELECT "as_at" AS "_kg_raw_as_at", …))`, so the authoritative
 * column list is the `_kg_named` aliases rather than the outer star.
 */
export function bindingColumns(sql: string | null | undefined): string[] {
  if (!sql) return [];
  const names: string[] = [];
  const alias = /AS\s+"_kg_raw_([A-Za-z0-9_]+)"/g;
  let match: RegExpExecArray | null;
  while ((match = alias.exec(sql)) !== null) {
    const name = match[1];
    if (name && !names.includes(name)) names.push(name);
  }
  if (names.length > 0) return names;
  return selectedColumns(sql).filter((name) => name !== "_kg_binding_symbol");
}

/** The build keys a binding step enforces: the `…_build_key` columns. */
export function buildKeys(sql: string | null | undefined): string[] {
  return bindingColumns(sql).filter((name) => /build_key$/i.test(name));
}

/** Every other column the binding projects. */
export function bindingProperties(sql: string | null | undefined): string[] {
  return bindingColumns(sql).filter((name) => !/build_key$/i.test(name));
}

/* -------------------------------------------------------------- IR identity */

/**
 * The IR ref a step belongs to.
 *
 * `plan.py` puts the ref on `component` for tables, projections, aggregates,
 * operators and exports, but leaves binding steps null even though their output
 * role is `core.binding.binding:edge:has_defect:…`; the role is the authoritative
 * identity, so the canvas recovers the ref from it.
 */
export function stepRef(node: StepNode): string | null {
  if (node.component) return node.component;
  const role = (node.outputs ?? []).map((slot) => slot.role ?? null).find(Boolean) ?? null;
  const component = roleComponent(role);
  return component ? `component:${component}` : null;
}

/** The role the step publishes, for the badge and the edge colour of its output. */
export function primaryRole(node: StepNode): string | null {
  for (const slot of node.outputs ?? []) if (slot.role) return slot.role;
  return null;
}

/* ----------------------------------------------------------- node body text */

/**
 * Everything the node body shows: a one-line meaning, the payload facts worth
 * seeing without opening the sheet, and the chips (`UNION ALL`, `materialized`,
 * `→ graph.jsonl`).
 */
export function stepDetail(node: StepNode, edges: readonly StepEdge[], document: ProjectDocument | null): StepDetail {
  const notes = node.notes ?? [];
  const relation = node.relation ?? stringField(node, "relation");
  const location = stringField(node, "location") ?? noteValue(notes, "←");
  const target = stringField(node, "relative_path") ?? noteValue(notes, "→");
  const facts: NodeFact[] = [];
  const badges: NodeFact[] = [];
  let summary: string | null = null;

  switch (node.kind) {
    case "table":
    case "source": {
      summary = summaryForTable(node, document);
      const columns = declaredColumns(node, document);
      if (columns !== null) {
        facts.push({ text: `${columns} declared columns`, title: `declared_columns from ${node.component ?? "the payload"}` });
      } else if ((node.payload_keys ?? []).includes("declared_columns")) {
        // The plan lists the payload key but not its value (see the gap note in the
        // feature header): say what is known instead of showing nothing.
        facts.push({ text: "declared columns", title: "the step payload carries declared_columns; the plan projection does not send its length" });
      }
      const format = stringField(node, "format") ?? formatFromLocation(location);
      if (format) facts.push({ text: format, tone: "template", title: "input format" });
      if (location) facts.push({ text: shorten(location), tone: "neutral", title: location });
      break;
    }
    case "projection": {
      const fields = projectionFields(node, document);
      summary = fields.length > 0 ? fields.slice(0, 3).join(", ") : "row-wise select over its inputs";
      facts.push({ text: `${fields.length} output fields`, title: fields.join(", ") || undefined });
      if (fields.length > 3) facts.push({ text: fields.slice(3, 6).join(", ") || "", title: fields.join(", ") });
      break;
    }
    case "binding": {
      const keys = buildKeys(node.sql);
      const properties = bindingProperties(node.sql);
      summary = keys.length > 0 ? `build key ${keys.join(" + ")}` : "one component's records";
      facts.push({ text: `${properties.length} properties`, title: properties.join(", ") || undefined });
      if (keys.length > 1) facts.push({ text: keys.map((key) => key.replace(/_build_key$/, "")).join(", ") });
      break;
    }
    case "aggregate": {
      const fanIn = edges.filter((edge) => edge.to_step === node.id).length;
      summary = `${fanIn} binding view${fanIn === 1 ? "" : "s"} unioned`;
      badges.push({ text: "UNION ALL", tone: "info", title: "the aggregate step unions every binding view of this component" });
      break;
    }
    case "operator": {
      summary = OPERATOR_MEANING[node.module_id] ?? "post-processing pass over the graph records";
      break;
    }
    case "export": {
      summary = `→ ${target ?? node.label}`;
      if (target) badges.push({ text: `→ ${shorten(target)}`, tone: "relation", title: target });
      break;
    }
    case "publish": {
      summary = `→ ${target ?? node.label}`;
      badges.push({ text: `→ ${target ?? node.label}`, tone: "relation", title: target ?? undefined });
      break;
    }
    case "document": {
      summary = "graph description document";
      if (target) badges.push({ text: `→ ${shorten(target)}`, tone: "relation", title: target });
      break;
    }
    case "script": {
      summary = "loader script for the exported files";
      break;
    }
    case "step":
    default:
      summary = node.action ?? null;
  }

  if (isMaterialised(node)) badges.push({ text: "materialized", tone: "template" });
  if (relation) facts.push({ text: relation, tone: "info", title: `relation ${relation}` });

  return {
    kindLabel: KIND_LABEL[node.kind] ?? node.kind,
    summary,
    facts: facts.filter((fact) => fact.text.length > 0),
    badges,
    hasSql: typeof node.sql === "string" && node.sql.trim().length > 0,
    relation,
    location,
    target,
  };
}

function summaryForTable(node: StepNode, document: ProjectDocument | null): string {
  const source = sourceFor(node, document);
  if (source) return `reads ${shorten(source.location)}`;
  const location = stringField(node, "location") ?? noteValue(node.notes ?? [], "←");
  return location ? `reads ${shorten(location)}` : "declared input shape";
}

function declaredColumns(node: StepNode, document: ProjectDocument | null): number | null {
  const lifted = arrayLength(payloadValue(node, "declared_columns"));
  if (lifted !== null) return lifted;
  const id = localId(node.component);
  if (id && document) {
    const table = (document.tables ?? []).find((candidate) => candidate.id === id);
    if (table) return (table.fields ?? []).length;
  }
  // The column list is the outer select of the source relation when there is one.
  const columns = selectedColumns(node.sql);
  return columns.length > 0 ? columns.length : null;
}

function projectionFields(node: StepNode, document: ProjectDocument | null): string[] {
  const lifted = payloadValue(node, "fields");
  const asNames = Array.isArray(lifted)
    ? lifted
        .map((field) => (typeof field === "string" ? field : (field as { name?: string })?.name))
        .filter((name): name is string => typeof name === "string")
    : [];
  if (asNames.length > 0) return asNames;
  const id = localId(node.component);
  if (id && document) {
    const projection = (document.projections ?? []).find((candidate) => candidate.id === id);
    const names = (projection?.fields ?? []).map((field) => field.name);
    if (names.length > 0) return names;
  }
  return selectedColumns(node.sql);
}

function sourceFor(node: StepNode, document: ProjectDocument | null) {
  const id = localId(node.component);
  if (!id || !document) return null;
  return (document.sources ?? []).find((source) => source.table === id) ?? null;
}

function localId(ref: string | null | undefined): string | null {
  if (!ref) return null;
  const [, id] = ref.split(":");
  return id && /^[a-z][a-z0-9_]*$/.test(id) ? id : null;
}

function formatFromLocation(location: string | null): string | null {
  if (!location) return null;
  const match = /\.([a-z0-9]+)$/i.exec(location);
  return match?.[1] ? match[1].toLowerCase() : null;
}

/** Long absolute paths are unreadable in a 240 px card; keep the tail. */
export function shorten(value: string, max = 34): string {
  if (value.length <= max) return value;
  return `…${value.slice(value.length - max + 1)}`;
}

/** Human label for an edge's role, used in the legend and the sheet. */
export function edgeLabel(edge: StepEdge): string {
  return roleLabel(edge.role ?? null) || "artifact";
}
