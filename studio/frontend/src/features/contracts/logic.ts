/**
 * Pure logic for the contracts feature: naming, referrer analysis, table-group
 * invariants, the single-driving-source rule for projections, the projection
 * chain summary, the nullability trust tiers, immutable field reorder, and the
 * data-shape import preview.
 *
 * Everything here is a total function over the document (no React, no stores, no
 * network) so the browser renders it and vitest proves it. Mirrors the backend
 * rules in `studio_backend.ir.{names,index,infer,normalize}`; where the frontend
 * derives something the backend also derives (struct homes, group catalogue paths,
 * expression sources) it follows the same rule so the two can never disagree.
 */

import { buildRef } from "@/lib/ids";
import {
  isNullable,
  nullable,
  sectionItems,
  structRef,
  unit,
  sourceBindsTable,
  tableAncestry,
  unwrapNullable,
  type DataField,
  type Expression,
  type LogicalType,
  type NonNullableLogicalType,
  type NullabilityTrust,
  type ProjectDocument,
  type Projection,
  type Source,
  type Struct,
  type Table,
} from "@/lib/ir";
import type { InferResponse } from "@/lib/types";

/* ------------------------------------------------------------------------- naming */

const DATA_SUFFIX: Record<"table" | "group" | "struct" | "projection", string> = {
  table: "Table",
  group: "TableGroup",
  struct: "Struct",
  projection: "Projection",
};

/** Matches `studio_backend.ir.names.snake`: split Pascal boundaries, then non-alnum. */
export function snakeCase(value: string): string {
  let out = value
    .replace(/([A-Z]+)([A-Z][a-z])/g, "$1_$2")
    .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
    .replace(/([A-Za-z])([0-9])/g, "$1_$2")
    .replace(/([0-9])([A-Za-z])/g, "$1_$2")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  out = out || "unnamed";
  return /^[a-z]/.test(out) ? out : `_${out}`.replace(/^_+/, "");
}

/** Matches `pascal`: `has_unit` → `HasUnit`. */
export function pascalCase(value: string): string {
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join("");
}

/**
 * The declaration the generator emits for a data section: `sites` → `SitesTable`,
 * a group → `PublicationsTableGroup`, `premises` → `PremisesStruct`.
 */
export function suggestDeclarationName(
  section: keyof typeof DATA_SUFFIX,
  id: string,
  group = false,
): string {
  const suffix = section === "table" ? (group ? DATA_SUFFIX.group : DATA_SUFFIX.table) : DATA_SUFFIX[section];
  return `${pascalCase(snakeCase(id)) || "Item"}${suffix}`;
}

/**
 * A free snake_case id for a typed label, matching `suggest_id`: a trailing tier
 * suffix is stripped (a table typed "Sites Table" stays `sites`, not `sites_table`)
 * and a suffix is added while the id is taken.
 */
export function suggestId(label: string, taken: Iterable<string>, fallback = "item"): string {
  const used = new Set(taken);
  let stem = snakeCase(label || fallback);
  for (const suffix of ["table_group", "table", "struct", "projection"]) {
    if (stem.endsWith(`_${suffix}`)) {
      stem = stem.slice(0, -suffix.length - 1);
      break;
    }
  }
  stem = stem || fallback;
  if (!used.has(stem)) return stem;
  for (let n = 2; n < 10_000; n += 1) {
    if (!used.has(`${stem}_${n}`)) return `${stem}_${n}`;
  }
  return `${stem}_${Date.now()}`;
}

/* --------------------------------------------------------------- struct references */

/** The qualnames a single logical type points at (arrays and nullables included). */
export function structRefsInType(type: LogicalType): string[] {
  const found: string[] = [];
  const pending: LogicalType[] = [type];
  while (pending.length > 0) {
    const value = pending.pop() as LogicalType;
    if (isNullable(value)) pending.push(value.value);
    else if (value.kind === "array") pending.push(value.item);
    else if (value.kind === "struct") found.push(value.qualname);
  }
  return found;
}

/** Every qualname reachable from a field list, transitively through declared structs. */
export function referencedStructQualnames(
  document: ProjectDocument,
  fields: readonly DataField[],
): string[] {
  const structs = sectionItems(document, "structs");
  const found: string[] = [];
  const seen = new Set<string>();
  const pending = fields.flatMap((field) => structRefsInType(field.logical_type));
  while (pending.length > 0) {
    const qualname = pending.pop() as string;
    if (seen.has(qualname)) continue;
    seen.add(qualname);
    found.push(qualname);
    const struct = structs.find((item) => item.declaration_name === qualname);
    if (struct) pending.push(...struct.fields?.flatMap((field) => structRefsInType(field.logical_type)) ?? []);
  }
  return found;
}

