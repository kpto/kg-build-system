"use client";

/**
 * Bindings — the expression-stack composer.
 *
 * The shell hands this area `FeatureProps`; everything it renders is derived from the
 * document plus the authoring index, and every edit goes through `apply`, so a stack
 * composed here is byte-for-byte an edit of `project.ir.json` and the UI follows a
 * hand-edited document the same way.
 *
 * Layout: the binding list on the left, the stack for the selected key or property
 * slot in the centre. The inspector panel for `binding:*` refs is registered by
 * `inspector.tsx`, imported here so the shell can resolve it.
 */

import { useEffect, useMemo, useState } from "react";

import type { Binding } from "@/lib/ir";
import type { FeatureProps } from "@/lib/types";
import { buildBindingContext } from "./logic/context";
import { stackRef, targetFromRef, type StackTarget } from "./logic/edits";
import { BindingList } from "./components/BindingList";
import { BindingEditor, EmptyBinding } from "./components/BindingEditor";
import { NewBindingModal } from "./components/NewBindingModal";
import "./inspector";

export default function BindingsFeature({ document, index, problems, selectedRef, onSelectRef, apply }: FeatureProps) {
  const ctx = useMemo(() => buildBindingContext(document, index), [document, index]);
  const bindings = useMemo(() => (document.bindings ?? []) as Binding[], [document]);
  const [creating, setCreating] = useState(false);

  const parsed = targetFromRef(selectedRef);
  const selectedBindingId = parsed?.bindingId ?? (selectedRef ?? "").replace(/^binding:/, "").split(".")[0] ?? null;
  const active: Binding | null =
    bindings.find((binding) => binding.id === selectedBindingId) ?? bindings[0] ?? null;

  // Land on something addressable as soon as a binding is chosen, so the inspector,
  // the problems panel and this area all follow one ref.
  useEffect(() => {
    if (!active) return;
    if (parsed && parsed.bindingId === active.id) return;
    if (selectedRef === `binding:${active.id}` || selectedRef === null || !selectedRef?.startsWith("binding:")) {
      onSelectRef(stackRef(active.id, { part: "build_key" }));
    }
  }, [active, parsed, selectedRef, onSelectRef]);

  const selectStack = (bindingId: string, target: StackTarget) => onSelectRef(stackRef(bindingId, target));

  return (
    <div className="flex min-h-0 flex-1">
      <BindingList
        ctx={ctx}
        bindings={bindings}
        problems={problems}
        activeBindingId={active?.id ?? null}
        activeRef={selectedRef}
        onSelectStack={selectStack}
        onSelectBinding={(bindingId) => onSelectRef(stackRef(bindingId, { part: "build_key" }))}
        onCreate={() => setCreating(true)}
      />

      {active ? (
        <BindingEditor
          document={document}
          index={index}
          binding={active}
          selectedRef={selectedRef}
          problems={problems}
          onSelectRef={onSelectRef}
          apply={apply}
          onDelete={(bindingId) => {
            apply((draft) => ({ ...draft, bindings: (draft.bindings ?? []).filter((item) => item.id !== bindingId) }));
            onSelectRef(null);
          }}
        />
      ) : (
        <EmptyBinding onCreate={() => setCreating(true)} />
      )}

      <NewBindingModal
        ctx={ctx}
        open={creating}
        onClose={() => setCreating(false)}
        apply={apply}
        onCreated={(bindingId) => onSelectRef(stackRef(bindingId, { part: "build_key" }))}
      />
    </div>
  );
}
