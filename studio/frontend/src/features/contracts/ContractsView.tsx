"use client";

/**
 * The contracts master list + detail pane for tables, structs and table groups.
 *
 * The list is searchable, shows a field/member count and a problem badge per row, and
 * hints when a shape came from inference (`generated from data/<feed>`). The detail pane
 * renders the field table editor or, for a group, the nested catalogue; deletions that
 * would dangle a reference are blocked with the referrers listed.
 */

import { useState } from "react";
import clsx from "clsx";

import {
  Button,
  Chip,
  EmptyState,
  IconButton,
  Modal,
  Panel,
  PlusIcon,
  ProblemBadge,
  SearchIcon,
  TextInput,
} from "@/components/ui";
import { buildRef } from "@/lib/ids";
import { type ProjectDocument, type Table } from "@/lib/ir";
import type { FeatureProps } from "@/lib/types";
import { useDocumentStore } from "@/stores/documentStore";
import { useProblemStore } from "@/stores/problemStore";
import {
  isGroupOnly,
  isGroupDeclaration,
  referrersForDeletion,
  shapeProvenance,
  type Referrer,
} from "@/features/contracts/logic";
import { deleteEntity, makeTable, renameEntity } from "@/features/contracts/edit";
import { FieldTable } from "./FieldTable";
import { GroupCatalogue } from "./GroupCatalogue";
import { ImportShapePanel } from "./ImportShapePanel";

type Selected =
  | { kind: "table"; id: string }
  | { kind: "struct"; id: string }
  | null;

function parseSelection(ref: string | null): Selected {
  if (!ref) return null;
  if (ref.startsWith("table:")) return { kind: "table", id: ref.slice("table:".length).split(".")[0] ?? "" };
  if (ref.startsWith("struct:")) return { kind: "struct", id: ref.slice("struct:".length).split(".")[0] ?? "" };
  return null;
}

export function ContractsView({ document, problems, selectedRef, onSelectRef, apply }: FeatureProps) {
  void problems;
  const tables = document.tables ?? [];
  const structs = document.structs ?? [];
  const selected = parseSelection(selectedRef);
  const [showImport, setShowImport] = useState(false);

  // The list default-selects the first table so the detail pane is never blank on arrival.
  const effective =
    selected ??
    (tables[0] ? { kind: "table" as const, id: tables[0].id } : structs[0] ? { kind: "struct" as const, id: structs[0].id } : null);

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[minmax(14rem,18rem)_1fr] gap-px bg-edge">
      <MasterList document={document} selected={effective} onSelect={onSelectRef} onImport={() => setShowImport((value) => !value)} importing={showImport} />
      {showImport ? (
        <ImportShapePanel document={document} onClose={() => setShowImport(false)} />
      ) : (
        <DetailPane document={document} selection={effective} onSelect={onSelectRef} apply={apply} />
      )}
    </div>
  );
}

/* ----------------------------------------------------------------- master list */

