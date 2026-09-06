/**
 * Document edits, all of them rebuilds.
 *
 * Every model in `ir.ts` is frozen on both sides of the wire, so an edit is always
 * "rebuild the part that changed" and every one of these is a pure
 * `(document) => document` handed to `FeatureProps.apply` — optimistic, undoable, and
 * the only way this feature writes.
 *
 * The composer writes `logical_type` values it derived locally with the framework's
 * own rules (`typecheck.ts`): the IR model requires the field, and `ir.normalize`
 * recomputes every one of them on save, so a stale derivation cannot reach the
 * document. Nothing here invents a type that the declarations do not imply.
 */

import type { Binding, Expression, LogicalType, NonNullableLogicalType, ProjectDocument, PropertyBinding } from "@/lib/ir";
import { replaced, sectionItems } from "@/lib/ir";
import type { BindingContext } from "./context";
import { resolvedSlots } from "./context";
import { bindingIdFor } from "./rules";
import { fieldPathType } from "./typecheck";

/* ---------------------------------------------------------------- target addressing */

export type StackTarget =
  | { readonly part: "build_key" }
  | { readonly part: "source_build_key" }
  | { readonly part: "target_build_key" }
  | { readonly part: "property"; readonly name: string };

/** The ref a stack answers to, exactly as `describeRef` and the diagnostics spell it. */
export function stackRef(bindingId: string, target: StackTarget): string {
  return target.part === "property"
    ? `binding:${bindingId}.property.${target.name}`
    : `binding:${bindingId}.${target.part}`;
}

export function targetFromRef(ref: string | null | undefined): { bindingId: string; target: StackTarget } | null {
  const match = /^binding:([a-z][a-z0-9_]*)(?:\.(build_key|source_build_key|target_build_key|property)(?:\.(.+))?)?$/.exec(
    ref ?? "",
  );
  if (!match) return null;
  const bindingId = match[1] as string;
  const part = match[2];
  if (!part) return null;
  if (part === "property") {
    const name = match[3];
    return name ? { bindingId, target: { part: "property", name } } : null;
  }
  return { bindingId, target: { part } as StackTarget };
}

export function findBinding(document: ProjectDocument, id: string): Binding | null {
  return (sectionItems(document, "bindings") as readonly Binding[]).find((item) => item.id === id) ?? null;
}

const expressionAt = (binding: Binding, target: StackTarget): Expression | null => {
  if (target.part === "property") {
    return (binding.properties ?? []).find((item) => item.name === target.name)?.expression ?? null;
  }
  return (binding[target.part] as Expression | null | undefined) ?? null;
};

export { expressionAt };

/** Write one stack, rebuilding only the binding and the slot it fills. */
export function withStackExpression(
  document: ProjectDocument,
  bindingId: string,
  target: StackTarget,
  expression: Expression,
): ProjectDocument {
  const binding = findBinding(document, bindingId);
  if (!binding) return document;
  let next: Binding;
  if (target.part === "property") {
    const properties = [...(binding.properties ?? [])];
    const index = properties.findIndex((item) => item.name === target.name);
    const filled: PropertyBinding = { name: target.name, expression };
    if (index >= 0) properties[index] = filled;
    else properties.push(filled);
    next = { ...binding, properties };
  } else {
    next = { ...binding, [target.part]: expression };
  }
  return replaced(document, "bindings", next);
}

/** Drop a property binding, which the generated record only allows for an optional slot. */
export function withoutProperty(document: ProjectDocument, bindingId: string, name: string): ProjectDocument {
  const binding = findBinding(document, bindingId);
  if (!binding) return document;
  return replaced(document, "bindings", {
    ...binding,
    properties: (binding.properties ?? []).filter((item) => item.name !== name),
  });
}

export function withEndpoints(
  document: ProjectDocument,
  bindingId: string,
  endpoints: { readonly source?: string | null; readonly target?: string | null },
): ProjectDocument {
  const binding = findBinding(document, bindingId);
  if (!binding) return document;
  return replaced(document, "bindings", {
    ...binding,
    ...(endpoints.source !== undefined ? { source: endpoints.source } : {}),
    ...(endpoints.target !== undefined ? { target: endpoints.target } : {}),
  });
}

export function withDebugName(document: ProjectDocument, bindingId: string, debugName: string | null): ProjectDocument {
  const binding = findBinding(document, bindingId);
  if (!binding) return document;
  return replaced(document, "bindings", { ...binding, debug_name: debugName || null });
}

/* -------------------------------------------------------------------- create/delete */

export interface NewBindingSeed {
  readonly component: string;
  readonly source: string;
  readonly path: readonly string[];
  /** Set when the picked field is nullable: the key is wrapped to make it legal. */
  readonly unwrap: boolean;
}

/**
 * A new binding: a concrete component (never a category), a derived unique id, and a
 * `build_key` seeded from a picked scalar field. An edge also gets its two endpoint
 * keys, because `edge_binding` takes all three; the seed is copied and the author
 * re-points each one, which is what the reference project's edge bindings look like.
 */
export function createBinding(ctx: BindingContext, seed: NewBindingSeed): (document: ProjectDocument) => ProjectDocument {
  return (document) => {
    const component = (sectionItems(document, "components") as readonly { id: string; kind: string }[]).find(
      (item) => item.id === seed.component,
    );
    if (!component) return document;
    const taken = sectionItems(document, "bindings").map((item) => (item as Binding).id);
    const declared = fieldPathType(ctx, seed.source, seed.path).type ?? { kind: "unit", name: "str" };
    const field: Expression = { kind: "field", source: seed.source, path: [...seed.path], logical_type: declared };
    // A key may not be nullable, so a nullable column is seeded already unwrapped with
    // `where_present` — the reference project's idiom for every key it builds.
    const key: Expression = seed.unwrap
      ? {
          kind: "operation",
          operator: "where_present",
          arguments: [field],
          parameters: {},
          logical_type: unwrapType(declared),
        }
      : field;
    const binding: Binding = {
      id: bindingIdFor(seed.component, taken),
      kind: component.kind === "edge" ? "edge" : "node",
      component: seed.component,
      debug_name: null,
      build_key: key,
      source_build_key: component.kind === "edge" ? key : null,
      target_build_key: component.kind === "edge" ? key : null,
      source: null,
      target: null,
      properties: [],
      annotations: [],
    };
    return replaced(document, "bindings", binding);
  };
}

export function deleteBinding(document: ProjectDocument, bindingId: string): ProjectDocument {
  return {
    ...document,
    bindings: sectionItems(document, "bindings")
      .map((item) => item as Binding)
      .filter((item) => item.id !== bindingId),
  };
}

/* ------------------------------------------------------------------------- helpers */

const unwrapType = (type: LogicalType): NonNullableLogicalType =>
  type.kind === "nullable" ? type.value : type;

/** Slots a brand new binding still owes, so the list can say "3 slots to fill". */
export const slotsToFill = (ctx: BindingContext, binding: Binding): number =>
  resolvedSlots(ctx, binding.component).length - (binding.properties ?? []).length;
