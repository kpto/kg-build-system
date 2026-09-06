"use client";

/**
 * The binding list: every concrete component with its bindings, grouped node / edge.
 *
 * A category or template is never listed — `binding/factories.py` refuses one
 * ("target must be a concrete node component") — and a component with two bindings is
 * normal, because core aggregates the results of two producers into one entity.
 */

import { Card, Chip, EmptyState, Panel, ProblemBadge } from "@/components/ui";
import type { Binding } from "@/lib/ir";
import type { Problem, ResolvedProperty } from "@/lib/types";
import type { BindingContext } from "../logic/context";
import { bindableComponents, unboundSlots } from "../logic/rules";
import { stackRef, type StackTarget } from "../logic/edits";

export interface BindingListProps {
  ctx: BindingContext;
  bindings: readonly Binding[];
  problems: readonly Problem[];
  activeBindingId: string | null;
  activeRef: string | null;
  onSelectStack(bindingId: string, target: StackTarget): void;
  onSelectBinding(bindingId: string): void;
  onCreate(): void;
}

export function BindingList({
  ctx,
  bindings,
  problems,
  activeBindingId,
  activeRef,
  onSelectStack,
  onSelectBinding,
  onCreate,
}: BindingListProps) {
  const components = bindableComponents(ctx);
  const byRef = indexProblems(problems);

  return (
    <Panel
      title="Bindings"
      subtitle={`${bindings.length} for ${components.length} components`}
      actions={
        <button
          type="button"
          onClick={onCreate}
          className="rounded-md border border-info/60 bg-info/15 px-1.5 py-0.5 text-[11px] font-medium text-ink hover:bg-info/25"
        >
          + new
        </button>
      }
      className="w-[19rem] shrink-0 border-r border-edge"
      padded={false}
    >
      {components.length === 0 ? (
        <EmptyState
          title="No concrete components yet"
          body="A binding always names a concrete component. Declare one in Topology first."
        />
      ) : (
        <div className="flex flex-col gap-3 p-2">
          {(["node", "edge"] as const).map((kind) => {
            const group = components.filter((component) => component.kind === kind);
            if (group.length === 0) return null;
            return (
              <section key={kind} className="flex flex-col gap-1.5">
                <h3 className="px-0.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
                  {kind} bindings
                </h3>
                {group.map((component) => (
                  <ComponentGroup
                    key={component.id}
                    ctx={ctx}
                    componentId={component.id}
                    title={component.declaration_name}
                    bindings={bindings.filter((binding) => binding.component === component.id)}
                    byRef={byRef}
                    activeBindingId={activeBindingId}
                    activeRef={activeRef}
                    onSelectStack={onSelectStack}
                    onSelectBinding={onSelectBinding}
                  />
                ))}
              </section>
            );
          })}
        </div>
      )}
    </Panel>
  );
}

interface GroupProps {
  ctx: BindingContext;
  componentId: string;
  title: string;
  bindings: readonly Binding[];
  byRef: Record<string, Problem[]>;
  activeBindingId: string | null;
  activeRef: string | null;
  onSelectStack(bindingId: string, target: StackTarget): void;
  onSelectBinding(bindingId: string): void;
}