function MasterList({
  document,
  selected,
  onSelect,
  onImport,
  importing,
}: {
  document: ProjectDocument;
  selected: Selected;
  onSelect(ref: string | null): void;
  onImport(): void;
  importing: boolean;
}) {
  const apply = useDocumentStore((state) => state.apply);
  const [query, setQuery] = useState("");
  const byRefIndex = useProblemStore((state) => state.byRefIndex);
  const tables = document.tables ?? [];
  const structs = document.structs ?? [];
  const needle = query.trim().toLowerCase();

  const match = (name: string, id: string) => !needle || name.toLowerCase().includes(needle) || id.toLowerCase().includes(needle);

  // Members render nested under their owning group, so the top level lists only the
  // tables that have no parent group. A "group" for listing purposes owns a catalogue
  // *and* reads nothing itself (`isGroupOnly`) — a member table that kept a copied
  // `members` list alongside its fields is a leaf, not a group row.
  const memberCount = tables.filter((table) => table.group).length;
  const ownsCatalogue = (table: Table) => isGroupOnly(table) || isGroupDeclaration(table);
  const groupRoots = tables.filter((table) => ownsCatalogue(table) && !table.group);
  const topTables = tables.filter((table) => !ownsCatalogue(table) && !table.group);

  const create = (group: boolean) => {
    const { table, document: next } = makeTable(group ? "new_group" : "new_table", document, group);
    apply(() => next);
    onSelect(buildRef("table", table.id));
  };

  return (
    <Panel
      title="Tables & structs"
      subtitle={`${tables.length} tables · ${structs.length} structs`}
      padded={false}
      actions={
        <>
          <Button size="sm" variant={importing ? "primary" : "default"} icon={<ImportIcon />} onClick={onImport} title="Import a data shape (POST /api/infer)">
            import
          </Button>
          <Button size="sm" icon={<PlusIcon />} onClick={() => create(false)}>table</Button>
          <Button size="sm" variant="ghost" icon={<PlusIcon />} onClick={() => create(true)}>group</Button>
        </>
      }
    >
      <div className="flex flex-col gap-1 p-2">
        <label className="flex items-center gap-1.5 rounded-md border border-edge bg-raised px-2">
          <SearchIcon />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="search tables and structs…"
            aria-label="search contracts"
            className="h-6 min-w-0 flex-1 bg-transparent text-[12px] text-ink outline-none placeholder:text-faint"
          />
        </label>

        <GroupSection label="tables">
          {topTables.filter((table) => match(table.name, table.id)).map((table) => (
            <EntityRow key={table.id} refString={buildRef("table", table.id)} label={table.name} detail={`${(table.fields ?? []).length} fields`} selected={selected} onSelect={onSelect} problems={byRefIndex[buildRef("table", table.id)] ?? []} provenance={shapeProvenance(document, table)} />
          ))}
          {groupRoots.filter((table) => match(table.name, table.id)).map((table) => (
            <GroupRow key={table.id} document={document} group={table} selected={selected} onSelect={onSelect} problems={byRefIndex[buildRef("table", table.id)] ?? []} />
          ))}
        </GroupSection>

        <GroupSection label="structs">
          {structs.filter((struct) => match(struct.name, struct.id)).map((struct) => (
            <EntityRow key={struct.id} refString={buildRef("struct", struct.id)} label={struct.name} detail={`${(struct.fields ?? []).length} members`} selected={selected} onSelect={onSelect} problems={byRefIndex[buildRef("struct", struct.id)] ?? []} provenance={{ inferred: false, feed: null }} />
          ))}
        </GroupSection>

        {tables.length === 0 && structs.length === 0 && (
          <p className="px-1.5 py-3 text-center text-[11px] text-faint">nothing declared yet — add a table or import a data shape</p>
        )}
        {memberCount > 0 && <p className="px-1.5 pt-1 font-mono text-[10px] text-faint">{memberCount} table(s) are group members</p>}
      </div>
    </Panel>
  );
}

function GroupSection({ label, children }: { label: string; children: React.ReactNode }) {
  const items = Array.isArray(children) ? children.filter(Boolean) : children ? [children] : [];
  if (items.length === 0) return null;
  return (
    <div className="flex flex-col gap-px">
      <p className="px-1.5 pt-1.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-faint">{label}</p>
      {children}
    </div>
  );
}

