/**
 * Module identity: the role a module plays and the colour its cards' border, header
 * and swatch carry.
 *
 * Nothing here is geometry: with every module drawn in one vertical field, the colour
 * is the only thing telling one module's steps from another's, so it stays the
 * canonical key for both the canvas and the filter strip's chips.
 *
 * The plan declares `modules[].role` (`core | operator | target`); a plan from an
 * older worker may not, so the role is inferred from the module id — `core` is the
 * framework's own module, the three shipped operators are known by id, and
 * everything else publishes something, which makes it a target.
 */

import type { ModuleRole } from "./types";
import { TOKEN } from "./tokens";

const OPERATOR_IDS: readonly string[] = [
  "collapse_exact_duplicates",
  "merge_compatible_facts",
  "reject_conflicting_non_null_values",
];

export function moduleRole(moduleId: string, declared?: string): ModuleRole {
  if (declared === "core" || declared === "operator" || declared === "target") return declared;
  if (moduleId === "core") return "core";
  if (OPERATOR_IDS.includes(moduleId)) return "operator";
  return "target";
}

/** Title-bar colours per role, with a second hue per role so two targets in one
 * plan are still told apart. */
const PALETTE: Record<ModuleRole, readonly string[]> = {
  core: [TOKEN.node],
  operator: [TOKEN.template, TOKEN.edgekind],
  target: [TOKEN.relation, TOKEN.info, TOKEN.warn, TOKEN.category],
};

/**
 * A stable colour for one module: the role's family, rotated by the module's index
 * among the modules sharing that role. Same plan ⇒ same colours, no hashing of the
 * id so a rename cannot repaint the whole canvas.
 */
export function laneColor(moduleId: string, role: ModuleRole, indexInRole: number): string {
  const options = PALETTE[role];
  return options[indexInRole % options.length] as string;
}

/** `moduleId → colour`, given the modules in plan order. */
export function laneColors(modules: readonly { id: string; role?: string }[]): Map<string, string> {
  const seen = new Map<ModuleRole, number>();
  const out = new Map<string, string>();
  for (const module of modules) {
    const role = moduleRole(module.id, module.role);
    const index = seen.get(role) ?? 0;
    seen.set(role, index + 1);
    out.set(module.id, laneColor(module.id, role, index));
  }
  return out;
}
