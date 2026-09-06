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
import { useSelectionStore } from "@/stores/selectionStore";
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
  const [seed, setSeed] = useState<Record<string, string>>({});
  const pendingIntent = useSelectionStore((state) => state.pendingIntent);
  const takeIntent = useSelectionStore((state) => state.takeIntent);

  // An intent that is set but not yet consumed counts as composing. The caller sets it
  // before switching the tab, so this is true on the very first render here — without
  // it the effect below would win the race and select an arbitrary binding first.
  const requested =
    pendingIntent?.area === "bindings" && pendingIntent.kind === "new-binding" ? pendingIntent : null;
  const composing = creating || requested !== null;

  useEffect(() => {
    if (!requested) return;
    setSeed(requested.seed);
    setCreating(true);
    takeIntent("bindings");
  }, [requested, takeIntent]);

  const parsed = targetFromRef(selectedRef);
  const selectedBindingId = parsed?.bindingId ?? (selectedRef ?? "").replace(/^binding:/, "").split(".")[0] ?? null;
  // While composing there is no active binding: showing `bindings[0]` behind the dialog
  // would name an unrelated binding in the panel the user is meant to be leaving.
  const active: Binding | null =
    bindings.find((binding) => binding.id === selectedBindingId) ?? (composing ? null : bindings[0]) ?? null;

  // Land on something addressable as soon as a binding is chosen, so the inspector,
  // the problems panel and this area all follow one ref.
  useEffect(() => {
    if (composing) return;
    if (!active) return;
    if (parsed && parsed.bindingId === active.id) return;
    if (selectedRef === `binding:${active.id}` || selectedRef === null || !selectedRef?.startsWith("binding:")) {
      onSelectRef(stackRef(active.id, { part: "build_key" }));
    }
  }, [active, composing, parsed, selectedRef, onSelectRef]);

  const selectStack = (bindingId: string, target: StackTarget) => onSelectRef(stackRef(bindingId, target));

  // A manual "new binding" starts blank: reusing the seed left by an earlier jump would
  // silently prefill the key from a projection the user is not binding.
  const startBlank = () => {
    setSeed({});
    setCreating(true);
  };

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
        onCreate={startBlank}
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
        <EmptyBinding onCreate={startBlank} />
      )}

      <NewBindingModal
        ctx={ctx}
        open={creating}
        seed={seed}
        onClose={() => {
          setCreating(false);
          setSeed({});
        }}
        apply={apply}
        onCreated={(bindingId) => {
          setCreating(false);
          setSeed({});
          onSelectRef(stackRef(bindingId, { part: "build_key" }));
        }}
      />
    </div>
  );
}
