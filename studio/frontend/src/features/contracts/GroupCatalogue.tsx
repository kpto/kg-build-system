"use client";

/**
 * The table-group catalogue. A group renders as a nested catalogue (like the
 * `publications` example: `clinical`/`preclinical` under `publications`, `vibration`
 * under the nested `mechanical` under `readings`). Adding a member inside a group sets
 * the child's `group` id and appends a `TableGroupMember`; the layout of the group's
 * bound source is resolved per leaf member so the author sees which physical file each
 * member reads.
 */

import { useMemo, useState } from "react";
import clsx from "clsx";

import { Button, Chip, IconButton, PlusIcon, ProblemBadge, Select, TextInput } from "@/components/ui";
import { buildRef } from "@/lib/ids";
import { typeLabel, type ProjectDocument, type Table } from "@/lib/ir";
import { sectionItems } from "@/lib/ir";
import { useDocumentStore } from "@/stores/documentStore";
import { useProblemsForRef } from "@/stores/problemStore";
import { useSelectionStore } from "@/stores/selectionStore";
import {
  addMemberToGroup,
  boundSourceForTable,
  isGroupOnly,
  isTableGroup,
  memberTables,
  resolveGroupSourcePaths,
} from "@/features/contracts/logic";
import { makeTable } from "@/features/contracts/edit";

interface GroupCatalogueProps {
  document: ProjectDocument;
  group: Table;
  /** Depth guard for the nested render; a broken document cannot loop the tree. */
  depth?: number;
}

export function GroupCatalogue({ document, group, depth = 0 }: GroupCatalogueProps) {
  const apply = useDocumentStore((state) => state.apply);
  const members = memberTables(document, group);
  const source = boundSourceForTable(document, group);
  const resolved = useMemo(() => (source ? resolveGroupSourcePaths(document, source) : []), [document, source]);
  const pathByMember = new Map(resolved.map((item) => [item.table.id, item.path]));

  const addMember = (memberId: string) => {
    const result = addMemberToGroup(document, group.id, memberId);
    if (result.ok && result.document) apply(() => result.document as ProjectDocument);
  };

  const addNewMember = (label: string) => {
    const { table, document: withTable } = makeTable(label || "member", document);
    const result = addMemberToGroup(withTable, group.id, table.id);
    const next = result.ok && result.document ? result.document : withTable;
    apply(() => next);
    useSelectionStore.getState().selectAndReveal(buildRef("table", table.id));
  };

  return (
    <div className="flex flex-col gap-1.5">
      {source ? (
        <p className="font-mono text-[10px] text-faint">
          source {source.id} · {source.location}
          {source.layout ? ` · layout ${source.layout}` : ""} — resolves per member ↓
        </p>
      ) : (
        <p className="text-[11px] text-warn">no source bound to this group — its members have no physical file yet</p>
      )}
      {members.length === 0 && (
        <p className="rounded border border-dashed border-edge px-2 py-2 text-center text-[11px] text-faint">
          empty group — add a member table below
        </p>
      )}
      <ul className="flex flex-col gap-1">
        {members.map((member) => (
          <MemberRow
            key={member.id}
            document={document}
            member={member}
            resolvedPath={pathByMember.get(member.id)}
            depth={depth}
            onAddNested={addMember}
          />
        ))}
      </ul>
      <MemberAdder document={document} group={group} onAddExisting={addMember} onAddNew={addNewMember} />
    </div>
  );
}

interface MemberRowProps {
  document: ProjectDocument;
  member: Table;
  resolvedPath?: string;
  depth: number;
  onAddNested(memberId: string): void;
}

function MemberRow({ document, member, resolvedPath, depth, onAddNested }: MemberRowProps) {
  const select = useSelectionStore((state) => state.select);
  const ref = buildRef("table", member.id);
  const problems = useProblemsForRef(ref);
  const [open, setOpen] = useState(isTableGroup(member));
  const nested = isGroupOnly(member);

  return (
    <li className={clsx("flex flex-col gap-1 border-l-2 pl-2.5", nested ? "border-category/50" : "border-edge")}>
      <div className="flex min-w-0 items-center gap-2">
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          aria-label={`${open ? "Collapse" : "Expand"} ${member.name}`}
          className="shrink-0 text-faint hover:text-ink"
        >
          <ChevronToggle open={open} />
        </button>
        <button type="button" onClick={() => select(ref)} className="min-w-0 flex-1 truncate text-left">
          <span className="font-mono text-[12px] text-ink">{member.name}</span>
          <span className="ml-2 text-[11px] text-faint">
            {nested ? `${memberTables(document, member).length} members` : `${(member.fields ?? []).length} fields`}
          </span>
        </button>
        {resolvedPath && <span className="hidden truncate font-mono text-[10px] text-relation sm:inline" title={resolvedPath}>{resolvedPath}</span>}
        <ProblemBadge problems={problems} ref={ref} compact />
      </div>
      {open && nested && (
        <div className="pl-1">
          <GroupCatalogue document={document} group={member} depth={depth + 1} />
        </div>
      )}
      {open && !nested && (member.fields ?? []).length > 0 && (
        <ul className="flex flex-wrap gap-1 pl-6">
          {(member.fields ?? []).slice(0, 8).map((field) => (
            <li key={field.name}>
              <Chip title={typeLabel(field.logical_type)}>{field.name}</Chip>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

function MemberAdder({
  document,
  group,
  onAddExisting,
  onAddNew,
}: {
  document: ProjectDocument;
  group: Table;
  onAddExisting(memberId: string): void;
  onAddNew(label: string): void;
}) {
  const [label, setLabel] = useState("");
  const members = new Set(memberTables(document, group).map((item) => item.id));
  const candidates = sectionItems(document, "tables")
    .filter((table) => !members.has(table.id) && !isGroupOnly(table) && table.id !== group.id)
    .map((table) => ({ value: table.id, label: table.name }));
  const [picked, setPicked] = useState("");

  return (
    <div className="flex flex-wrap items-end gap-2 border-t border-edge pt-2">
      <label className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="text-[11px] uppercase tracking-[0.06em] text-muted">new member table</span>
        <TextInput
          mono
          placeholder="e.g. clinical"
          value={label}
          onChange={(event) => setLabel(event.target.value)}
        />
      </label>
      <Button
        size="sm"
        icon={<PlusIcon />}
        disabled={!label.trim()}
        onClick={() => {
          onAddNew(label);
          setLabel("");
        }}
      >
        add member
      </Button>
      <div className="flex items-center gap-1">
        <Select
          aria-label="existing table as member"
          className="max-w-[10rem]"
          placeholder="or existing table…"
          value={picked}
          options={candidates}
          onChange={(event) => setPicked(event.target.value)}
        />
        <IconButton
          size="sm"
          label="Add selected table as member"
          icon={<PlusIcon />}
          disabled={!picked}
          onClick={() => {
            onAddExisting(picked);
            setPicked("");
          }}
        />
      </div>
    </div>
  );
}

function ChevronToggle({ open }: { open: boolean }) {
  return (
    <svg viewBox="0 0 24 24" width={12} height={12} aria-hidden className={clsx("transition-transform", open && "rotate-90")} fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
      <path d="m9 5 7 7-7 7" />
    </svg>
  );
}
