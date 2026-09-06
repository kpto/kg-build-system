"use client";

/**
 * The centre of the Bindings tab: the stack for one key or property slot.
 *
 * It composes the composer with everything a binding has to settle around the stack —
 * the endpoint tokens the declaration demands, the slot tabs the author moves between,
 * and the generated-code preview — and it is the only place this feature writes.
 */

import { useEffect, useMemo, useState } from "react";

import { Chip, EmptyState, ProblemBadge } from "@/components/ui";
import type { Binding, ProjectDocument } from "@/lib/ir";
import { typeLabel } from "@/lib/ir";
import type { AuthoringIndex, Problem } from "@/lib/types";
import { buildBindingContext, resolvedSlots } from "../logic/context";
import { slotFor } from "../logic/rules";
import { expressionAt, stackRef, targetFromRef, type StackTarget } from "../logic/edits";
import { EndpointTokens } from "./EndpointTokens";
import { StackComposer } from "./StackComposer";

export interface BindingEditorProps {
  document: ProjectDocument;
  index: AuthoringIndex | null;
  binding: Binding;
  selectedRef: string | null;
  problems: readonly Problem[];
  onSelectRef(ref: string | null): void;
  apply(mutate: (draft: ProjectDocument) => ProjectDocument): void;
  onDelete(bindingId: string): void;
}

export function BindingEditor({
  document,
  index,
  binding,
  selectedRef,
  problems,
  onSelectRef,
  apply,
  onDelete,
}: BindingEditorProps) {
  const ctx = useMemo(() => buildBindingContext(document, index), [document, index]);
  const parsed = targetFromRef(selectedRef);
  const slots = useMemo(() => resolvedSlots(ctx, binding.component), [ctx, binding.component]);
  const component = (document.components ?? []).find((item) => item.id === binding.component) ?? null;

  const fallback: StackTarget = binding.build_key ? { part: "build_key" } : { part: "property", name: slots[0]?.name ?? "name" };
  const target: StackTarget = parsed && parsed.bindingId === binding.id ? parsed.target : fallback;
  const ref = stackRef(binding.id, target);
  const slot = target.part === "property" ? slotFor(ctx, binding.component, target.name) : null;
  const [showAllSlots, setShowAllSlots] = useState(false);

  useEffect(() => setShowAllSlots(false), [binding.id]);

  const targets: StackTarget[] = [
    { part: "build_key" },
    ...(binding.kind === "edge" ? [{ part: "source_build_key" } as StackTarget, { part: "target_build_key" } as StackTarget] : []),
    ...slots.map((item) => ({ part: "property", name: item.name }) as StackTarget),
  ];
  const visible = showAllSlots ? targets : targets.filter((item) => item.part !== "property" || expressionAt(binding, item) != null || !isFilled(binding, item));

  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col">
      <header className="flex shrink-0 flex-wrap items-center gap-2 border-b border-edge px-2.5 py-1.5">
        <span className="truncate text-[13px] font-semibold text-ink">{binding.debug_name || binding.id}</span>
        <Chip tone={binding.kind === "edge" ? "relation" : "node"}>{component?.declaration_name ?? binding.component}</Chip>
        <ProblemBadge problems={problems.filter((problem) => (problem.ref ?? "").startsWith(`binding:${binding.id}`))} ref={`binding:${binding.id}`} />
        <span className="ml-auto flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => onDelete(binding.id)}
            className="rounded border border-edge px-1.5 py-0.5 text-[10px] text-muted hover:border-danger hover:text-danger"
          >
            delete binding
          </button>
        </span>
      </header>

      <nav
        aria-label="stacks in this binding"
        className="flex shrink-0 flex-wrap items-center gap-1 border-b border-edge bg-canvas px-2 py-1"
      >
        {visible.map((item) => {
          const itemRef = stackRef(binding.id, item);
          const active = itemRef === ref;
          const label = item.part === "property" ? item.name : item.part;
          const slotItem = item.part === "property" ? slotFor(ctx, binding.component, item.name) : null;
          const filled = expressionAt(binding, item) != null;
          const problemsHere = problems.filter((problem) => problem.ref === itemRef);
          return (
            <button
              key={itemRef}
              type="button"
              onClick={() => onSelectRef(itemRef)}
              aria-current={active ? "true" : undefined}
              title={slotItem ? `${label} · ${typeLabel(slotItem.logical_type)}` : label}
              className={[
                "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 font-mono text-[11px]",
                active ? "border-info bg-info/15 text-ink" : "border-edge bg-raised text-muted hover:border-edge-strong hover:text-ink",
                !filled && item.part === "property" ? "border-dashed" : "",
              ].join(" ")}
            >
              {label}
              {slotItem && <span className="text-[9px] text-faint">{typeLabel(slotItem.logical_type)}</span>}
              {problemsHere.length > 0 && <ProblemBadge problems={problemsHere} ref={itemRef} compact />}
            </button>
          );
        })}
        {targets.length > visible.length && (
          <button
            type="button"
            onClick={() => setShowAllSlots(true)}
            className="rounded border border-dashed border-edge px-1.5 py-0.5 font-mono text-[10px] text-faint hover:text-ink"
          >
            + {targets.length - visible.length} unfilled
          </button>
        )}
      </nav>

      <EndpointTokens ctx={ctx} binding={binding} apply={apply} />

      <StackComposer
        key={ref}
        ctx={ctx}
        binding={binding}
        target={target}
        slot={slot}
        componentName={component?.declaration_name ?? binding.component}
        operators={index?.operators ?? []}
        problems={problems.filter((problem) => problem.ref === ref)}
        apply={apply}
      />
    </section>
  );
}

function isFilled(binding: Binding, target: StackTarget): boolean {
  return expressionAt(binding, target) != null;
}

export function EmptyBinding({ onCreate }: { onCreate(): void }) {
  return (
    <EmptyState
      className="h-full"
      title="No binding selected"
      body="Pick a component on the left to compose its key and property stacks, or create a new binding."
      actions={
        <button
          type="button"
          onClick={onCreate}
          className="rounded-md border border-info/60 bg-info/15 px-2 py-1 text-[12px] text-ink hover:bg-info/25"
        >
          + new binding
        </button>
      }
    />
  );
}
