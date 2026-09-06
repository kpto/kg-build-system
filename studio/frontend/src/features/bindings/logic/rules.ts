/**
 * The binding-level rules: key legality, slot type safety, endpoint tokens.
 *
 * Each check reproduces one gate in `kg_build_system/binding/factories.py` so a
 * problem the studio refuses to compose and a problem the framework raises on the
 * generated Python are the same problem, worded the same way — the diagnostics mapper
 * matches framework errors by their text, so a message here that matches the
 * framework's helps the author connect the two.
 */

import type { Binding, Expression, LogicalType, NonNullableLogicalType, Property } from "@/lib/ir";
import type { ComponentIndexEntry, ResolvedProperty } from "@/lib/types";
import { isNullable, typeLabel, unwrapNullable } from "@/lib/ir";
import type { BindingContext } from "./context";
import { compatible, componentEntry, documentComponent, resolvedSlots } from "./context";
import { inferExpression } from "./typecheck";

/* ---------------------------------------------------------------------------- keys */

export interface KeyCheck {
  readonly argument: string;
  readonly ok: boolean;
  /** The framework's own wording, so the message matches the blueprint error. */
  readonly message: string | null;
  /** The one-click repair, when one exists. */
  readonly fix: "where_present" | null;
}

/**
 * A key must be a value expression, a scalar, and never nullable — checked in that
 * order, worded after the argument's own name (`source_build_key must be a scalar`),
 * which is exactly `binding/factories.py::_require_key`.
 */
export function checkKey(argument: string, type: LogicalType | null | undefined): KeyCheck {
  const base = { argument, ok: true, message: null as string | null, fix: null as KeyCheck["fix"] };
  if (type == null) return { ...base, ok: false, message: `${argument} must be a value selection or expression` };
  const core = unwrapNullable(type);
  if (core.kind === "array" || core.kind === "struct") {
    return { ...base, ok: false, message: `${argument} must be a scalar, and it resolves to ${typeLabel(type)}` };
  }
  if (isNullable(type)) {
    return {
      ...base,
      ok: false,
      message: `${argument} must not be nullable, and it resolves to ${typeLabel(type)}`,
      fix: "where_present",
    };
  }
  return base;
}

/** Every key a binding must satisfy, in the order the factory checks them. */
export function keyChecks(binding: Binding): readonly { readonly argument: string; readonly expression: Expression | null }[] {
  const keys: { argument: string; expression: Expression | null }[] = [
    { argument: "build_key", expression: binding.build_key ?? null },
  ];
  if (binding.kind === "edge") {
    keys.push(
      { argument: "source_build_key", expression: binding.source_build_key ?? null },
      { argument: "target_build_key", expression: binding.target_build_key ?? null },
    );
  }
  return keys;
}

/* -------------------------------------------------------------------- slot safety */

export interface SlotCheck {
  readonly ok: boolean;
  readonly expected: LogicalType | null;
  readonly actual: LogicalType | null;
  readonly message: string | null;
  readonly hint: string | null;
}

/**
 * `binding/factories.py::_require_properties` + `_compatible`: an exact match, or a
 * non-null expression given to a nullable slot. The failure text is the framework's,
 * with the domain-model repr it prints (`UnitType(name='str')`), because that is the
 * string the diagnostics mapper parses to place the problem back on this slot.
 */
export function checkSlot(componentName: string, slot: ResolvedProperty | null, actual: LogicalType | null): SlotCheck {
  if (!slot) {
    return {
      ok: true,
      expected: null,
      actual,
      message: null,
      hint: "the component declares no such slot — check the property name in Topology",
    };
  }
  const expected = slot.logical_type;
  const matches = typeEqual(expected, actual) || (isNullable(expected) && typeEqual(unwrapNullable(expected), actual));
  if (matches) return { ok: true, expected, actual, message: null, hint: null };
  return {
    ok: false,
    expected,
    actual,
    message: `${componentName}.${slot.name} expects ${domainRepr(expected)}, but the expression resolves to ${
      actual == null ? "nothing yet" : domainRepr(actual)
    }`,
    hint: `Property '${slot.name}' is declared ${typeLabel(expected)} on component ${componentName}.`,
  };
}

function typeEqual(a: LogicalType | null | undefined, b: LogicalType | null | undefined): boolean {
  if (a == null || b == null) return false;
  return JSON.stringify(a) === JSON.stringify(b);
}

