"use client";

/**
 * The field table editor — rows of `name · description · type · trust`, not JSON.
 *
 * One row is the unified `Field[T]` descriptor (KG_BUILD_SYSTEM_SPEC §4): a slug name
 * with a live declaration suggestion, an inline description that expands to a
 * textarea, the shared `TypePicker` for the logical type, and the three-state nullability
 * trust. Rows drag to reorder (`@dnd-kit/sortable`). A struct-typed field grows a
 * chevron that drills into its members inline with a breadcrumb path — the drill-in
 * edits the shared struct, so the change reaches every field that references it.
 */

import { useEffect, useId, useState } from "react";
import clsx from "clsx";
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import {
  Button,
  Chip,
  IconButton,
  PlusIcon,
  ProblemBadge,
  TextInput,
  TypePicker,
  ChevronIcon,
  CloseIcon,
} from "@/components/ui";
import { buildRef } from "@/lib/ids";
import {
  isNullable,
  unwrapNullable,
  type DataField,
  type LogicalType,
  type ProjectDocument,
  type Struct,
} from "@/lib/ir";
import { useDocumentStore } from "@/stores/documentStore";
import { useProblemsForRef } from "@/stores/problemStore";
import { useSelectionStore } from "@/stores/selectionStore";
import {
  fieldAffordances,
  resolveStruct,
  reorderFields,
  structModuleMap,
  trustAllowsNonNull,
} from "@/features/contracts/logic";
import {
  addField,
  deleteField,
  makeField,
  makeStruct,
  renameField,
  setFields,
  structFieldType,
  updateField,
} from "@/features/contracts/edit";
import { TrustSegmented } from "./TrustSegmented";

interface FieldTableProps {
  document: ProjectDocument;
  section: "tables" | "structs";
  entityId: string;
  /** The breadcrumb prefix for drill-ins, e.g. `["targets", "attributes"]`. */
  path: readonly string[];
  depth?: number;
}

export function FieldTable({ document, section, entityId, path, depth = 0 }: FieldTableProps) {
  const apply = useDocumentStore((state) => state.apply);
  const entity = (section === "tables" ? document.tables : document.structs)?.find((item) => item.id === entityId);
  const fields = entity?.fields ?? [];
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  if (!entity) return null;

  const commit = (next: ProjectDocument) => apply(() => next);

  const onDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const from = fields.findIndex((field) => field.name === active.id);
    const to = fields.findIndex((field) => field.name === over.id);
    if (from < 0 || to < 0) return;
    commit(setFields(document, section, entityId, reorderFields(fields, from, to)));
  };

  const addPlainField = () => {
    const field = makeField("field", fields.map((item) => item.name));
    commit(addField(document, section, entityId, field));
    useSelectionStore.getState().select(buildRef(section === "tables" ? "table" : "struct", entityId, "field", field.name));
  };

  // Adding a struct-typed field with no struct present must create one to point at.
  const addStructField = () => {
    const { struct, document: withStruct } = makeStruct("record", document);
    const field = makeField(struct.name, fields.map((item) => item.name));
    const typed: DataField = { ...field, logical_type: structFieldType(struct) };
    commit(addField(withStruct, section, entityId, typed));
    useSelectionStore.getState().select(buildRef("struct", struct.id));
  };

  return (
    <div className="flex flex-col gap-1.5">
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
        <SortableContext items={fields.map((field) => field.name)} strategy={verticalListSortingStrategy}>
          <ul className="flex flex-col gap-1">
            {fields.map((field) => (
              <FieldRow
                key={`${path.join(".")}:${field.name}`}
                document={document}
                section={section}
                entityId={entityId}
                field={field}
                path={[...path, field.name]}
                depth={depth}
              />
            ))}
          </ul>
        </SortableContext>
      </DndContext>
      {fields.length === 0 && (
        <p className="rounded border border-dashed border-edge px-2 py-2 text-center text-[11px] text-faint">
          no fields yet — add one below
        </p>
      )}
      <div className="flex items-center gap-1.5 pt-0.5">
        <Button size="sm" icon={<PlusIcon />} onClick={addPlainField}>
          add field
        </Button>
        <Button size="sm" variant="ghost" icon={<PlusIcon />} onClick={addStructField}>
          add struct field
        </Button>
      </div>
    </div>
  );
}

interface FieldRowProps {
  document: ProjectDocument;
  section: "tables" | "structs";
  entityId: string;
  field: DataField;
  path: readonly string[];
  depth: number;
}

