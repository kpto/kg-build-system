"use client";

import { useMemo, useState } from "react";

import {
  Button,
  Chip,
  Field,
  IconButton,
  Modal,
  ProblemBadge,
  Select,
  TextInput,
  Toggle,
  Tooltip,
  TypePicker,
} from "@/components/ui";
import type { InspectorProps } from "@/lib/types";
import type { Component, LogicalType, ProjectDocument, Property } from "@/lib/ir";
import { isNullable, typeLabel } from "@/lib/ir";
import {
  categoriesOfKind,
  componentById,
  componentIdFromRef,
  componentRef,
  deleteImpact,
  emptySlot,
  patchComponent,
  removeComponentCascade,
  renameComponent,
  setSlotOptional,
  slotAllowsOptional,
  templatesOfKind,
} from "./logic";

/**
 * The topology component inspector.
 *
 * It edits one thing at a time through `apply`, so the canvas, the problems panel and
 * every other surface follow each edit. The framework rules live in `logic.ts` and are
 * reflected here by construction: the category parent only offers same-kind categories,
 * mixins only same-kind templates, the optional toggle is disabled for a non-nullable
 * slot (the framework needs a nullable type to render `property(default=None)`), and a
 * delete that would orphan bindings asks first and names what dangles.
 */
export function TopologyInspector({ document, ref, problems, onSelectRef, apply }: InspectorProps) {
  const id = componentIdFromRef(ref);
  const component = id ? componentById(document, id) : null;

  if (!id || !component) {
    // The ref stopped resolving (deleted here or in another tab); the shell's fallback
    // inspector renders the "no longer exists" message, so this panel claims nothing.
    return null;
  }

  return (
    <div className="flex min-h-0 flex-col">
      <IdentityHeader component={component} problems={problems} onSelectRef={onSelectRef} />
      <IdentityFields document={document} component={component} apply={apply} />
      <SlotsEditor
        document={document}
        component={component}
        apply={apply}
        onSelectRef={onSelectRef}
        selectedRef={ref}
      />
      <DangerZone document={document} component={component} apply={apply} onSelectRef={onSelectRef} />
    </div>
  );
}

/* ------------------------------------------------------------------------- header */

function IdentityHeader({
  component,
  problems,
  onSelectRef,
}: {
  component: Component;
  problems: InspectorProps["problems"];
  onSelectRef(ref: string | null): void;
}) {
  const ref = componentRef(component.id);
  return (
    <div className="flex flex-col gap-1.5 border-b border-edge p-2.5">
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-[13px] font-semibold text-ink">{component.name}</p>
          <p className="truncate font-mono text-[10px] uppercase tracking-[0.06em] text-faint">
            {component.kind} · {component.tier}
          </p>
        </div>
        <ProblemBadge problems={problems} ref={ref} />
      </div>
      <button
        type="button"
        onClick={() => onSelectRef(ref)}
        className="w-full truncate rounded border border-edge bg-raised px-1.5 py-1 text-left font-mono text-[10px] text-info hover:border-edge-strong"
        title={ref}
      >
        {ref}
      </button>
    </div>
  );
}

/* ----------------------------------------------------------------------- identity */