/* -------------------------------------------------------------------- referrers */

export type ReferrerKind = "source" | "group" | "field" | "expression";

export interface Referrer {
  readonly ref: string;
  readonly label: string;
  readonly kind: ReferrerKind;
}

/** The `.source` names every field-reference inside an expression tree reads. */
export function expressionSources(expr: Expression | null | undefined): string[] {
  if (!expr || typeof expr !== "object" || typeof expr.kind !== "string") return [];
  switch (expr.kind) {
    case "field":
      return expr.source ? [expr.source] : [];
    case "operation":
      return (expr.arguments ?? []).flatMap((arg) => expressionSources(arg));
    default:
      return [];
  }
}

/** The struct a `StructType` names, matched by declaration name (unique or nothing). */
export function resolveStruct(document: ProjectDocument, ref: NonNullableLogicalType): Struct | null {
  if (ref.kind !== "struct") return null;
  const matches = sectionItems(document, "structs").filter(
    (item) => item.declaration_name === ref.qualname,
  );
  return matches.length === 1 ? matches[0] ?? null : null;
}

/**
 * The module each struct is referenced by in the document, so a `TypePicker` option
 * value matches an existing reference and re-picking keeps the same spelling. A struct
 * nobody references yet gets `""` — the module the backend (re)derives on save.
 */
export function structModuleMap(document: ProjectDocument): Record<string, string> {
  const map: Record<string, string> = {};
  const scan = (fields: readonly DataField[] | undefined) => {
    for (const field of fields ?? []) {
      const pending: LogicalType[] = [field.logical_type];
      while (pending.length > 0) {
        const value = pending.pop() as LogicalType;
        if (isNullable(value)) pending.push(value.value);
        else if (value.kind === "array") pending.push(value.item);
        else if (value.kind === "struct" && !(value.qualname in map)) map[value.qualname] = value.module;
      }
    }
  };
  for (const table of sectionItems(document, "tables")) scan(table.fields);
  for (const struct of sectionItems(document, "structs")) scan(struct.fields);
  return map;
}

/** Tables and structs whose fields reference this struct by declaration name. */
export function referrersOfStruct(document: ProjectDocument, struct: Struct): Referrer[] {
  const out: Referrer[] = [];
  const scan = (fields: readonly DataField[], id: string, kind: "table" | "struct", name: string) => {
    for (const field of fields) {
      if (structRefsInType(field.logical_type).includes(struct.declaration_name)) {
        out.push({
          ref: buildRef(kind, id),
          label: `${name}.${field.name}`,
          kind: "field",
        });
        return;
      }
    }
  };
  for (const table of sectionItems(document, "tables")) scan(table.fields ?? [], table.id, "table", table.name);
  for (const other of sectionItems(document, "structs")) {
    if (other.id === struct.id) continue;
    scan(other.fields ?? [], other.id, "struct", other.name);
  }
  return out;
}

/** Sources bound to it, groups that own it as a member, expressions that read it. */
export function referrersOfTable(document: ProjectDocument, table: Table): Referrer[] {
  const out: Referrer[] = [];
  for (const source of sectionItems(document, "sources")) {
    if (source.table === table.id || source.table === table.name) {
      out.push({ ref: buildRef("source", source.id), label: source.location, kind: "source" });
    }
  }
  for (const group of sectionItems(document, "tables")) {
    const member = (group.members ?? []).find((item) => item.ref === table.id);
    if (member) {
      out.push({
        ref: buildRef("table", group.id),
        label: `${group.name} ▸ ${member.python_name}`,
        kind: "group",
      });
    }
  }
  for (const [kind, id, name, fields] of expressionBearingEntities(document)) {
    for (const { path, expression } of fields) {
      if (expressionSources(expression).includes(table.name)) {
        out.push({ ref: buildRef(kind, id, ...path), label: name, kind: "expression" });
      }
    }
  }
  return out;
}

/** Bindings and projections whose expressions read this projection as a source. */
export function referrersOfProjection(document: ProjectDocument, projection: Projection): Referrer[] {
  const out: Referrer[] = [];
  for (const [kind, id, name, fields] of expressionBearingEntities(document)) {
    if (kind === "projection" && id === projection.id) continue;
    for (const { path, expression } of fields) {
      if (expressionSources(expression).includes(projection.name)) {
        // A binding is named by its id and the stack that reads it, not by its
        // component: several bindings can write one component, and a delete-blocking
        // list that repeats the same word three times tells the user nothing to fix.
        const label = kind === "binding" ? `${id}.${path.join(".")}` : name;
        out.push({ ref: buildRef(kind, id, ...path), label, kind: "expression" });
      }
    }
  }
  return out;
}