/** `repr()` of the framework's dataclass logical type. */
export function domainRepr(type: LogicalType | NonNullableLogicalType | null | undefined): string {
  if (type == null) return "None";
  switch (type.kind) {
    case "unit":
      return `UnitType(name='${type.name}')`;
    case "array":
      return `ArrayType(item=${domainRepr(type.item)})`;
    case "struct":
      return `StructType(module='${type.module}', qualname='${type.qualname}')`;
    case "nullable":
      return `NullableType(value=${domainRepr(type.value)})`;
    default:
      return "None";
  }
}

/** Where a stack has to end up, so its head can be judged before anything is picked. */
export interface HeadTarget {
  readonly componentName: string;
  /** The slot the stack fills; null for a key and for a name the component does not declare. */
  readonly slot: ResolvedProperty | null;
  /** The key argument the stack fills; null for a property slot. */
  readonly key: string | null;
}

export interface HeadCheck {
  readonly ok: boolean;
  /** The head fills the target only once the stack unwraps it with `where_present`. */
  readonly unwrap: boolean;
  readonly message: string | null;
}

/**
 * `checkSlot`/`_require_key` moved to the front of the stack: what a head may be, given
 * where the stack has to end up. A nullable column may start a stack for a non-null slot
 * or key because the composer unwraps it with `where_present`, so it is answered `unwrap`
 * rather than refused; a value that can never satisfy the target is refused with the very
 * sentence the finished stack would be refused in.
 */
export function checkHead(type: LogicalType, target: HeadTarget): HeadCheck {
  if (target.key != null) {
    const check = checkKey(target.key, type);
    if (check.ok) return { ok: true, unwrap: false, message: null };
    if (check.fix === "where_present") return { ok: true, unwrap: true, message: null };
    return { ok: false, unwrap: false, message: check.message };
  }
  const check = checkSlot(target.componentName, target.slot, type);
  if (check.ok) return { ok: true, unwrap: false, message: null };
  if (target.slot && compatible(target.slot.logical_type, unwrapNullable(type))) {
    return { ok: true, unwrap: true, message: null };
  }
  return { ok: false, unwrap: false, message: check.message };
}

/** The slot a property binding fills, inherited slots included. */
export function slotFor(ctx: BindingContext, componentId: string, name: string): ResolvedProperty | null {
  return resolvedSlots(ctx, componentId).find((slot) => slot.name === name) ?? null;
}

/** Slots a binding still owes: non-optional and unfilled (`ir/index.py::unbound_required_slots`). */
export function unboundSlots(ctx: BindingContext, binding: Binding): readonly ResolvedProperty[] {
  const filled = new Set((binding.properties ?? []).map((item) => item.name));
  return resolvedSlots(ctx, binding.component).filter((slot) => !slot.optional && !filled.has(slot.name));
}

export const optionalSlots = (ctx: BindingContext, binding: Binding): readonly ResolvedProperty[] =>
  resolvedSlots(ctx, binding.component).filter((slot) => slot.optional);

/* ----------------------------------------------------------------------- endpoints */

export interface EndpointSide {
  readonly side: "source" | "target";
  readonly required: boolean;
  readonly category: string | null;
  readonly options: readonly { value: string; label: string }[];
  readonly message: string | null;
}

/**
 * `source_node=`/`target_node=` take an `endpoint(ConcreteNode)` token required
 * *exactly when* the declared endpoint is a category, and the named component must be
 * concrete and equal to or descending from that category. A node component has no
 * endpoints and answers "not required" on both sides.
 */
export function endpointSides(ctx: BindingContext, componentId: string): readonly EndpointSide[] {
  const component = documentComponent(ctx, componentId);
  if (!component || component.kind !== "edge") return [];
  const entry = componentEntry(ctx, componentId);
  const declared = declaredEndpoints(ctx, componentId);
  return (["source", "target"] as const).map((side) => {
    const endpointId = side === "source" ? declared[0] : declared[1];
    const category = endpointId ? documentComponent(ctx, endpointId) : null;
    const flag = entry?.endpoint_is_category?.[side] ?? category?.tier === "category";
    const options = concreteDescendants(ctx, endpointId);
    return {
      side,
      required: Boolean(flag),
      category: category?.declaration_name ?? endpointId ?? null,
      options,
      message:
        flag && options.length === 0
          ? `no concrete node component descends from ${category?.declaration_name ?? endpointId} yet, so this binding cannot name the side`
          : null,
    };
  });
}

