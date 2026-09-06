"use client";

/**
 * The inspector panels the contracts feature registers for the dock.
 *
 * The shell's generic `EntityInspector` (priority 0) already shows a summary and the
 * type picker for a typed part; these panels replace it at higher priority so a table,
 * struct or projection shows what its own editor shows — the trust control for a field,
 * the chain summary for a projection output — rather than a generic tree.
 */

import type { ReactNode } from "react";

import { Chip, TypePicker } from "@/components/ui";
import { buildRef, parseRef, refLabel } from "@/lib/ids";
import {
  expressionSummary,
  findInSection,
  sectionItems,
  typeLabel,
  type DataField,
  type LogicalType,
  type Projection,
  type ProjectDocument,
} from "@/lib/ir";
import type { InspectorProps } from "@/lib/types";
import { registerInspector } from "@/components/shell/inspectorRegistry";
import { structModuleMap, chainSummary, trustTier, fieldAffordances } from "./logic";
import { updateField } from "./edit";
import { TrustSegmented } from "./TrustSegmented";
import { useDocumentStore } from "@/stores/documentStore";

/** Register every contracts panel; returns the combined unregister for the caller's effect. */
export function registerContractInspectors(): () => void {
  const unregisters = [
    registerInspector({
      id: "contracts.field",
      label: "Field",
      priority: 10,
      matches: (ref) => {
        const parsed = parseRef(ref);
        return !!parsed?.part && parsed.part === "field" && (parsed.kind === "table" || parsed.kind === "struct");
      },
      render: (props) => <FieldInspector {...props} />,
    }),
    registerInspector({
      id: "contracts.projectionField",
      label: "Projection output",
      priority: 10,
      matches: (ref) => {
        const parsed = parseRef(ref);
        return !!parsed?.part && parsed.part === "field" && parsed.kind === "projection";
      },
      render: (props) => <ProjectionFieldInspector {...props} />,
    }),
    registerInspector({
      id: "contracts.entity",
      label: "Contract",
      priority: 8,
      matches: (ref) => {
        const parsed = parseRef(ref);
        return !!parsed && !parsed.part && (parsed.kind === "table" || parsed.kind === "struct");
      },
      render: (props) => <EntityInspector {...props} />,
    }),
  ];
  return () => {
    for (const unregister of unregisters) unregister();
  };
}

/* ---------------------------------------------------------------------- field */

function FieldInspector({ document, ref, apply }: InspectorProps) {
  const parsed = parseRef(ref);
  if (!parsed?.part || !parsed.name) return null;
  const section = parsed.kind === "table" ? "tables" : "structs";
  const entity = findInSection(document, section, parsed.id) as { id: string; name: string; fields?: readonly DataField[] } | null;
  const field = entity?.fields?.find((item) => item.name === parsed.name);
  if (!entity || !field) return null;
  const trust = trustTier(field.nullability);
  const affordances = fieldAffordances(field.logical_type);

  return (
    <div className="flex min-h-0 flex-col">
      <Header title={`${entity.name}.${field.name}`} kind={`${section === "tables" ? "table" : "struct"} field`} />
      <div className="flex flex-col gap-2.5 border-b border-edge p-2.5">
        <Line label="type" value={<Chip tone={trust.value === "defaulted" ? "warn" : "node"} title={typeLabel(field.logical_type)}>{typeLabel(field.logical_type)}</Chip>} />
        <Line label="trust" value={<Chip title={trust.tooltip}>{trust.label}</Chip>} />
        <p className="text-[11px] leading-snug text-muted">{trust.permits}</p>
        {affordances.length > 0 && <Line label="usable as" value={<span className="font-mono text-[11px] text-relation">{affordances.join(" · ")}</span>} />}
        {field.description && <p className="text-[12px] leading-relaxed text-ink">{field.description}</p>}
      </div>
      <div className="flex flex-col gap-2 border-b border-edge p-2.5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">edit type</p>
        <InspectorTypeEditor ref={ref} value={field.logical_type} document={document} apply={apply} />
        <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">nullability trust</p>
        <InspectorTrustEditor ref={ref} value={field.nullability} document={document} apply={apply} />
      </div>
    </div>
  );
}

function InspectorTypeEditor({ ref: refString, value, document, apply }: { ref: string; value: LogicalType; document: ProjectDocument; apply: InspectorProps["apply"] }) {
  const modules = structModuleMap(document);
  const structs = sectionItems(document, "structs").map((struct) => ({
    module: modules[struct.declaration_name] ?? "",
    qualname: struct.declaration_name,
    label: struct.name,
  }));
  return (
    <TypePicker
      value={value}
      structs={structs}
      onChange={(next) => {
        const parsed = parseRef(refString);
        if (!parsed?.name) return;
        const section = parsed.kind === "table" ? "tables" : "structs";
        const { id, name } = parsed;
        apply((draft) => updateField(draft, section, id, name, { logical_type: next }));
      }}
    />
  );
}