/**
 * The binding stacks that read one specific output of a projection.
 *
 * `referrersOfProjection` answers "who reads this projection at all", which is enough
 * for a delete-impact list but not for navigation: a projection with four outputs is
 * usually consumed by four different stacks, and answering with the first of them
 * sends the user to an unrelated property. A consumer names the output as the first
 * path segment of a field reference (`pathway_participants.target_id`), so matching on
 * it lands on the stack that actually uses the row the user was looking at.
 */
export function outputReaders(
  document: ProjectDocument,
  projection: Projection,
  outputName: string,
): Referrer[] {
  const out: Referrer[] = [];
  for (const [kind, id, _name, fields] of expressionBearingEntities(document)) {
    if (kind !== "binding") continue;
    for (const { path, expression } of fields) {
      if (readsOutput(expression, projection.name, outputName)) {
        // Labelled by the binding's id, not its component: two bindings may write the
        // same component (`clinical_binding` and `preclinical_binding` both publish to
        // `publication`), and the id is what the composer then shows as its heading.
        out.push({ ref: buildRef(kind, id, ...path), label: `${id}.${path.join(".")}`, kind: "expression" });
      }
    }
  }
  return out;
}

/** True when `expression` contains a reference to `<source>.<outputName>`. */
function readsOutput(expression: Expression | null | undefined, source: string, outputName: string): boolean {
  if (!expression || typeof expression !== "object" || typeof expression.kind !== "string") return false;
  if (expression.kind === "field") {
    return expression.source === source && expression.path?.[0] === outputName;
  }
  if (expression.kind === "operation") {
    return (expression.arguments ?? []).some((arg) => readsOutput(arg, source, outputName));
  }
  return false;
}

type ExpressionField = { readonly path: [string, string?]; readonly expression: Expression };

function expressionBearingEntities(
  document: ProjectDocument,
): Array<["binding" | "projection", string, string, readonly ExpressionField[]]> {
  const out: Array<["binding" | "projection", string, string, readonly ExpressionField[]]> = [];
  for (const binding of sectionItems(document, "bindings")) {
    const fields: ExpressionField[] = [
      { path: ["build_key"], expression: binding.build_key },
      ...(binding.source_build_key ? [{ path: ["source_build_key"] as [string], expression: binding.source_build_key }] : []),
      ...(binding.target_build_key ? [{ path: ["target_build_key"] as [string], expression: binding.target_build_key }] : []),
      ...(binding.properties ?? []).map((property) => ({
        path: ["property", property.name] as [string, string],
        expression: property.expression,
      })),
    ];
    out.push(["binding", binding.id, binding.component, fields]);
  }
  for (const projection of sectionItems(document, "projections")) {
    const fields: ExpressionField[] = (projection.fields ?? []).map((field) => ({
      path: ["field", field.name] as [string, string],
      expression: field.expression,
    }));
    out.push(["projection", projection.id, projection.name, fields]);
  }
  return out;
}

/**
 * The tables one source actually delivers data to.
 *
 * A source names a table or a whole group; a group source is a directory plus a
 * `layout`, so it fans out to every leaf member rather than feeding the catalogue
 * itself. The bound table is always included: a group is readable as a logical source
 * in its own right, and a source whose table no longer exists feeds nothing.
 */
export function tablesFed(document: ProjectDocument, source: Source): Table[] {
  const tables = sectionItems(document, "tables");
  const bound = tables.find((table) => sourceBindsTable(source, table));
  if (!bound) return [];
  const out: Table[] = [bound];
  if (isTableGroup(bound)) {
    for (const { table } of resolveGroupSourcePaths(document, source)) {
      if (!out.some((item) => item.id === table.id)) out.push(table);
    }
  }
  return out;
}

/** Whether a *different* source still delivers data to this table, directly or via a group. */
function fedByAnotherSource(document: ProjectDocument, sourceId: string, table: Table): boolean {
  const tables = sectionItems(document, "tables");
  const others = sectionItems(document, "sources").filter((item) => item.id !== sourceId);
  return tableAncestry(tables, table).some((link) => others.some((other) => sourceBindsTable(other, link)));
}

/**
 * What still needs the data behind this source.
 *
 * Nothing in the document names a source — the pointer runs source → table — so the
 * question has to be asked one step further out: which tables does this source feed,
 * and does any of them still get its data from somewhere else once it is gone? A
 * table left unbound is the state the Sources tab already offers to repair; a binding
 * or projection that reads a table with no feed left cannot compile at all, so those
 * readers are what blocks the delete. They are named by id (a binding's id, never its
 * component — two bindings can write one component) together with the table they would
 * lose, which is the thing the user has to go repoint.
 */
