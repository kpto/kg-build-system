"use client";

/**
 * Endpoint tokens.
 *
 * `source_node=` / `target_node=` are required **exactly when** the component declares
 * that side as a category, and the named component must be concrete and equal to or
 * descending from it — so the control is hidden for a node and for an edge whose
 * declaration already names concrete components, and mandatory otherwise.
 */

import { Chip, Select } from "@/components/ui";
import type { Binding, ProjectDocument } from "@/lib/ir";
import type { BindingContext } from "../logic/context";
import { endpointSides, missingEndpointMessage } from "../logic/rules";
import { withEndpoints } from "../logic/edits";

export interface EndpointTokensProps {
  ctx: BindingContext;
  binding: Binding;
  apply(mutate: (draft: ProjectDocument) => ProjectDocument): void;
}

export function EndpointTokens({ ctx, binding, apply }: EndpointTokensProps) {
  const sides = endpointSides(ctx, binding.component);
  const required = sides.filter((side) => side.required);
  // Nothing required and nothing stated: the declaration names concrete components, so
  // there is no token to author and no control to show.
  if (required.length === 0 && !binding.source && !binding.target) return null;

  return (
    <section className="flex flex-col gap-1.5 border-b border-edge bg-surface px-2.5 py-2" aria-label="endpoint tokens">
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">endpoints</h3>
      {sides.map((side) => {
        const value = side.side === "source" ? binding.source : binding.target;
        if (!side.required && !value) return null;
        return (
          <div key={side.side} className="flex flex-col gap-1">
            <div className="grid grid-cols-[6rem_1fr] items-center gap-2">
              <span className="text-[11px] font-medium uppercase tracking-[0.05em] text-muted">
                {side.side}_node
                {side.required && (
                  <span className="ml-0.5 text-danger" aria-hidden>
                    *
                  </span>
                )}
              </span>
              <Select
                aria-label={`${side.side} endpoint token`}
                value={value ?? ""}
                options={side.options}
                placeholder={side.message ?? "pick a concrete node component"}
                invalid={side.required && !value}
                onChange={(event) => apply((draft) => withEndpoints(draft, binding.id, { [side.side]: event.target.value || null }))}
              />
            </div>
            {side.required && !value && (
              <p role="alert" className="pl-[6rem] text-[11px] text-danger">
                {missingEndpointMessage(side.side, side.category)}
              </p>
            )}
            {!side.required && value && (
              <p className="pl-[6rem] flex items-center gap-1.5 text-[10px] text-faint">
                <Chip tone="ok">optional</Chip>
                the declaration names concrete components, so this token only documents intent
              </p>
            )}
          </div>
        );
      })}
    </section>
  );
}