function FieldRow({ document, section, entityId, field, path, depth }: FieldRowProps) {
  const apply = useDocumentStore((state) => state.apply);
  const ref = buildRef(section === "tables" ? "table" : "struct", entityId, "field", field.name);
  const problems = useProblemsForRef(ref);
  const [editingDesc, setEditingDesc] = useState(false);
  const [drillOpen, setDrillOpen] = useState(false);
  const [draftName, setDraftName] = useState(field.name);
  const nameInput = useId();

  const commit = (next: ProjectDocument) => apply(() => next);

  useEffect(() => setDraftName(field.name), [field.name]);

  const struct = structOf(document, field.logical_type);
  const affordances = fieldAffordances(field.logical_type);
  const nonNull = !isNullable(field.logical_type);
  const trustWarning =
    nonNull && (field.nullability ?? "defaulted") === "defaulted"
      ? "defaulted cannot claim a non-null type — set declared/enforced or make it nullable"
      : null;

  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: field.name });

  const commitName = () => {
    const trimmed = draftName.trim();
    if (!trimmed || trimmed === field.name) {
      setDraftName(field.name);
      return;
    }
    commit(renameField(document, section, entityId, field.name, trimmed));
  };

  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={clsx("studio-card flex flex-col gap-2 p-2", isDragging && "z-10 opacity-80")}
    >
      <div className="flex min-w-0 items-start gap-2">
        {/* Drag handle: keyboard-focusable, announces the row it moves. */}
        <button
          type="button"
          aria-label={`Reorder field ${field.name}`}
          title="Drag to reorder"
          className="mt-1 shrink-0 cursor-grab rounded p-0.5 text-faint hover:bg-raised hover:text-ink active:cursor-grabbing"
          {...attributes}
          {...listeners}
        >
          <GripIcon />
        </button>

        <div className="flex min-w-0 flex-1 flex-col gap-1.5 sm:flex-row sm:items-center">
          {/* name: a slug input with a live id/declaration_name suggestion */}
          <label htmlFor={nameInput} className="sr-only">
            field name
          </label>
          <div className="flex min-w-0 flex-col">
            <TextInput
              id={nameInput}
              mono
              className="max-w-[12rem]"
              value={draftName}
              onChange={(event) => setDraftName(event.target.value)}
              onBlur={commitName}
              onKeyDown={(event) => {
                if (event.key === "Enter") (event.target as HTMLInputElement).blur();
                if (event.key === "Escape") setDraftName(field.name);
              }}
            />
            {draftName !== field.name && draftName.trim() ? (
              <span className="pl-0.5 font-mono text-[10px] text-info" aria-live="polite">
                → {draftName.trim().replace(/[^a-z0-9_]+/g, "_").toLowerCase()}
              </span>
            ) : null}
          </div>

          {/* type: the shared TypePicker, offering structs that exist in this document */}
          <div className="min-w-0 flex-1">
            <TypePicker
              value={field.logical_type}
              structs={structOptions(document)}
              onChange={(next: LogicalType) => commit(updateField(document, section, entityId, field.name, { logical_type: next }))}
            />
          </div>

          {/* nullability trust: three-state segmented control */}
          <div className="shrink-0">
            <TrustSegmented
              idPrefix={`trust-${entityId}-${field.name}`}
              value={field.nullability}
              warning={trustAllowsNonNull(field.logical_type, field.nullability ?? "defaulted") ? null : trustWarning}
              onChange={(next) => commit(updateField(document, section, entityId, field.name, { nullability: next }))}
            />
          </div>

          <div className="flex shrink-0 items-center gap-1">
            <ProblemBadge problems={problems} ref={ref} compact />
            {struct && (
              <IconButton
                size="sm"
                label={drillOpen ? "Hide struct members" : `Show ${struct.declaration_name} members`}
                active={drillOpen}
                icon={<ChevronIcon size={13} open={drillOpen} />}
                onClick={() => setDrillOpen((open) => !open)}
              />
            )}
            <IconButton
              size="sm"
              label={`Delete field ${field.name}`}
              icon={<CloseIcon size={13} />}
              onClick={() => commit(deleteField(document, section, entityId, field.name))}
            />
          </div>
        </div>
      </div>

      {/* description: inline, expands to a textarea */}
      <div className="pl-6">
        {editingDesc ? (
          <div className="flex flex-col gap-1">
            <textarea
              autoFocus
              defaultValue={field.description ?? ""}
              rows={3}
              aria-label="field description"
              className="w-full resize-y rounded-md border border-edge bg-raised px-2 py-1 text-[12px] text-ink focus:border-info"
              placeholder="What this field means — shown to every reader of the contract."
              onBlur={(event) => {
                commit(updateField(document, section, entityId, field.name, { description: event.target.value || null }));
                setEditingDesc(false);
              }}
            />
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setEditingDesc(true)}
            className="w-full truncate rounded px-1 py-0.5 text-left text-[12px] hover:bg-raised"
          >
            {field.description ? (
              <span className="text-muted">{field.description}</span>
            ) : (
              <span className="italic text-faint">add description…</span>
            )}
          </button>
        )}
        {affordances.length > 0 && (
          <p className="pl-1 pt-0.5 font-mono text-[10px] text-faint">usable as: {affordances.join(" · ")}</p>
        )}
      </div>

      {/* nested struct drill-in with breadcrumb path */}
      {struct && drillOpen && (
        <StructDrillIn document={document} struct={struct} path={path} depth={depth} />
      )}
    </li>
  );
}