export function referrersOfSource(document: ProjectDocument, source: Source): Referrer[] {
  const out: Referrer[] = [];
  for (const table of tablesFed(document, source)) {
    if (fedByAnotherSource(document, source.id, table)) continue;
    for (const [kind, id, _name, fields] of expressionBearingEntities(document)) {
      for (const { path, expression } of fields) {
        if (expressionSources(expression).includes(table.name)) {
          out.push({
            ref: buildRef(kind, id, ...path),
            label: `${id}.${path.join(".")} reads ${table.id}`,
            kind: "expression",
          });
        }
      }
    }
  }
  return out;
}

/** Every referrer that would dangle if `kind:id` were deleted, across all kinds. */
export function referrersForDeletion(
  document: ProjectDocument,
  kind: "table" | "struct" | "projection" | "source",
  id: string,
): Referrer[] {
  if (kind === "source") {
    const source = sectionItems(document, "sources").find((item) => item.id === id);
    return source ? referrersOfSource(document, source) : [];
  }
  if (kind === "struct") {
    const struct = sectionItems(document, "structs").find((item) => item.id === id);
    return struct ? referrersOfStruct(document, struct) : [];
  }
  if (kind === "table") {
    const table = sectionItems(document, "tables").find((item) => item.id === id);
    return table ? referrersOfTable(document, table) : [];
  }
  const projection = sectionItems(document, "projections").find((item) => item.id === id);
  return projection ? referrersOfProjection(document, projection) : [];
}

/* ------------------------------------------------------------- table-group model */

/** Whether the table owns a catalogue (a group), mirroring `Table.is_group`. */
export function isTableGroup(table: Table): boolean {
  return (table.members?.length ?? 0) > 0;
}

/**
 * Whether the table exists only to own a catalogue, mirroring `index.is_group_only`:
 * a member table built by copying a group keeps the group's `members` alongside its
 * own fields, so "owns a catalogue" and "has nothing to read" are separate questions.
 */
export function isGroupOnly(table: Table): boolean {
  return isTableGroup(table) && (table.fields?.length ?? 0) === 0;
}

/**
 * Whether a table was authored as a group (its class name ends in `TableGroup`), which
 * is true even before it gains its first member. `isGroupOnly` is the framework's answer
 * (needs members); this is the studio's authoring-intent answer, so an empty group you
 * are mid-way through building still shows its catalogue editor rather than a field grid.
 */
export function isGroupDeclaration(table: Table): boolean {
  return table.declaration_name.endsWith("TableGroup");
}

/** Resolve a group's `members` to their tables, in member order. */
export function memberTables(document: ProjectDocument, group: Table): Table[] {
  const byId = new Map(sectionItems(document, "tables").map((item) => [item.id, item]));
  return (group.members ?? [])
    .map((member) => byId.get(member.ref))
    .filter((table): table is Table => table !== undefined);
}

/** The group a member points back to, via its `group` id. */
export function parentGroup(document: ProjectDocument, table: Table): Table | null {
  if (!table.group) return null;
  return sectionItems(document, "tables").find((item) => item.id === table.group) ?? null;
}

/**
 * The catalogue path of a table: group names outermost first, then its own name.
 * Mirrors `infer.catalog_path`, guarding against a non-terminating parent chain.
 */
export function catalogPath(document: ProjectDocument, table: Table): string[] {
  const parts = [table.name];
  const seen = new Set([table.id]);
  let parentId = table.group;
  while (parentId) {
    if (seen.has(parentId)) break;
    seen.add(parentId);
    const parent = sectionItems(document, "tables").find((item) => item.id === parentId);
    if (!parent) break;
    parts.push(parent.name);
    parentId = parent.group;
  }
  return parts.reverse();
}

/** The dotted address of a member (`readings.mechanical.vibration`), else its name. */
export function tableAddress(document: ProjectDocument, table: Table): string {
  return catalogPath(document, table).join(".");
}

export interface AddMemberResult {
  readonly ok: boolean;
  readonly reason?: string;
  readonly document?: ProjectDocument;
}

/**
 * Add `memberId` to `groupId`, setting the member's `group` and appending a
 * `TableGroupMember`. Enforces the framework's group invariants (see §9): no self,
 * no duplicate member, no cycle, unique catalogue path. Returns the rebuilt document
 * only when the invariant holds.
 */
