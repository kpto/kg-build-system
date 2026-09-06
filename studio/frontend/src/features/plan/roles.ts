/**
 * Artifact-role vocabulary: family, colour and short label for one role string.
 *
 * A plan role is `<namespace>.<name>` (`plan.py::_role_name`), e.g.
 * `core.data.table.sites`, `core.graph.edge.has_unit`,
 * `core.binding.binding:edge:has_defect:4a77…`. The canvas colours edges by this
 * family rather than by module, because the family is what a socket *carries*.
 */

import { TOKEN } from "./tokens";

export type RoleFamily =
  | "table"
  | "projection"
  | "binding"
  | "node"
  | "edge"
  | "publication"
  | "other";

const FAMILIES: readonly { readonly test: (rest: string) => boolean; readonly family: RoleFamily }[] = [
  { test: (rest) => rest.startsWith("data.table"), family: "table" },
  { test: (rest) => rest.startsWith("data.projection"), family: "projection" },
  { test: (rest) => rest.includes("binding:"), family: "binding" },
  { test: (rest) => rest.includes("graph.node.") || rest.includes("component.node."), family: "node" },
  { test: (rest) => rest.includes("graph.edge.") || rest.includes("component.edge."), family: "edge" },
  { test: (rest) => rest.startsWith("publication"), family: "publication" },
];

const COLOR: Record<RoleFamily, string> = {
  table: TOKEN.template,
  projection: TOKEN.edgekind,
  binding: TOKEN.category,
  node: TOKEN.node,
  edge: TOKEN.relation,
  publication: TOKEN.warn,
  other: TOKEN.faint,
};

export const ROLE_LABEL: Record<RoleFamily, string> = {
  table: "declared table",
  projection: "projection",
  binding: "binding view",
  node: "graph node",
  edge: "graph edge",
  publication: "published artifact",
  other: "artifact",
};

/** Split `<namespace>.<name>`; a role without a dot is entirely the name. */
export function roleParts(role: string | null | undefined): { namespace: string; name: string } {
  const value = (role ?? "").trim();
  const dot = value.indexOf(".");
  if (dot < 0) return { namespace: "", name: value };
  return { namespace: value.slice(0, dot), name: value.slice(dot + 1) };
}

export function roleFamily(role: string | null | undefined): RoleFamily {
  const { namespace, name } = roleParts(role);
  if (!name) return "other";
  for (const entry of FAMILIES) if (entry.test(name)) return entry.family;
  return namespace === "workflow" ? "publication" : "other";
}

/** The hex stroke colour for a role, straight off the token set. */
export function roleColor(role: string | null | undefined): string {
  return COLOR[roleFamily(role)];
}

/**
 * The short name beside a socket: `core.graph.edge.has_unit` → `edge.has_unit`,
 * `core.binding.binding:edge:has_defect:4a77…` → `bind has_defect`. The binding
 * symbol's hash suffix identifies nothing a reader can use, so it is dropped.
 */
export function roleLabel(role: string | null | undefined): string {
  const { name } = roleParts(role);
  if (!name) return "";
  const symbol = /binding:(node|edge):([a-z0-9_]+)/.exec(name);
  if (symbol) return `bind ${symbol[2]}`;
  return name
    .replace(/^data\./, "")
    .replace(/^graph\./, "")
    .replace(/^component\./, "")
    .replace(/^publication\./, "");
}

/**
 * The component a role names, or `null`.
 *
 * Roles are the only place the plan records which component a *binding* step
 * belongs to: `plan.py` fails to lift it into `node.component` (see the gap note in
 * the feature README), so the canvas reads it back out of the role.
 */
export function roleComponent(role: string | null | undefined): string | null {
  const { name } = roleParts(role);
  if (!name) return null;
  const symbol = /binding:(?:node|edge):([a-z0-9_]+)/.exec(name);
  if (symbol?.[1]) return symbol[1];
  for (const prefix of ["graph.node.", "graph.edge.", "component.node.", "component.edge."]) {
    const at = name.indexOf(prefix);
    if (at < 0) continue;
    // A neo4j role continues into a python symbol id; the component is the first
    // plain identifier after the prefix.
    const candidate = name.slice(at + prefix.length).split(/[.:]/)[0] ?? "";
    return /^[a-z][a-z0-9_]*$/.test(candidate) ? candidate : null;
  }
  return null;
}