function GroupRow({
  document,
  group,
  selected,
  onSelect,
  problems,
}: {
  document: ProjectDocument;
  group: Table;
  selected: Selected;
  onSelect(ref: string | null): void;
  problems: FeatureProps["problems"];
}) {
  const [open, setOpen] = useState(true);
  const refString = buildRef("table", group.id);
  const isSel = selected?.kind === "table" && selected.id === group.id;
  return (
    <div className="flex flex-col">
      <button
        type="button"
        onClick={() => { setOpen((value) => !value); onSelect(refString); }}
        aria-current={isSel ? "true" : undefined}
        className={clsx("flex w-full items-center gap-1.5 rounded px-1.5 py-1 text-left hover:bg-raised", isSel && "bg-raised")}
      >
        <Chevron open={open} />
        <Chip tone="category" plain>group</Chip>
        <span className="min-w-0 flex-1 truncate font-mono text-[12px] text-ink">{group.name}</span>
        <span className="font-mono text-[10px] text-faint">{(group.members ?? []).length}</span>
        <ProblemBadge problems={problems} ref={refString} compact />
      </button>
      {open && (
        <div className="ml-3 border-l border-edge pl-1.5">
          {(group.members ?? []).map((member) => {
            const memberTable = (document.tables ?? []).find((item) => item.id === member.ref);
            if (!memberTable) return null;
            const memberRef = buildRef("table", memberTable.id);
            return (
              <EntityRow
                key={member.ref}
                refString={memberRef}
                label={memberTable.name}
                detail={isGroupOnly(memberTable) ? `${(memberTable.members ?? []).length} members` : `${(memberTable.fields ?? []).length} fields`}
                selected={selected}
                onSelect={onSelect}
                problems={problemsFor(memberRef)}
                provenance={shapeProvenance(document, memberTable)}
                indent
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

// A plain read of the problem index for nested rows (the hook form needs a fixed call order).
function problemsFor(ref: string): FeatureProps["problems"] {
  return useProblemStore.getState().byRefIndex[ref] ?? [];
}

function EntityRow({
  refString,
  label,
  detail,
  selected,
  onSelect,
  problems,
  provenance,
  indent = false,
}: {
  refString: string;
  label: string;
  detail: string;
  selected: Selected;
  onSelect(ref: string | null): void;
  problems: FeatureProps["problems"];
  provenance: { inferred: boolean; feed: string | null };
  indent?: boolean;
}) {
  const kind = refString.startsWith("struct:") ? "struct" : "table";
  const id = refString.slice(refString.indexOf(":") + 1).split(".")[0];
  const isSel = selected?.kind === kind && selected.id === id;
  return (
    <button
      type="button"
      onClick={() => onSelect(refString)}
      aria-current={isSel ? "true" : undefined}
      className={clsx(
        "flex w-full items-center gap-1.5 rounded px-1.5 py-1 text-left hover:bg-raised",
        isSel && "bg-raised",
        indent && "pl-1",
      )}
    >
      <span className="min-w-0 flex-1 truncate font-mono text-[12px] text-ink">{label}</span>
      {provenance.inferred && (
        <Chip
          tone="relation"
          className="max-w-[46%] shrink"
          title={`shape inferred from ${provenance.feed ?? "a data feed"}`}
        >
          {provenance.feed ?? "inferred"}
        </Chip>
      )}
      <span className="shrink-0 font-mono text-[10px] text-faint">{detail}</span>
      <ProblemBadge problems={problems} ref={refString} compact />
    </button>
  );
}

/* ----------------------------------------------------------------- detail pane */

function DetailPane({
  document,
  selection,
  onSelect,
  apply,
}: {
  document: ProjectDocument;
  selection: Selected;
  onSelect(ref: string | null): void;
  apply: FeatureProps["apply"];
}) {
  const [pendingDelete, setPendingDelete] = useState<Referrer[] | null>(null);
  const [renaming, setRenaming] = useState<string | null>(null);

  if (!selection) {
    return (
      <Panel title="Detail">
        <EmptyState title="Nothing selected" body="Add a table, or import a data shape to start the catalogue." />
      </Panel>
    );
  }

  if (selection.kind === "struct") {
    const struct = (document.structs ?? []).find((item) => item.id === selection.id);
    if (!struct) return <Panel title="Detail"><EmptyState title="Struct gone" body="It was deleted in another tab." /></Panel>;
    const referrers = referrersForDeletion(document, "struct", struct.id);
    return (
      <Panel
        title={struct.name}
        subtitle={`${struct.declaration_name} · ${(struct.fields ?? []).length} members`}
        actions={<DeleteButton label="struct" onClick={() => setPendingDelete(referrers)} />}
      >
        <RenameRow kind="struct" name={struct.name} renaming={renaming} setRenaming={setRenaming} onCommit={(next) => { apply((draft) => renameEntity(draft, "structs", struct.id, next)); setRenaming(null); }} />
        <div className="pt-2">
          <FieldTable document={document} section="structs" entityId={struct.id} path={[struct.name]} />
        </div>
        <DeleteDialog pending={pendingDelete} onCancel={() => setPendingDelete(null)} onConfirm={() => { apply((draft) => deleteEntity(draft, "structs", struct.id)); onSelect(null); setPendingDelete(null); }} />
      </Panel>
    );
  }

  const table = (document.tables ?? []).find((item) => item.id === selection.id);
  if (!table) return <Panel title="Detail"><EmptyState title="Table gone" body="It was deleted in another tab." /></Panel>;
  const group = isGroupOnly(table) || isGroupDeclaration(table);
  const referrers = referrersForDeletion(document, "table", table.id);
  const provenance = shapeProvenance(document, table);

  return (
    <Panel
      title={table.name}
      subtitle={`${table.declaration_name}${group ? " · group" : ` · ${(table.fields ?? []).length} fields`}`}
      actions={<DeleteButton label={group ? "group" : "table"} onClick={() => setPendingDelete(referrers)} />}
      id="panel-contract-detail"
    >
      {provenance.inferred && (
        <p className="mb-2 rounded-md border border-relation/40 bg-relation-soft px-2 py-1 text-[11px] text-relation">
          generated from <span className="font-mono">{provenance.feed ?? "a data feed"}</span> — shape inferred from the file, edit freely
        </p>
      )}
      <RenameRow kind="table" name={table.name} renaming={renaming} setRenaming={setRenaming} onCommit={(next) => { apply((draft) => renameEntity(draft, "tables", table.id, next)); setRenaming(null); }} />
      <div className="pt-2">
        {group ? (
          <GroupCatalogue document={document} group={table} />
        ) : (
          <FieldTable document={document} section="tables" entityId={table.id} path={[table.name]} />
        )}
      </div>
      <DeleteDialog pending={pendingDelete} onCancel={() => setPendingDelete(null)} onConfirm={() => { apply((draft) => deleteEntity(draft, "tables", table.id)); onSelect(null); setPendingDelete(null); }} />
    </Panel>
  );
}

function RenameRow({
  kind,
  name,
  renaming,
  setRenaming,
  onCommit,
}: {
  kind: string;
  name: string;
  renaming: string | null;
  setRenaming(value: string | null): void;
  onCommit(next: string): void;
}) {
  const key = `${kind}:${name}`;
  if (renaming !== key) {
    return (
      <div className="flex items-center gap-2">
        <span className="font-mono text-[12px] text-muted">{name}</span>
        <Button size="sm" variant="ghost" onClick={() => setRenaming(key)}>rename</Button>
      </div>
    );
  }
  return (
    <form
      className="flex items-center gap-1.5"
      onSubmit={(event) => {
        event.preventDefault();
        const value = (new FormData(event.currentTarget).get("name") as string) || "";
        if (value.trim()) onCommit(value.trim());
      }}
    >
      <TextInput autoFocus name="name" mono defaultValue={name} className="max-w-[16rem]" />
      <Button size="sm" variant="primary" type="submit">save</Button>
      <Button size="sm" variant="ghost" type="button" onClick={() => setRenaming(null)}>cancel</Button>
    </form>
  );
}

function DeleteButton({ label, onClick }: { label: string; onClick(): void }) {
  return (
    <Button size="sm" variant="danger" onClick={onClick}>
      delete {label}
    </Button>
  );
}

/**
 * The delete confirmation. When `pending` holds referrers the deletion is blocked and
 * the referrers are listed; when it is an empty array the delete proceeds.
 */
function DeleteDialog({
  pending,
  onCancel,
  onConfirm,
}: {
  pending: Referrer[] | null;
  onCancel(): void;
  onConfirm(): void;
}) {
  if (pending === null) return null;
  const blocked = pending.length > 0;
  return (
    <Modal
      open
      onClose={onCancel}
      title={blocked ? "Cannot delete — still referenced" : "Confirm delete"}
      footer={
        blocked ? (
          <Button variant="primary" onClick={onCancel}>keep it</Button>
        ) : (
          <>
            <Button onClick={onCancel}>cancel</Button>
            <Button variant="danger" onClick={onConfirm}>delete</Button>
          </>
        )
      }
    >
      {blocked ? (
        <div className="flex flex-col gap-2">
          <p className="text-[12px] text-ink">
            This declaration is still referenced by {pending.length} item{pending.length === 1 ? "" : "s"}. Deleting it would dangle those
            references, so the delete is blocked. Remove or repoint them first.
          </p>
          <ul className="flex flex-col gap-1">
            {pending.map((referrer) => (
              <li key={`${referrer.ref}:${referrer.label}`} className="flex items-center gap-2 rounded border border-danger/40 bg-danger/10 px-2 py-1">
                <Chip tone="danger">{referrer.kind}</Chip>
                <span className="min-w-0 flex-1 truncate font-mono text-[11px] text-ink">{referrer.label}</span>
                <span className="shrink-0 font-mono text-[10px] text-faint">{referrer.ref}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-[12px] text-ink">Nothing references this declaration. Deleting removes it from the project.</p>
      )}
    </Modal>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg viewBox="0 0 24 24" width={11} height={11} aria-hidden className={clsx("shrink-0 transition-transform", open && "rotate-90")} fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
      <path d="m9 5 7 7-7 7" />
    </svg>
  );
}

function ImportIcon() {
  return (
    <svg viewBox="0 0 24 24" width={13} height={13} aria-hidden className="shrink-0" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 4v9m0 0 3.2-3.2M12 13 8.8 9.8" />
      <path d="M4.5 15v3a1.5 1.5 0 0 0 1.5 1.5h12A1.5 1.5 0 0 0 19.5 18v-3" />
    </svg>
  );
}