export function addMemberToGroup(
  document: ProjectDocument,
  groupId: string,
  memberId: string,
  pythonName?: string,
): AddMemberResult {
  const tables = sectionItems(document, "tables");
  const group = tables.find((item) => item.id === groupId);
  const member = tables.find((item) => item.id === memberId);
  if (!group) return { ok: false, reason: "the group no longer exists" };
  if (!member) return { ok: false, reason: "the member table no longer exists" };
  if (group.id === member.id) return { ok: false, reason: "a group cannot contain itself" };
  if ((group.members ?? []).some((item) => item.ref === member.id)) {
    return { ok: false, reason: `${member.name} is already a member of ${group.name}` };
  }
  // Reject a cycle: making `member` a child of `group` loops the catalogue when
  // `group` already sits below `member`, i.e. walking up from the group reaches it.
  let walk: Table | null = group;
  const guard = new Set<string>();
  while (walk) {
    if (walk.id === member.id) {
      return { ok: false, reason: `adding ${member.name} to ${group.name} would make a group contain itself` };
    }
    if (guard.has(walk.id)) break;
    guard.add(walk.id);
    walk = parentGroup(document, walk);
  }
  const name = pythonName ?? suggestId(member.name, (group.members ?? []).map((item) => item.python_name));
  const nextTables = tables.map((item) => {
    if (item.id === member.id) return { ...item, group: group.id } as Table;
    if (item.id === group.id) {
      return { ...item, members: [...(item.members ?? []), { python_name: name, ref: member.id }] } as Table;
    }
    return item;
  });
  return { ok: true, document: { ...document, tables: nextTables } };
}

/**
 * Render a group source's `{group_path}`/`{table_name}` layout for every leaf member,
 * resolving it against the source `location`. Mirrors how the framework expands a
 * group bind_source into one canonical path per final table.
 */
export function resolveGroupSourcePaths(
  document: ProjectDocument,
  source: Source,
): Array<{ table: Table; path: string }> {
  const group = sectionItems(document, "tables").find((item) => item.id === source.table);
  if (!group || !isTableGroup(group)) return [];
  const layout = source.layout ?? "{group_path}/{table_name}";
  const out: Array<{ table: Table; path: string }> = [];
  const visited = new Set<string>([group.id]);
  const walk = (members: Table[], prefix: string[]) => {
    for (const member of members) {
      // Only a catalogue-only group nests; a member table that kept a copied
      // `members` list (it has fields too) is a leaf, and self-membership stays out.
      const children = isGroupOnly(member) && !visited.has(member.id) ? memberTables(document, member) : [];
      if (children.length > 0) {
        visited.add(member.id);
        walk(children, [...prefix, member.name]);
      } else {
        const groupPath = prefix.join("/");
        const rendered = layout.replace("{group_path}", groupPath).replace("{table_name}", member.name);
        const path = `${source.location.replace(/\/+$/, "")}/${rendered}`.replace(/\/{2,}/g, "/");
        out.push({ table: member, path });
      }
    }
  };
  walk(memberTables(document, group), [group.name]);
  return out;
}

/** Which source (if any) binds a table or one of its ancestor groups. */
export function boundSourceForTable(document: ProjectDocument, table: Table): Source | null {
  const sources = sectionItems(document, "sources");
  for (const link of tableAncestry(sectionItems(document, "tables"), table)) {
    const direct = sources.find((source) => sourceBindsTable(source, link));
    if (direct) return direct;
  }
  return null;
}

/* ----------------------------------------------------------- provenance hint */

/**
 * A shape is "generated from data/<feed>" when its fields carry a physical schema
 * path (set only by `POST /api/infer`, never by hand authoring). The feed is the
 * bound source's location when there is one, else the root of the schema path.
 */
export function shapeProvenance(
  document: ProjectDocument,
  table: Table,
): { inferred: boolean; feed: string | null } {
  const fields = table.fields ?? [];
  const inferred = fields.some((field) => (field.schema_path ?? "").length > 0);
  if (!inferred) return { inferred: false, feed: null };
  const source = boundSourceForTable(document, table);
  if (source) return { inferred: true, feed: feedPathFor(document, source, table) };
  const firstPath = fields.find((field) => field.schema_path)?.schema_path ?? "";
  return { inferred: true, feed: firstPath ? firstPath.split(".")[0] ?? null : null };
}

/**
 * The file one table actually reads. A group source names a directory plus a layout,
 * so every member resolves to its own path; a plain source already names the file.
 */
export function feedPathFor(document: ProjectDocument, source: Source, table: Table): string {
  if (!source.layout) return source.location;
  const expanded = resolveGroupSourcePaths(document, source).find(
    (item) => item.table.id === table.id,
  );
  return expanded?.path ?? source.location;
}

/* ---------------------------------------------------- single driving source rule */

export interface DrivingSource {
  readonly sources: readonly string[];
  readonly driving: string | null;
  readonly count: number;
  readonly conflict: boolean;
}