/** The component's endpoints, inherited from its edge parent when undeclared. */
export function declaredEndpoints(ctx: BindingContext, componentId: string): readonly [string | null, string | null] {
  const seen = new Set<string>();
  let current = documentComponent(ctx, componentId);
  while (current && !seen.has(current.id)) {
    if (current.source || current.target) return [current.source ?? null, current.target ?? null];
    seen.add(current.id);
    current = current.parent ? documentComponent(ctx, current.parent) : null;
  }
  return [current?.source ?? null, current?.target ?? null];
}

/** Concrete node components equal to or descending from `ancestorId`. */
export function concreteDescendants(
  ctx: BindingContext,
  ancestorId: string | null | undefined,
): readonly { value: string; label: string }[] {
  if (!ancestorId) return [];
  const components = ctx.document.components ?? [];
  const descends = (id: string | null | undefined, guard = 0): boolean => {
    if (!id || guard > 20) return false;
    if (id === ancestorId) return true;
    const item = components.find((candidate) => candidate.id === id);
    if (!item) return false;
    return descends(item.parent, guard + 1) || (item.mixins ?? []).some((name) => descends(name, guard + 1));
  };
  return components
    .filter((item) => item.kind === "node" && item.tier === "concrete" && descends(item.id))
    .map((item) => ({ value: item.id, label: item.declaration_name }));
}

/** The framework's wording for a missing token, per side. */
export const missingEndpointMessage = (side: "source" | "target", category: string | null): string =>
  `${side}_node must name the declared endpoint category ${category ?? "the category"}: pass endpoint(...) for that side`;

/* ------------------------------------------------------------------ binding identity */

/**
 * The id a new binding gets: the component's id, then a numeric suffix if it is taken.
 * Two bindings for one component is an idiom, not an error (the reference project
 * binds `ReadingNode` twice, one binding per logger family), so a suffix is expected.
 */
export function bindingIdFor(componentId: string, taken: Iterable<string>): string {
  const used = new Set(taken);
  const desired = `${componentId}_binding`;
  if (!used.has(desired)) return desired;
  for (let n = 2; n < 10_000; n += 1) {
    const candidate = `${componentId}_binding_${n}`;
    if (!used.has(candidate)) return candidate;
  }
  return `${desired}_${Date.now()}`;
}

/** The debug name, when the author wants the generated module to say something else. */
export const debugNameFor = (binding: Binding): string => binding.debug_name ?? binding.id;

export interface BindableComponent extends ComponentIndexEntry {
  readonly declaration_name: string;
  readonly name: string;
}

/** Only concrete components are bindable — an abstract category raises in the factory. */
export function bindableComponents(ctx: BindingContext): readonly BindableComponent[] {
  const fromIndex = ctx.index?.components ?? [];
  const out: BindableComponent[] = [];
  for (const component of ctx.document.components ?? []) {
    if (component.tier !== "concrete") continue;
    const entry = fromIndex.find((item) => item.id === component.id);
    out.push({
      ...(entry ?? {
        id: component.id,
        kind: component.kind,
        tier: component.tier,
      }),
      id: component.id,
      kind: component.kind,
      tier: "concrete",
      declaration_name: component.declaration_name,
      name: component.name,
      resolved_properties: entry?.resolved_properties ?? resolvedSlots(ctx, component.id),
      endpoint_is_category: entry?.endpoint_is_category,
    });
  }
  return out;
}

export const propertiesOf = (component: { readonly properties?: readonly Property[] } | null): readonly Property[] =>
  component?.properties ?? [];

/** Does this expression read a single logical source? `relational/planner.py` insists. */
export function sourcesRead(expression: Expression | null | undefined): string[] {
  const found: string[] = [];
  const walk = (node: Expression | null | undefined) => {
    if (!node) return;
    if (node.kind === "field") {
      if (!found.includes(node.source)) found.push(node.source);
      return;
    }
    if (node.kind === "operation") (node.arguments ?? []).forEach(walk);
  };
  walk(expression ?? null);
  return found;
}

export { inferExpression };
