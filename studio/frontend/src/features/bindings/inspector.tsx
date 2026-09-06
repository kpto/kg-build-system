"use client";

/**
 * The inspector panel for binding refs.
 *
 * The shell owns the dock and registers a generic fallback at priority 0; this panel
 * matches `binding:*` and `binding:<id>.property.<name>` (and the three key refs) at
 * priority 10, so the dock shows what a binding *means* — its stacks, their resulting
 * types against the declared slot, the key rules and the endpoint tokens — instead of
 * a generic entity card.
 *
 * Registering at module load, guarded to the client, keeps the dock able to resolve the
 * panel the first time any area selects a binding ref (the problems panel jumps here,
 * the palette too), not only after this tab has mounted.
 */

import { useEffect } from "react";

import { Chip, ProblemBadge, SeverityMark } from "@/components/ui";
import type { Binding, ProjectDocument } from "@/lib/ir";
import { expressionSummary, typeLabel } from "@/lib/ir";
import type { InspectorProps, Problem } from "@/lib/types";
import { registerInspector } from "@/components/shell/inspectorRegistry";
import { buildBindingContext, resolvedSlots } from "./logic/context";
import { checkKey, checkSlot, endpointSides, keyChecks } from "./logic/rules";
import { inferExpression } from "./logic/typecheck";
import { renderPreview } from "./logic/preview";
import { expressionAt, stackRef, type StackTarget } from "./logic/edits";

const PANEL_ID = "bindings.stack";

export function isBindingRef(ref: string): boolean {
  return /^binding:[a-z][a-z0-9_]*(\.(build_key|source_build_key|target_build_key|property(\.[^s].*)?))?$/.test(ref)
    || /^binding:[a-z][a-z0-9_]*\.property\..+$/.test(ref);
}

function matches(ref: string, document: ProjectDocument): boolean {
  if (!isBindingRef(ref)) return false;
  const id = ref.replace(/^binding:/, "").split(".")[0];
  return (document.bindings ?? []).some((binding) => binding.id === id);
}

function BindingInspector(props: InspectorProps) {
  const { document, ref, problems, onSelectRef, apply } = props;
  const id = ref.replace(/^binding:/, "").split(".")[0];
  const binding = (document.bindings ?? []).find((item) => item.id === id) as Binding | undefined;
  if (!binding) return null;
  const ctx = buildBindingContext(document, null);
  const component = (document.components ?? []).find((item) => item.id === binding.component);
  const slots = resolvedSlots(ctx, binding.component);
  const sides = endpointSides(ctx, binding.component);

  const targets: StackTarget[] = [
    { part: "build_key" },
    ...(binding.kind === "edge"
      ? [{ part: "source_build_key" } as StackTarget, { part: "target_build_key" } as StackTarget]
      : []),
    ...slots.map((slot) => ({ part: "property", name: slot.name }) as StackTarget),
  ];

  return (
    <div className="flex min-h-0 flex-col">
      <div className="flex flex-col gap-1.5 border-b border-edge p-2.5">
        <div className="flex items-start gap-2">
          <div className="min-w-0 flex-1">
            <p className="truncate text-[13px] font-semibold text-ink">{binding.debug_name || binding.id}</p>
            <p className="truncate font-mono text-[10px] uppercase tracking-[0.06em] text-faint">
              {binding.kind} binding · {component?.declaration_name ?? binding.component}
            </p>
          </div>
          <ProblemBadge problems={problems} ref={`binding:${binding.id}`} />
        </div>
        <p className="truncate font-mono text-[10px] text-info">{ref}</p>
        {sides.some((side) => side.required) && (
          <p className="text-[11px] text-warn">
            this component declares a category endpoint — an `endpoint(...)` token is required
          </p>
        )}
        <button
          type="button"
          onClick={() => onSelectRef(ref)}
          className="w-full truncate rounded border border-edge bg-raised px-1.5 py-1 text-left font-mono text-[10px] text-info hover:border-edge-strong"
          title="open this stack in the composer"
        >
          open in composer →
        </button>
      </div>

      <ul className="min-h-0 flex-1 overflow-auto">
        {targets.map((target) => {
          const childRef = stackRef(binding.id, target);
          const expression = expressionAt(binding, target);
          const type = inferExpression(ctx, expression).type;
          const slot = target.part === "property" ? slots.find((item) => item.name === target.name) ?? null : null;
          const problem = slot ? checkSlot(component?.declaration_name ?? binding.component, slot, type) : null;
          const key = target.part !== "property" ? checkKey(target.part, type) : null;
          const childProblems = problems.filter((item) => item.ref === childRef);
          const bad = (problem && !problem.ok) || (key && !key.ok);
          return (
            <li key={childRef} className="border-b border-edge/60">
              <button
                type="button"
                onClick={() => onSelectRef(childRef)}
                aria-current={childRef === ref ? "true" : undefined}
                className="flex w-full flex-col gap-0.5 px-2.5 py-1.5 text-left hover:bg-raised"
              >
                <span className="flex items-center gap-1.5">
                  <span className="w-28 shrink-0 truncate font-mono text-[11px] text-ink">
                    {target.part === "property" ? target.name : target.part}
                  </span>
                  <span className="shrink-0 font-mono text-[10px] text-faint">{type == null ? "—" : typeLabel(type)}</span>
                  {bad && <SeverityMark severity="error" />}
                  {!bad && childProblems.length > 0 && <ProblemBadge problems={childProblems} ref={childRef} compact />}
                </span>
                <span className="truncate font-mono text-[10px] text-relation">
                  {expression ? expressionSummary(expression) : "unfilled"}
                </span>
                {bad && <span className="text-[10px] leading-snug text-danger">{(problem?.message ?? key?.message) || ""}</span>}
              </button>
              {childRef === ref && expression && (
                <pre className="overflow-auto bg-canvas px-2.5 pb-2 font-mono text-[10px] leading-relaxed text-relation">
                  {renderPreview(ctx, expression)}
                </pre>
              )}
            </li>
          );
        })}
      </ul>

      {problems.length > 0 && (
        <ul className="flex shrink-0 flex-col gap-1 border-t border-edge p-2.5">
          {problems.slice(0, 3).map((problem: Problem) => (
            <li key={problem.id} className="flex items-start gap-1.5">
              <SeverityMark severity={problem.severity} />
              <span className="min-w-0 flex-1 text-[11px] leading-snug text-ink">{problem.message}</span>
            </li>
          ))}
        </ul>
      )}

      <div className="flex shrink-0 items-center gap-1.5 border-t border-edge px-2.5 py-1.5">
        <Chip tone="neutral" title="every key is checked scalar + non-null, in that order">
          {keyChecks(binding).length} keys
        </Chip>
        <Chip tone="neutral">{slots.length} slots</Chip>
        <span className="ml-auto text-[10px] text-faint">edits go through the document store</span>
      </div>
    </div>
  );
}

const panel = {
  id: PANEL_ID,
  label: "Binding stack",
  priority: 10,
  matches,
  render: (props: InspectorProps) => <BindingInspector {...props} />,
};

if (typeof window !== "undefined") registerInspector(panel);

/** Also register on mount, so hot reloads and late imports keep the panel available. */
export function useBindingInspectorRegistration(): void {
  useEffect(() => registerInspector(panel), []);
}