/**
 * A projection reads exactly one driving logical source (§6). The driving source is
 * derived from the outputs' field references, never stored. A second distinct source
 * is a framework violation, so it is reported rather than hidden.
 */
export function drivingSource(projection: Projection): DrivingSource {
  const seen: string[] = [];
  for (const field of projection.fields ?? []) {
    for (const source of expressionSources(field.expression)) {
      if (!seen.includes(source)) seen.push(source);
    }
  }
  return {
    sources: seen,
    driving: seen.length === 1 ? seen[0] ?? null : null,
    count: seen.length,
    conflict: seen.length > 1,
  };
}

/**
 * Whether a candidate output expression may join the projection: allowed while it
 * references no source (a literal), or the projection's one driving source. A second
 * source is rejected with the framework rule stated.
 */
export function canAddOutput(document: ProjectDocument, projection: Projection, candidate: Expression): { ok: boolean; reason?: string } {
  const candidateSources = new Set(expressionSources(candidate));
  if (candidateSources.size === 0) return { ok: true };
  const current = drivingSource(projection).sources.filter((name) => sectionItems(document, "tables").some((t) => t.name === name) || sectionItems(document, "projections").some((p) => p.name === name));
  if (current.length === 0) return { ok: true };
  if (current.length === 1 && candidateSources.has(current[0] as string)) return { ok: true };
  return {
    ok: false,
    reason: `a projection has one driving source (${current.join(", ")}); this output also reads ${[...candidateSources].join(", ")}. Bring the second source in through its own projection and read that.`,
  };
}

/* --------------------------------------------------------------- chain summary */

const CHAIN_VERB: Readonly<Record<string, string>> = {
  expand: "expand",
  where_present: "where_present",
  without_nulls: "without_nulls",
  sorted: "sorted",
  distinct: "distinct",
};

function literalToken(value: unknown): string {
  if (value === null) return "null";
  if (typeof value === "string") return JSON.stringify(value);
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "…";
}

function chainSegments(expr: Expression | null | undefined): string[] {
  if (!expr || typeof expr !== "object" || typeof expr.kind !== "string") return ["?"];
  switch (expr.kind) {
    case "field":
      return [`${expr.source ?? "?"}.${(expr.path ?? []).join(".")}`];
    case "literal":
      return [literalToken(expr.value ?? null)];
    case "operation": {
      const args = expr.arguments ?? [];
      const base = args.length > 0 ? chainSegments(args[0]) : [];
      const name = expr.parameters?.name;
      let token: string;
      const verb = CHAIN_VERB[expr.operator];
      if (expr.operator === "struct_field") {
        token = `struct_field(${typeof name === "string" ? name : "?"})`;
      } else if (expr.operator === "map_items") {
        token = `map_items(${typeof name === "string" ? name : "?"})`;
      } else if (verb !== undefined) {
        token = verb;
      } else if (expr.operator === "coalesce") {
        token = `coalesce(${literalToken((args[1] as { value?: unknown } | undefined)?.value)})`;
      } else {
        const extra = args.slice(1).map((arg) => literalToken((arg as { value?: unknown } | undefined)?.value)).join(", ");
        token = `${expr.operator}${extra ? `(${extra})` : ""}`;
      }
      return [...base, token];
    }
    default:
      return ["?"];
  }
}

/**
 * A projection output rendered as a left-to-right reading chain, e.g.
 * `pathways.steps ▸ expand ▸ struct_field(participants) ▸ expand ▸ struct_field(molecule_id)`.
 */
export function chainSummary(expr: Expression | null | undefined): string {
  return chainSegments(expr).join(" ▸ ");
}

/* -------------------------------------------------------------- trust tiers */

export interface TrustTier {
  readonly value: NullabilityTrust;
  readonly label: string;
  readonly permits: string;
  readonly renders: string;
  readonly tooltip: string;
}

/**
 * The three schema-trust levels from SOURCE_SCHEMA_TRUST_AND_NULLABILITY_SPEC §3,
 * stated in terms of what each permits a member to claim.
 */
export const TRUST_TIERS: readonly TrustTier[] = [
  {
    value: "declared",
    label: "declared",
    permits: "the source asserts non-null, so a non-null type is allowed",
    renders: "Field[X]",
    tooltip:
      "DECLARED — the format declares non-null (e.g. Parquet required) but no engine enforces it. Renders Field[X]; guarded at the point of use on every build.",
  },
  {
    value: "enforced",
    label: "enforced",
    permits: "an upstream store guarantees non-null, so a non-null type is trusted",
    renders: "Field[X]",
    tooltip:
      "ENFORCED — a NOT NULL constraint upstream guarantees it (a stored relation). Renders Field[X]; not re-checked, so the claim rests on the store.",
  },
  {
    value: "defaulted",
    label: "defaulted",
    permits: "the source says nothing, so every level is nullable",
    renders: "Field[X | None]",
    tooltip:
      "DEFAULTED — schema-less sources (JSON, CSV) declare nothing; nullability is never inferred from values. Renders Field[X | None] at every level.",
  },
];