function ComponentGroup({
  ctx,
  componentId,
  title,
  bindings,
  byRef,
  activeBindingId,
  activeRef,
  onSelectStack,
  onSelectBinding,
}: GroupProps) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1.5 px-0.5 pt-0.5">
        <span className="truncate font-mono text-[11px] text-faint">{title}</span>
        {bindings.length > 1 && (
          <Chip tone="info" title="Two bindings for one component is the idiom: core aggregates them.">
            {bindings.length}
          </Chip>
        )}
        {bindings.length === 0 && <span className="text-[11px] text-danger">no binding</span>}
      </div>
      {bindings.map((binding) => {
        const owed = unboundSlots(ctx, binding);
        const active = binding.id === activeBindingId;
        const problems = byRef[`binding:${binding.id}`] ?? [];
        return (
          <Card
            key={binding.id}
            as="li"
            selected={active}
            onSelect={() => onSelectBinding(binding.id)}
            className={active ? "" : "opacity-95"}
            header={
              <div className="flex items-center gap-1.5">
                <span className="min-w-0 flex-1 truncate text-[12px] font-medium text-ink">
                  {binding.debug_name || binding.id}
                </span>
                <ProblemBadge problems={problems} ref={`binding:${binding.id}`} compact />
              </div>
            }
          >
            <SlotRows
              ctx={ctx}
              binding={binding}
              owed={owed}
              byRef={byRef}
              activeRef={activeRef}
              onSelectStack={onSelectStack}
            />
          </Card>
        );
      })}
    </div>
  );
}

function SlotRows({
  ctx,
  binding,
  owed,
  byRef,
  activeRef,
  onSelectStack,
}: {
  ctx: BindingContext;
  binding: Binding;
  owed: readonly ResolvedProperty[];
  byRef: Record<string, Problem[]>;
  activeRef: string | null;
  onSelectStack(bindingId: string, target: StackTarget): void;
}) {
  const owedNames = new Set(owed.map((slot) => slot.name));
  const targets: { target: StackTarget; label: string; bound: boolean }[] = [
    { target: { part: "build_key" }, label: "build_key", bound: Boolean(binding.build_key) },
  ];
  if (binding.kind === "edge") {
    targets.push(
      { target: { part: "source_build_key" }, label: "source_key", bound: Boolean(binding.source_build_key) },
      { target: { part: "target_build_key" }, label: "target_key", bound: Boolean(binding.target_build_key) },
    );
  }
  for (const slot of bindingsToSlots(ctx, binding)) {
    targets.push({
      target: { part: "property", name: slot },
      label: slot,
      bound: (binding.properties ?? []).some((item) => item.name === slot),
    });
  }
  return (
    <ul className="flex flex-wrap gap-1">
      {targets.map(({ target, label, bound }) => {
        const ref = stackRef(binding.id, target);
        const problems = byRef[ref] ?? [];
        const missing = target.part === "property" && owedNames.has(label);
        return (
          <li key={ref}>
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                onSelectStack(binding.id, target);
              }}
              aria-current={activeRef === ref ? "true" : undefined}
              title={ref}
              className={[
                "inline-flex items-center gap-1 rounded border px-1 py-0.5 font-mono text-[10px]",
                activeRef === ref ? "border-info text-ink" : "border-edge hover:border-edge-strong",
                missing ? "bg-warn/10 text-warn" : bound ? "bg-raised text-muted" : "bg-raised text-faint",
              ].join(" ")}
            >
              <span aria-hidden className={bound && !missing ? "text-ok" : "text-faint"}>
                {bound && !missing ? "●" : "○"}
              </span>
              {label}
              {problems.length > 0 && <ProblemBadge problems={problems} ref={ref} compact />}
            </button>
          </li>
        );
      })}
    </ul>
  );
}

/** Every slot the binding could fill: what it fills plus what it owes. */
function bindingsToSlots(ctx: BindingContext, binding: Binding): string[] {
  const names = new Set<string>((binding.properties ?? []).map((item) => item.name));
  for (const slot of unboundSlots(ctx, binding)) names.add(slot.name);
  for (const slot of ctx.index?.components?.find((item) => item.id === binding.component)?.resolved_properties ?? []) {
    names.add(slot.name);
  }
  return [...names];
}

function indexProblems(problems: readonly Problem[]): Record<string, Problem[]> {
  const map: Record<string, Problem[]> = {};
  for (const problem of problems) {
    if (!problem.ref) continue;
    (map[problem.ref] ??= []).push(problem);
    const entity = problem.ref.split(".").slice(0, 2).join(".");
    if (entity !== problem.ref) (map[entity] ??= []).push(problem);
  }
  return map;
}