function IdentityFields({
  document,
  component,
  apply,
}: {
  document: ProjectDocument;
  component: Component;
  apply: InspectorProps["apply"];
}) {
  const [nameDraft, setNameDraft] = useState<string | null>(null);
  const categories = useMemo(
    () => categoriesOfKind(document, component.kind),
    [document, component.kind],
  );
  const allTemplates = useMemo(
    () => templatesOfKind(document, component.kind),
    [document, component.kind],
  );
  const inherited = useMemo(
    () => collectInherited(component, document),
    [component, document],
  );

  const displayName = nameDraft ?? component.name;

  const commitName = () => {
    if (nameDraft !== null && nameDraft.trim() && nameDraft !== component.name) {
      apply((draft) => renameComponent(draft, component.id, nameDraft.trim()));
    }
    setNameDraft(null);
  };

  const mixins = component.mixins ?? [];

  const toggleMixin = (mixinId: string) => {
    const next = mixins.includes(mixinId)
      ? mixins.filter((existing) => existing !== mixinId)
      : [...mixins, mixinId];
    apply((draft) => patchComponent(draft, component.id, { mixins: next }));
  };

  return (
    <div className="flex flex-col gap-2 border-b border-edge p-2.5">
      <Field
        label="display name"
        htmlFor={`name-${component.id}`}
        hint="editing the name keeps the id"
      >
        <TextInput
          id={`name-${component.id}`}
          value={displayName}
          onChange={(event) => setNameDraft(event.target.value)}
          onBlur={commitName}
          onKeyDown={(event) =>
            event.key === "Enter" && (event.target as HTMLInputElement).blur()
          }
        />
      </Field>

      <Field label="semantic label" htmlFor={`label-${component.id}`} hint="the NodeLabel / EdgeLabel text">
        <TextInput
          id={`label-${component.id}`}
          defaultValue={component.label ?? ""}
          key={`label-${component.label ?? ""}`}
          placeholder={component.kind === "edge" ? "HAS_UNIT" : "Site"}
          onBlur={(event) =>
            apply((draft) =>
              patchComponent(draft, component.id, { label: event.target.value.trim() || null }),
            )
          }
        />
      </Field>

      <Field label="description" htmlFor={`desc-${component.id}`} stack>
        <textarea
          id={`desc-${component.id}`}
          rows={2}
          defaultValue={component.description ?? ""}
          key={`desc-${component.description ?? ""}`}
          placeholder="what this component models"
          className="w-full resize-y rounded-md border border-edge bg-raised px-2 py-1 text-[12px] text-ink placeholder:text-faint hover:border-edge-strong focus:border-info"
          onBlur={(event) =>
            apply((draft) =>
              patchComponent(draft, component.id, {
                description: event.target.value.trim() || null,
              }),
            )
          }
        />
      </Field>

      <div className="flex items-center gap-2">
        <span className="w-[6.5rem] shrink-0 truncate text-[11px] font-medium uppercase tracking-[0.06em] text-muted">
          tier
        </span>
        <Chip tone={tierTone(component.tier)} plain>
          {component.tier}
        </Chip>
        <span className="truncate font-mono text-[10px] text-faint">{component.declaration_name}</span>
      </div>

      {component.tier !== "template" && (
        <Field label="category parent" htmlFor={`parent-${component.id}`}>
          <Select
            id={`parent-${component.id}`}
            value={component.parent ?? ""}
            placeholder={component.tier === "concrete" ? "required" : "none (top category)"}
            invalid={component.tier === "concrete" && !component.parent}
            options={categories
              .filter((category) => category.id !== component.id)
              .map((category) => ({ value: category.id, label: category.name }))}
            onChange={(event) =>
              apply((draft) =>
                patchComponent(draft, component.id, { parent: event.target.value || null }),
              )
            }
          />
        </Field>
      )}

      {allTemplates.length > 0 && (
        <div className="flex flex-col gap-1">
          <span className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted">
            mixin templates
          </span>
          <div className="flex flex-wrap gap-1">
            {allTemplates
              .filter((template) => template.id !== component.id)
              .map((template) => (
                <Chip
                  key={template.id}
                  tone="template"
                  active={mixins.includes(template.id)}
                  onClick={() => toggleMixin(template.id)}
                  title={mixins.includes(template.id) ? "remove mix-in" : "add mix-in"}
                >
                  {template.name}
                </Chip>
              ))}
            {mixins.length === 0 && <span className="text-[11px] text-faint">none mixed in</span>}
          </div>
          {inherited.length > 0 && (
            <p className="text-[10px] text-faint">inherits: {inherited.join(", ")}</p>
          )}
        </div>
      )}
    </div>
  );
}

/* -------------------------------------------------------------------------- slots */