export function trustTier(value: NullabilityTrust | undefined): TrustTier {
  const byValue = TRUST_TIERS.find((item) => item.value === (value ?? "defaulted"));
  if (byValue) return byValue;
  const fallback = TRUST_TIERS.find((item) => item.value === "defaulted");
  return fallback ?? TRUST_TIERS[0]!;
}

/** Whether a non-null logical type is honest under the tier (nullability claim check). */
export function trustAllowsNonNull(type: LogicalType, trust: NullabilityTrust): boolean {
  return isNullable(type) || trust !== "defaulted";
}

/* ----------------------------------------------------------- field affordances */

/**
 * "What can I do with this field" — the selections the authoring contract (§5) makes
 * available from a field's normalized shape: a nullable unwraps with `where_present`
 * or `default_to`, an array expands, a struct picks. Rendered as a compact hint so a
 * field row states its reachable operations without the author reading the spec.
 */
export function fieldAffordances(type: LogicalType): string[] {
  const affordances: string[] = [];
  if (isNullable(type)) affordances.push("where_present", "default_to");
  const core = unwrapNullable(type);
  if (core.kind === "array") {
    affordances.push("expand");
    const item = unwrapNullable(core.item);
    if (item.kind === "struct") affordances.push("map_items");
  } else if (core.kind === "struct") {
    affordances.push("pick");
  }
  return affordances;
}

/* --------------------------------------------------------------- field reorder */

/** Immutable `arrayMove`: a new array with the item at `from` inserted at `to`. */
export function reorderFields<F>(fields: readonly F[], from: number, to: number): F[] {
  if (from === to || from < 0 || to < 0 || from >= fields.length || to >= fields.length) {
    return [...fields];
  }
  const next = [...fields];
  const [moved] = next.splice(from, 1);
  next.splice(to, 0, moved as F);
  return next;
}

/* ------------------------------------------------------------- import preview */

export type ImportMode = "table" | "table_group";
export interface ImportPreview {
  readonly location: string;
  readonly mode: ImportMode;
  readonly newTables: Table[];
  readonly existingTableIds: string[];
  readonly newStructs: Struct[];
  readonly existingStructIds: string[];
  readonly notes: readonly string[];
  readonly totalNew: number;
}

/** Fold a `/api/infer` response against the current document into a preview. */
export function buildImportPreview(response: InferResponse, document: ProjectDocument, location: string, mode: ImportMode): ImportPreview {
  const tables = response.tables ?? [];
  const structs = response.structs ?? [];
  const existingTables = new Set(sectionItems(document, "tables").map((item) => item.id));
  const existingStructs = new Set(sectionItems(document, "structs").map((item) => item.id));
  const newTables = tables.filter((item) => !existingTables.has(item.id));
  const newStructs = structs.filter((item) => !existingStructs.has(item.id));
  return {
    location,
    mode,
    newTables,
    existingTableIds: tables.filter((item) => existingTables.has(item.id)).map((item) => item.id),
    newStructs,
    existingStructIds: structs.filter((item) => existingStructs.has(item.id)).map((item) => item.id),
    notes: response.notes ?? [],
    totalNew: newTables.length + newStructs.length,
  };
}

/**
 * Merge an import preview into the document: add the new tables/structs only, leaving
 * anything already declared alone. Mirrors `infer_contract.InferredShape.merge_into`.
 */
export function applyImportPreview(document: ProjectDocument, preview: ImportPreview): ProjectDocument {
  const tables = [...sectionItems(document, "tables")];
  for (const table of preview.newTables) {
    if (!tables.some((item) => item.id === table.id)) tables.push(table);
  }
  const structs = [...sectionItems(document, "structs")];
  for (const struct of preview.newStructs) {
    if (!structs.some((item) => item.id === struct.id)) structs.push(struct);
  }
  return { ...document, tables, structs };
}

const maybeStr = nullable(unit("str"));

/**
 * Offline fixtures for the mock demo, mirroring `studio/examples/target-pathways.ir.json`
 * and the `studio_test_project/data/*.json` feeds. They let the whole import flow run
 * with no backend, and their `schema_path`s mark them as inferred shapes. Used only
 * when `/api/infer` is unreachable; the live path calls the real inference provider.
 */
