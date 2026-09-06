"use client";

import clsx from "clsx";

import { Chip, EmptyState, ProblemBadge, RowButton, SeverityMark, TypePicker } from "@/components/ui";
import { parseRef, refLabel } from "@/lib/ids";
import { describeRef, SECTION_BY_KIND } from "@/lib/ir";
import type { LogicalType, ProjectDocument } from "@/lib/ir";
import type { InspectorProps, Problem } from "@/lib/types";
import { useProblemStore } from "@/stores/problemStore";

/**
 * The shell's fallback inspector.
 *
 * It renders the ref's summary from `describeRef`, its children with per-child
 * badges, and — when the ref addresses a typed part (a field or a property slot) —
 * the type picker that edits it. A feature registers its own panel to replace it.
 */
export function EntityInspector({ document, ref, problems, onSelectRef, apply }: InspectorProps) {
  const summary = describeRef(document, ref);
  const byRefIndex = useProblemStore((state) => state.byRefIndex);

  if (!summary) {
    return (
      <EmptyState
        title="Nothing selected"
        body={
          ref
            ? `${ref} no longer resolves in the document — it was probably deleted, here or in another tab.`
            : "Select an entity in a feature area, or press / to search the document."
        }
      />
    );
  }

  const parsed = parseRef(ref);
  const typed = typedTarget(document, ref);

  return (
    <div className="flex min-h-0 flex-col">
      <div className="flex flex-col gap-1.5 border-b border-edge p-2.5">
        <div className="flex items-start gap-2">
          <div className="min-w-0 flex-1">
            <p className="truncate text-[13px] font-semibold text-ink">{summary.title}</p>
            <p className="truncate font-mono text-[10px] uppercase tracking-[0.06em] text-faint">
              {summary.kind}
            </p>
          </div>
          <ProblemBadge problems={problems} ref={ref} />
        </div>
        <RowButton
          onActivate={() => onSelectRef(summary.ref)}
          className="w-full truncate rounded border border-edge bg-raised px-1.5 py-1 text-left font-mono text-[10px] text-info hover:border-edge-strong"
          title={`${summary.ref}\nselect the whole entity`}
        >
          {summary.ref}
        </RowButton>
        {summary.description && (
          <p className="text-[12px] leading-relaxed text-muted">{summary.description}</p>
        )}
        {summary.detail && <p className="font-mono text-[11px] text-faint">{summary.detail}</p>}
      </div>

      {typed && (
        <div className="flex flex-col gap-2 border-b border-edge p-2.5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
            {typed.label}
          </p>
          <TypePicker
            id="inspector-type"
            value={typed.type}
            structs={structOptions(document)}
            onChange={(next: LogicalType) => apply((draft) => withTypeAtRef(draft, ref, next))}
          />
        </div>
      )}

      {parsed?.part && parsed.name && (
        <PartProblems problems={problems} onSelectRef={onSelectRef} />
      )}

      {summary.children.length > 0 && (
        <div className="min-h-0 flex-1 overflow-auto">
          <p className="px-2.5 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
            Parts
          </p>
          <ul>
            {summary.children.map((child) => {
              const childProblems = byRefIndex[child.ref] ?? [];
              const active = child.ref === ref;
              return (
                <li key={child.ref}>
                  <RowButton
                    onActivate={() => onSelectRef(child.ref)}
                    active={active}
                    className={clsx(
                      "flex w-full items-center gap-2 border-b border-edge/50 px-2.5 py-1 text-left hover:bg-raised",
                      active && "bg-raised",
                    )}
                  >
                    <span className="w-28 shrink-0 truncate font-mono text-[11px] text-ink">
                      {child.label}
                    </span>
                    <span
                      className={clsx(
                        "min-w-0 flex-1 truncate font-mono text-[11px]",
                        child.kind === "expression" ? "text-relation" : "text-muted",
                      )}
                    >
                      {child.detail}
                    </span>
                    <ProblemBadge problems={childProblems} ref={child.ref} compact />
                  </RowButton>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

function PartProblems({
  problems,
  onSelectRef,
}: {
  problems: Problem[];
  onSelectRef(ref: string | null): void;
}) {
  if (problems.length === 0) return null;
  return (
    <ul className="flex flex-col gap-1 border-b border-edge p-2.5">
      {problems.map((problem) => (
        <li key={problem.id} className="flex flex-col gap-1">
          <span className="flex items-start gap-1.5">
            <SeverityMark severity={problem.severity} />
            <span className="min-w-0 flex-1 text-[11px] leading-snug text-ink">
              {problem.message}
            </span>
          </span>
          {problem.ref && (
            <Chip
              tone="neutral"
              className="max-w-full self-start"
              onClick={() => onSelectRef(problem.ref ?? null)}
              title={problem.ref}
            >
              {refLabel(problem.ref)}
            </Chip>
          )}
        </li>
      ))}
    </ul>
  );
}

/* ------------------------------------------------------------------ type editing */

/** Struct references the picker may point at, from this document's own structs. */
export function structOptions(document: ProjectDocument) {
  const pkg = document.project.package;
  return (document.structs ?? []).map((struct) => ({
    module: `${pkg}.table`,
    qualname: struct.declaration_name,
    label: struct.name,
  }));
}

interface TypedTarget {
  readonly label: string;
  readonly type: LogicalType;
}

/** The logical type a part-ref addresses, if it addresses one. */
export function typedTarget(
  document: ProjectDocument,
  ref: string | null,
): TypedTarget | null {
  const parsed = parseRef(ref);
  if (!parsed?.part || !parsed.name) return null;
  const section = SECTION_BY_KIND[parsed.kind];

  if (parsed.part === "field" && (section === "tables" || section === "structs")) {
    for (const item of document[section] ?? []) {
      if (item.id !== parsed.id) continue;
      const field = (item.fields ?? []).find((candidate) => candidate.name === parsed.name);
      return field
        ? { label: `${item.declaration_name}.${field.name}`, type: field.logical_type }
        : null;
    }
  }
  if (parsed.part === "field" && section === "annotation_types") {
    for (const item of document.annotation_types ?? []) {
      if (item.id !== parsed.id) continue;
      const field = (item.fields ?? []).find((candidate) => candidate.name === parsed.name);
      return field
        ? { label: `${item.declaration_name}.${field.name}`, type: field.logical_type }
        : null;
    }
  }
  if (parsed.part === "property" && section === "components") {
    for (const item of document.components ?? []) {
      if (item.id !== parsed.id) continue;
      const property = (item.properties ?? []).find((candidate) => candidate.name === parsed.name);
      return property
        ? { label: `${item.name}.${property.name}`, type: property.logical_type }
        : null;
    }
  }
  return null;
}

/**
 * Replace the logical type at a part-ref, rebuilding only the path to it.
 *
 * The models are frozen in the backend, so an edit is always a rebuild; this is the
 * same shape a feature's own patch will take.
 */
export function withTypeAtRef(
  document: ProjectDocument,
  ref: string | null,
  next: LogicalType,
): ProjectDocument {
  const parsed = parseRef(ref);
  if (!parsed?.part || !parsed.name) return document;
  const section = SECTION_BY_KIND[parsed.kind];

  const mapFields = <T extends { id: string; fields?: readonly { name: string; logical_type: LogicalType }[] }>(
    items: readonly T[],
  ): T[] =>
    items.map((item) =>
      item.id !== parsed.id
        ? item
        : {
            ...item,
            fields: (item.fields ?? []).map((field) =>
              field.name === parsed.name ? { ...field, logical_type: next } : field,
            ),
          },
    );

  if (section === "tables" || section === "structs") {
    return { ...document, [section]: mapFields(document[section] ?? []) } as ProjectDocument;
  }
  if (section === "annotation_types") {
    return { ...document, annotation_types: mapFields(document.annotation_types ?? []) };
  }
  if (section === "components") {
    return {
      ...document,
      components: (document.components ?? []).map((component) =>
        component.id !== parsed.id
          ? component
          : {
              ...component,
              properties: (component.properties ?? []).map((property) =>
                property.name === parsed.name ? { ...property, logical_type: next } : property,
              ),
            },
      ),
    };
  }
  return document;
}