interface StructDrillInProps {
  document: ProjectDocument;
  struct: Struct;
  path: readonly string[];
  depth: number;
}

function StructDrillIn({ document, struct, path, depth }: StructDrillInProps) {
  const apply = useDocumentStore((state) => state.apply);
  const structRef = buildRef("struct", struct.id);
  return (
    <div className="ml-6 flex flex-col gap-1.5 border-l-2 border-edge pl-2.5">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="font-mono text-[10px] text-faint" aria-label="breadcrumb path">
          {path.join(" ▸ ")}
        </span>
        <Chip tone="node" title={struct.declaration_name}>
          {`${(struct.fields ?? []).length} members · ${struct.declaration_name}`}
        </Chip>
        <div className="ml-auto flex items-center gap-1.5">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => useSelectionStore.getState().selectAndReveal(structRef)}
          >
            edit struct
          </Button>
          <MakeStructFromSelection document={document} struct={struct} onMade={(next) => apply(() => next)} />
        </div>
      </div>
      {/* Members edit the shared struct, so a change reaches every field that points here. */}
      <FieldTable document={document} section="structs" entityId={struct.id} path={path} depth={depth + 1} />
    </div>
  );
}

/**
 * "Make struct from selection": lift the current struct's members into a fresh named
 * struct declaration and repoint this field at it — the shape stays, the identity is
 * now reusable across other fields.
 */
function MakeStructFromSelection({
  document,
  struct,
  onMade,
}: {
  document: ProjectDocument;
  struct: Struct;
  onMade(next: ProjectDocument): void;
}) {
  const [open, setOpen] = useState(false);
  const [label, setLabel] = useState("");
  if (!open) {
    return (
      <Button size="sm" variant="ghost" onClick={() => setOpen(true)} disabled={(struct.fields?.length ?? 0) === 0}>
        make struct from selection
      </Button>
    );
  }
  return (
    <div className="flex items-center gap-1">
      <TextInput
        autoFocus
        mono
        placeholder="new struct name"
        className="max-w-[10rem]"
        value={label}
        onChange={(event) => setLabel(event.target.value)}
      />
      <Button
        size="sm"
        variant="primary"
        disabled={!label.trim()}
        onClick={() => {
          const { struct: fresh, document: withStruct } = makeStruct(label, document);
          const moved: ProjectDocument = {
            ...withStruct,
            structs: withStruct.structs?.map((item) => (item.id === fresh.id ? { ...item, fields: struct.fields ?? [] } : item)),
          };
          onMade(moved);
          useSelectionStore.getState().selectAndReveal(buildRef("struct", fresh.id));
          setOpen(false);
          setLabel("");
        }}
      >
        create
      </Button>
      <IconButton size="sm" label="Cancel" icon={<CloseIcon size={12} />} onClick={() => setOpen(false)} />
    </div>
  );
}

/* ---------------------------------------------------------------------- helpers */

/** The struct a field's type reaches through (nullable/array unwrapped, declared only). */
function structOf(document: ProjectDocument, type: LogicalType): Struct | null {
  let value = unwrapNullable(type);
  if (value.kind === "array") value = unwrapNullable(value.item);
  return resolveStruct(document, value);
}

/** Structs the picker may reference, using each struct's referenced module spelling. */
function structOptions(document: ProjectDocument) {
  const modules = structModuleMap(document);
  return (document.structs ?? []).map((struct) => ({
    module: modules[struct.declaration_name] ?? "",
    qualname: struct.declaration_name,
    label: struct.name,
  }));
}

function GripIcon() {
  return (
    <svg viewBox="0 0 24 24" width={13} height={13} aria-hidden className="shrink-0" fill="currentColor">
      <circle cx="9" cy="6" r="1.4" />
      <circle cx="15" cy="6" r="1.4" />
      <circle cx="9" cy="12" r="1.4" />
      <circle cx="15" cy="12" r="1.4" />
      <circle cx="9" cy="18" r="1.4" />
      <circle cx="15" cy="18" r="1.4" />
    </svg>
  );
}