const OFFLINE_FEEDS: Readonly<Record<string, { tables: Table[]; structs: Struct[] }>> = {
  targets: {
    tables: [
      {
        id: "targets",
        declaration_name: "TargetsTable",
        name: "targets",
        fields: [
          { name: "target_id", logical_type: maybeStr, schema_path: "target_id", nullability: "defaulted" },
          { name: "symbol", logical_type: maybeStr, schema_path: "symbol", nullability: "defaulted" },
          { name: "reviewed", logical_type: nullable(unit("bool")), schema_path: "reviewed", nullability: "defaulted" },
          {
            name: "attributes",
            logical_type: nullable(structRef("", "AttributesStruct")),
            schema_path: "attributes",
            nullability: "defaulted",
          },
        ],
        members: [],
        group: null,
      },
    ],
    structs: [
      {
        id: "attributes",
        declaration_name: "AttributesStruct",
        name: "attributes",
        fields: [
          { name: "sequence_length", logical_type: nullable(unit("int")), schema_path: "attributes.sequence_length" },
          { name: "curator", logical_type: nullable(structRef("", "AttributesCuratorStruct")), schema_path: "attributes.curator" },
        ],
      },
      {
        id: "attributes_curator",
        declaration_name: "AttributesCuratorStruct",
        name: "attributes_curator",
        fields: [
          { name: "name", logical_type: maybeStr, schema_path: "attributes.curator.name" },
          { name: "team", logical_type: nullable(structRef("", "AttributesCuratorTeamStruct")), schema_path: "attributes.curator.team" },
        ],
      },
      {
        id: "attributes_curator_team",
        declaration_name: "AttributesCuratorTeamStruct",
        name: "attributes_curator_team",
        fields: [{ name: "code", logical_type: maybeStr, schema_path: "attributes.curator.team.code" }],
      },
    ],
  },
  publications: {
    tables: [
      {
        id: "clinical",
        declaration_name: "ClinicalTable",
        name: "clinical",
        fields: [
          { name: "publication_id", logical_type: maybeStr, schema_path: "publication_id" },
          { name: "target_id", logical_type: maybeStr, schema_path: "target_id" },
          { name: "subjects", logical_type: nullable(unit("int")), schema_path: "subjects" },
        ],
        members: [],
        group: "publications",
      },
      {
        id: "preclinical",
        declaration_name: "PreclinicalTable",
        name: "preclinical",
        fields: [
          { name: "publication_id", logical_type: maybeStr, schema_path: "publication_id" },
          { name: "assay", logical_type: maybeStr, schema_path: "assay" },
        ],
        members: [],
        group: "publications",
      },
      {
        id: "publications",
        declaration_name: "PublicationsTableGroup",
        name: "publications",
        fields: [],
        members: [
          { python_name: "clinical", ref: "clinical" },
          { python_name: "preclinical", ref: "preclinical" },
        ],
        group: null,
      },
    ],
    structs: [],
  },
};

/**
 * It reuses a shape the sample document already declares (matched by id or name, at
 * its natural id) so the whole import flow is developable, then folds it through the
 * same `buildImportPreview` split the live path uses — an already-present table reads
 * as "exists" rather than an invented duplicate. Never used when the backend answers.
 */
export function offlineImportPreview(
  document: ProjectDocument,
  location: string,
  mode: ImportMode,
): ImportPreview | null {
  const basename = location.split("/").pop()?.replace(/\.[^.]+$/, "") ?? "";
  if (!basename) return null;
  const id = snakeCase(basename);
  const canned = OFFLINE_FEEDS[id];
  if (canned) {
    const response: InferResponse = {
      tables: canned.tables,
      structs: canned.structs,
      notes: ["offline sample shape — the live backend derives this from POST /api/infer"],
    };
    return buildImportPreview(response, document, location, mode);
  }
  const tables = sectionItems(document, "tables");
  const match = tables.find((item) => item.id === id || item.id === basename || item.name === basename);
  if (!match) return null;
  const asGroup = isGroupOnly(match);
  const cloned: Table = {
    ...match,
    id,
    name: id,
    declaration_name: suggestDeclarationName(asGroup ? "group" : "table", id, asGroup),
    group: null,
    members: asGroup ? match.members : [],
  };
  const referenced = new Set(referencedStructQualnames(document, cloned.fields ?? []));
  const structs = sectionItems(document, "structs").filter((item) => referenced.has(item.declaration_name));
  const response: InferResponse = {
    tables: [cloned],
    structs,
    notes: ["offline sample shape — the live backend derives this from POST /api/infer"],
  };
  return buildImportPreview(response, document, location, mode);
}
