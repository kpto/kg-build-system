"use client";

import { useMemo, useState } from "react";

import { Button, Field, Modal, Select, TextInput } from "@/components/ui";
import type { ComponentKind, ComponentTier, ProjectDocument } from "@/lib/ir";
import { categoriesOfKind, createComponent, deriveIdentity, type NewComponentSpec } from "./logic";

export interface AddNodeModalProps {
  open: boolean;
  document: ProjectDocument;
  onClose(): void;
  /** Called with the new component ref (and any on-demand category) once created. */
  onCreate(spec: NewComponentSpec): void;
}

const KINDS: readonly { value: ComponentKind; label: string }[] = [
  { value: "node", label: "Node — a vertex" },
  { value: "edge", label: "Edge — a relationship" },
];

const TIERS: readonly { value: ComponentTier; label: string }[] = [
  { value: "concrete", label: "Concrete — bindable" },
  { value: "category", label: "Category — graph parent" },
  { value: "template", label: "Template — mix-in" },
];

/**
 * The add-node flow. It asks for a display name, the kind and the tier — nothing else:
 * `id` and `declaration_name` are derived client-side (mirroring `ids.ts`), and a
 * concrete component is given a category parent the moment it is created, because a
 * concrete without one is a document the backend rejects. When the kind has no category
 * yet the parent field offers "create a new one", so the illegal case is unconstructable.
 */
export function AddNodeModal({ open, document, onClose, onCreate }: AddNodeModalProps) {
  const [displayName, setDisplayName] = useState("");
  const [kind, setKind] = useState<ComponentKind>("node");
  const [tier, setTier] = useState<ComponentTier>("concrete");
  const [parentChoice, setParentChoice] = useState<string>("");
  const [nonce, setNonce] = useState(0);

  const trimmed = displayName.trim();
  const identity = useMemo(() => {
    if (!trimmed) return null;
    try {
      return deriveIdentity(document, trimmed, kind, tier);
    } catch {
      return null;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [document, trimmed, kind, tier, nonce]);

  const categories = useMemo(() => categoriesOfKind(document, kind), [document, kind]);
  const needsParent = tier === "concrete";
  const parentRequiredButMissing = needsParent && categories.length === 0 && parentChoice !== "__new__";

  const reset = () => {
    setDisplayName("");
    setKind("node");
    setTier("concrete");
    setParentChoice("");
  };

  const submit = () => {
    if (!trimmed) return;
    const parentId =
      tier === "template"
        ? null
        : parentChoice === "__new__"
          ? null
          : parentChoice || null;
    onCreate({ displayName: trimmed, kind, tier, parentId });
    reset();
    onClose();
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add a component"
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button
            variant="primary"
            disabled={!trimmed || parentRequiredButMissing}
            onClick={submit}
            data-testid="add-node-create"
          >
            Create {kind}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <Field label="display name" htmlFor="node-display-name" required hint="id and declaration name are derived from this">
          <TextInput
            id="node-display-name"
            autoFocus
            value={displayName}
            placeholder="e.g. Pump Room"
            onChange={(event) => setDisplayName(event.target.value)}
          />
        </Field>

        {identity && (
          <p className="rounded border border-edge bg-raised px-2 py-1 font-mono text-[11px] text-faint">
            id <span className="text-ink">{identity.id}</span> · declaration{" "}
            <span className="text-ink">{identity.declaration_name}</span>
          </p>
        )}

        <div className="grid grid-cols-2 gap-3">
          <Field label="kind" htmlFor="node-kind" stack>
            <Select
              id="node-kind"
              value={kind}
              options={KINDS}
              onChange={(event) => {
                setKind(event.target.value as ComponentKind);
                setParentChoice("");
              }}
            />
          </Field>
          <Field label="tier" htmlFor="node-tier" stack>
            <Select
              id="node-tier"
              value={tier}
              options={TIERS}
              onChange={(event) => {
                setTier(event.target.value as ComponentTier);
                setParentChoice("");
              }}
            />
          </Field>
        </div>

        {tier !== "template" && (
          <Field
            label="category parent"
            htmlFor="node-parent"
            stack
            error={parentRequiredButMissing ? "concrete needs a category parent — create one" : undefined}
            hint={
              needsParent
                ? "the single graph parent this concrete descends from"
                : "optional abstract parent for this category"
            }
          >
            <Select
              id="node-parent"
              value={parentChoice}
              placeholder={needsParent ? "choose a category…" : "none (top category)"}
              options={[
                ...categories.map((category) => ({
                  value: category.id,
                  label: category.name,
                })),
                { value: "__new__", label: needsParent ? "+ create a new category" : "+ create a parent category" },
              ]}
              onChange={(event) => setParentChoice(event.target.value)}
            />
          </Field>
        )}

        {parentChoice === "__new__" && (
          <p className="text-[11px] text-faint">
            A fresh {kind} category (named “unnamed” for a concrete) is added and set as the
            parent{tier === "concrete" ? ` — select it later in the inspector` : ""}.
          </p>
        )}

        <p className="text-[11px] leading-snug text-muted">
          {tier === "template" ? (
            <>
              A template is not drawn on the graph — it reaches no build. It appears in the
              mix-in library beside the canvas, contributes its property slots and
              annotations to whichever components mix it in, and is marked{" "}
              <span className="text-warn">unused</span> until one does.
            </>
          ) : (
            <>
              Position, property slots and description are set after creation in the
              inspector. To relate two nodes, shift-drag from one onto the other.
            </>
          )}
        </p>
      </div>
    </Modal>
  );
}