function InspectorTrustEditor({ ref: refString, value, document, apply }: { ref: string; value: DataField["nullability"]; document: ProjectDocument; apply: InspectorProps["apply"] }) {
  const applyStore = useDocumentStore((state) => state.apply);
  void apply;
  return (
    <TrustSegmented
      idPrefix={`insp-${refString}`}
      value={value}
      onChange={(next) => {
        const parsed = parseRef(refString);
        if (!parsed?.name) return;
        const section = parsed.kind === "table" ? "tables" : "structs";
        const { id, name } = parsed;
        applyStore((draft) => updateField(draft, section, id, name, { nullability: next }));
      }}
    />
  );
}

/* ---------------------------------------------------------- projection output */

function ProjectionFieldInspector({ document, ref }: InspectorProps) {
  const parsed = parseRef(ref);
  if (!parsed?.name) return null;
  const projection = findInSection(document, "projections", parsed.id) as Projection | null;
  const field = projection?.fields?.find((item) => item.name === parsed.name);
  if (!projection || !field) return null;
  return (
    <div className="flex min-h-0 flex-col">
      <Header title={`${projection.name}.${field.name}`} kind="projection output" />
      <div className="flex flex-col gap-2 border-b border-edge p-2.5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">summary chain</p>
        <div className="rounded-md border border-edge bg-raised p-2 font-mono text-[11px] leading-relaxed text-relation">
          {chainSummary(field.expression)}
        </div>
        <p className="text-[11px] text-faint">read-only here — the expression stack is authored in the bindings composer ({expressionSummary(field.expression)}).</p>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------- entity */

function EntityInspector({ document, ref, onSelectRef }: InspectorProps) {
  const parsed = parseRef(ref);
  if (!parsed) return null;
  const section = parsed.kind === "table" ? "tables" : "structs";
  const entity = findInSection(document, section, parsed.id) as { name: string; declaration_name: string; fields?: readonly DataField[]; members?: readonly { python_name: string; ref: string }[]; group?: string | null } | null;
  if (!entity) return null;
  const members = "members" in entity ? entity.members ?? [] : [];
  const fieldCount = entity.fields?.length ?? 0;
  return (
    <div className="flex min-h-0 flex-col">
      <Header title={entity.name} kind={members.length > 0 ? "table group" : parsed.kind === "table" ? "table" : "struct"} />
      <div className="flex flex-col gap-1.5 border-b border-edge p-2.5">
        <Line label="declaration" value={<span className="font-mono text-[11px] text-ink">{entity.declaration_name}</span>} />
        <Line label="shape" value={<span className="font-mono text-[11px] text-muted">{fieldCount} fields{members.length ? ` · ${members.length} members` : ""}</span>} />
        {entity.group && <Line label="group" value={<Chip tone="category" onClick={() => onSelectRef(buildRef("table", entity.group!))}>{refLabel(buildRef("table", entity.group))}</Chip>} />}
      </div>
      {(entity.fields?.length ?? 0) > 0 && (
        <div className="min-h-0 flex-1 overflow-auto">
          <p className="px-2.5 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">fields</p>
          <ul>
            {(entity.fields ?? []).map((field) => (
              <li key={field.name}>
                <button type="button" onClick={() => onSelectRef(buildRef(parsed.kind, parsed.id, "field", field.name))} className="flex w-full items-center gap-2 border-b border-edge/50 px-2.5 py-1 text-left hover:bg-raised">
                  <span className="w-28 shrink-0 truncate font-mono text-[11px] text-ink">{field.name}</span>
                  <span className="min-w-0 flex-1 truncate font-mono text-[11px] text-muted">{typeLabel(field.logical_type)}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/* -------------------------------------------------------------------- shared */

function Header({ title, kind }: { title: string; kind: string }) {
  return (
    <div className="flex flex-col gap-0.5 border-b border-edge p-2.5">
      <p className="truncate text-[13px] font-semibold text-ink">{title}</p>
      <p className="truncate font-mono text-[10px] uppercase tracking-[0.06em] text-faint">{kind}</p>
    </div>
  );
}

function Line({ label, value }: { label: string; value: ReactNode }): ReactNode {
  return (
    <div className="grid grid-cols-[5rem_1fr] items-center gap-2">
      <span className="text-[11px] uppercase tracking-[0.06em] text-muted">{label}</span>
      <div className="min-w-0">{value}</div>
    </div>
  );
}