function SlotsEditor({
  document,
  component,
  apply,
  onSelectRef,
  selectedRef,
}: {
  document: ProjectDocument;
  component: Component;
  apply: InspectorProps["apply"];
  onSelectRef(ref: string | null): void;
  selectedRef: string;
}) {
  const slots = component.properties ?? [];
  const structs = useMemo(() => structOptions(document), [document]);

  const mutateSlots = (next: readonly Property[]) =>
    apply((draft) => patchComponent(draft, component.id, { properties: next.map(normalize) }));

  const update = (index: number, changes: Partial<Property>) => {
    mutateSlots(slots.map((slot, position) => (position === index ? { ...slot, ...changes } : slot)));
  };

  const addSlot = () => {
    const existing = new Set(slots.map((slot) => slot.name));
    let n = slots.length + 1;
    let name = `slot_${n}`;
    while (existing.has(name)) name = `slot_${(n += 1)}`;
    mutateSlots([...slots, emptySlot(name)]);
  };

  const removeSlot = (index: number) => mutateSlots(slots.filter((_, position) => position !== index));

  return (
    <div className="flex flex-col gap-2 border-b border-edge p-2.5">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
          property slots
        </span>
        <Button size="sm" onClick={addSlot} data-testid="add-slot">
          add slot
        </Button>
      </div>

      {slots.length === 0 && <p className="text-[11px] text-faint">no property slots declared</p>}

      {slots.map((slot, index) => {
        const slotRef = `${componentRef(component.id)}.property.${slot.name}`;
        const nullable = slotAllowsOptional(slot.logical_type);
        return (
          <div
            key={index}
            className={
              slotRef === selectedRef
                ? "rounded-md border border-info/50 p-1.5"
                : "rounded-md border border-edge p-1.5"
            }
          >
            <div className="flex items-center gap-1.5">
              <button type="button" onClick={() => onSelectRef(slotRef)} className="min-w-0 flex-1" title={slotRef}>
                <TextInput
                  aria-label={`slot ${index + 1} name`}
                  mono
                  defaultValue={slot.name}
                  key={`slotname-${index}-${slot.name}`}
                  onBlur={(event) => {
                    const value = event.target.value.trim();
                    if (value && value !== slot.name) update(index, { name: value });
                  }}
                />
              </button>
              <IconButton
                size="sm"
                label={`remove slot ${slot.name}`}
                icon={<span aria-hidden>×</span>}
                onClick={() => removeSlot(index)}
              />
            </div>

            <div className="mt-1.5">
              <TypePicker
                value={slot.logical_type}
                structs={structs}
                onChange={(next: LogicalType) => update(index, { logical_type: next })}
              />
            </div>

            <TextInput
              aria-label={`slot ${slot.name} description`}
              className="mt-1.5"
              defaultValue={slot.description ?? ""}
              key={`slotdesc-${index}-${slot.description ?? ""}`}
              placeholder="description"
              onBlur={(event) => update(index, { description: event.target.value.trim() || null })}
            />

            <div className="mt-1.5 flex items-center justify-between">
              <Tooltip
                content={
                  nullable
                    ? "property(default=None): a binding may leave this slot unfilled"
                    : "only a nullable type can default to None"
                }
              >
                <Toggle
                  label="optional"
                  checked={slot.optional ?? false}
                  disabled={!nullable}
                  onChange={(checked) => update(index, setSlotOptional(slot, checked))}
                />
              </Tooltip>
              <span className="font-mono text-[10px] text-faint">{typeLabel(slot.logical_type)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function normalize(property: Property): Property {
  return property.optional && !isNullable(property.logical_type)
    ? { ...property, optional: false }
    : property;
}

/* --------------------------------------------------------------------- danger zone */

function DangerZone({
  document,
  component,
  apply,
  onSelectRef,
}: {
  document: ProjectDocument;
  component: Component;
  apply: InspectorProps["apply"];
  onSelectRef(ref: string | null): void;
}) {
  const [confirming, setConfirming] = useState(false);
  const impact = useMemo(() => deleteImpact(document, component.id), [document, component.id]);
  const total =
    impact.bindings.length +
    impact.children.length +
    impact.mixinUsers.length +
    impact.endpointUsers.length;

  const doDelete = () => {
    apply((draft) => removeComponentCascade(draft, component.id));
    setConfirming(false);
    onSelectRef(null);
  };

  return (
    <div className="flex flex-col gap-2 p-2.5">
      <Button variant="danger" size="sm" onClick={() => setConfirming(true)} data-testid="delete-component">
        Delete component
      </Button>

      <Modal
        open={confirming}
        onClose={() => setConfirming(false)}
        title={`Delete ${component.name}?`}
        size="sm"
        footer={
          <>
            <Button onClick={() => setConfirming(false)}>Cancel</Button>
            <Button variant="danger" onClick={doDelete} data-testid="confirm-delete">
              {impact.dangling ? "Delete anyway" : "Delete"}
            </Button>
          </>
        }
      >
        {impact.dangling ? (
          <div className="flex flex-col gap-2 text-[12px] text-ink">
            <p className="text-danger">
              Deleting {component.name} touches {total} reference{total === 1 ? "" : "s"} that would
              otherwise dangle:
            </p>
            {impact.bindings.length > 0 && (
              <ImpactList title="bindings removed" ids={impact.bindings.map((binding) => binding.id)} />
            )}
            {impact.children.length > 0 && (
              <ImpactList title="children re-parented" ids={impact.children.map((child) => child.name)} />
            )}
            {impact.mixinUsers.length > 0 && (
              <ImpactList title="dropped from mixins" ids={impact.mixinUsers.map((child) => child.name)} />
            )}
            {impact.endpointUsers.length > 0 && (
              <ImpactList title="edges re-pointed" ids={impact.endpointUsers.map((child) => child.name)} />
            )}
          </div>
        ) : (
          <p className="text-[12px] text-muted">Nothing references this component — it deletes cleanly.</p>
        )}
      </Modal>
    </div>
  );
}

function ImpactList({ title, ids }: { title: string; ids: readonly string[] }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] font-semibold uppercase tracking-[0.06em] text-faint">{title}</span>
      <div className="flex flex-wrap gap-1">
        {ids.map((id) => (
          <Chip key={id} tone="warn">
            {id}
          </Chip>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------------- helpers */

function tierTone(tier: Component["tier"]): "node" | "category" | "template" {
  return tier === "concrete" ? "node" : tier === "category" ? "category" : "template";
}

/** Struct options the slot TypePicker may point at — the document's own structs. */
function structOptions(document: ProjectDocument) {
  const pkg = document.project.package;
  return (document.structs ?? []).map((struct) => ({
    module: `${pkg}.table`,
    qualname: struct.declaration_name,
    label: struct.name,
  }));
}

/** The slot names this component inherits (parent chain + mixins), for the "inherits" hint. */
function collectInherited(component: Component, document: ProjectDocument): string[] {
  const names: string[] = [];
  const seen = new Set<string>();
  const walk = (id: string | null) => {
    if (!id || seen.has(id)) return;
    seen.add(id);
    const parent = componentById(document, id);
    if (!parent) return;
    for (const slot of parent.properties ?? []) names.push(`${slot.name} ← ${parent.name}`);
    walk(parent.parent ?? null);
    for (const mixin of parent.mixins ?? []) walk(mixin);
  };
  walk(component.parent ?? null);
  for (const mixin of component.mixins ?? []) walk(mixin);
  return names;
}
