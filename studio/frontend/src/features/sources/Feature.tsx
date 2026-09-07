"use client";

/**
 * Sources — the physical inputs bound to tables.
 *
 * PROP CONTRACT (`FeatureProps`, see `src/lib/types.ts`):
 *   document      `document.sources` are the `bind_source` calls; `source.table` names a
 *                 table or table group, and a group's `layout` templates `{group_path}`
 *                 and `{table_name}`. Refs are `source:<id>`.
 *   index         Unused: sources reference tables, and the shell already filters
 *                 problems by ref.
 *   problems      Pre-filtered problems whose ref is `source:*`.
 *   selectedRef / onSelectRef   The standard global selection.
 *   apply         Adds, edits and removes a source; optimistic, coalesced, undoable.
 *                 Removal goes through the shared delete controls, so "what still needs
 *                 this data?" is answered the way every other declaration answers it.
 *
 * Implemented as the picker it needs to be (DESIGN.md §5): discovered data files on the
 * left (`GET /api/data/files`), the document's bindings on the right. Shape inference
 * still belongs to the backend — `POST /api/infer` folds an imported shape into the
 * document rather than the filesystem — so that stays out of here.
 */

import { useEffect, useMemo, useState } from "react";
import clsx from "clsx";

import {
  Button,
  Card,
  Chip,
  EmptyState,
  Field,
  Panel,
  PlusIcon,
  ProblemBadge,
  Select,
  TextInput,
} from "@/components/ui";
import { freeId } from "@/lib/ids";
import { sectionItems, sourceBindsTable, tableAncestry } from "@/lib/ir";
import type { DataFile, FeatureProps } from "@/lib/types";
import type { Source, SourceFormat } from "@/lib/ir";
import { useDocumentStore } from "@/stores/documentStore";
import { useProblemStore } from "@/stores/problemStore";
import { useSelectionStore } from "@/stores/selectionStore";
import { referrersForDeletion, type Referrer } from "@/features/contracts/logic";
import { DeleteButton, DeleteDialog } from "@/features/contracts/DeleteControls";
import { loadDataFiles } from "@/components/shell/useStudioSession";
import { removeSourceCascade } from "./edit";

const FORMATS: readonly SourceFormat[] = ["csv", "json", "parquet"];

export default function SourcesFeature({
  document,
  selectedRef,
  onSelectRef,
  apply,
}: FeatureProps) {
  const mock = useDocumentStore((state) => state.mock);
  const byRefIndex = useProblemStore((state) => state.byRefIndex);
  const [files, setFiles] = useState<readonly DataFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [picked, setPicked] = useState<string>("");

  useEffect(() => {
    let alive = true;
    loadDataFiles(mock)
      .then((raw) => {
        // `/api/data/files` wraps its list in `{files}`; the shared `api.dataFiles()` is
        // typed as a bare array, so unwrap before rendering (live mode returns the object).
        if (alive) setFiles(Array.isArray(raw) ? raw : ((raw as unknown as { files?: DataFile[] })?.files ?? []));
      })
      .catch((cause: unknown) => {
        if (alive) setError(cause instanceof Error ? cause.message : String(cause));
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [mock]);

  const sources = sectionItems(document, "sources");
  // The selected source, if the selection is one: like the projection detail panel,
  // the delete control exists only for the declaration it acts on.
  const target = sources.find((source) => `source:${source.id}` === selectedRef) ?? null;
  const [pendingDelete, setPendingDelete] = useState<Referrer[] | null>(null);
  const allTables = useMemo(() => sectionItems(document, "tables"), [document]);
  const tables = useMemo(
    () => allTables.map((table) => ({ value: table.id, label: table.name })),
    [allTables],
  );
  // A group's source fans out to its members, so a member of a bound group already
  // has data behind it and must not be listed as missing one.
  const unbound = allTables
    .filter(
      (table) =>
        !tableAncestry(allTables, table).some((link) =>
          sources.some((source) => sourceBindsTable(source, link)),
        ),
    )
    .map((table) => ({ value: table.id, label: table.name }));

  const patch = (id: string, changes: Partial<Source>) =>
    apply((draft) => ({
      ...draft,
      sources: sectionItems(draft, "sources").map((item) =>
        item.id === id ? ({ ...item, ...changes } as Source) : item,
      ),
    }));

  const bind = () => {
    const file = files.find((candidate) => candidate.location === picked);
    const target = unbound[0];
    if (!file || !target) return;
    const id = freeId(`${file.name}_source`, sources.map((source) => source.id));
    const source: Source = {
      id,
      table: target.value,
      location: file.location,
      format: (FORMATS as readonly string[]).includes(file.format)
        ? (file.format as SourceFormat)
        : "json",
    };
    apply((draft) => ({ ...draft, sources: [...sectionItems(draft, "sources"), source] }));
    useSelectionStore.getState().selectAndReveal(`source:${id}`);
    setPicked("");
  };

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[minmax(13rem,17rem)_1fr] gap-px bg-edge">
      <Panel title="Data files" subtitle={loading ? "loading…" : `${files.length} discovered`}>
        {error ? (
          <EmptyState title="Data files unavailable" body={error} />
        ) : files.length === 0 && !loading ? (
          <EmptyState
            title="No data files discovered"
            body={`Nothing readable under ${document.project.data_directory}/ of the project root.`}
          />
        ) : (
          <ul className="flex flex-col gap-px">
            {files.map((file) => (
              <li key={file.location}>
                <button
                  type="button"
                  onClick={() => setPicked(file.location)}
                  aria-current={picked === file.location ? "true" : undefined}
                  className={clsx(
                    "flex w-full items-center gap-2 rounded px-1.5 py-1 text-left hover:bg-raised",
                    picked === file.location && "bg-raised",
                  )}
                >
                  <Chip>{file.format}</Chip>
                  <span className="min-w-0 flex-1 truncate font-mono text-[11px] text-ink">
                    {file.location}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel
        title="Bound sources"
        subtitle={`${sources.length} bound · ${unbound.length} missing`}
        id="panel-sources"
        actions={
          <div className="flex items-center gap-1.5">
            {target && (
              <DeleteButton
                label="source"
                onClick={() => setPendingDelete(referrersForDeletion(document, "source", target.id))}
              />
            )}
            <Button
              variant="primary"
              icon={<PlusIcon />}
              disabled={!picked || unbound.length === 0}
              onClick={bind}
              title={
                unbound.length === 0
                  ? "Every table already has a source"
                  : `Bind to table ${unbound[0]?.label ?? ""}`
              }
            >
              bind source
            </Button>
          </div>
        }
      >
        {unbound.length > 0 && (
          <p className="pb-2 text-[12px] text-warn">
            no source for {unbound.map((table) => table.label).join(", ")}
          </p>
        )}
        {sources.length === 0 ? (
          <EmptyState title="No sources yet" body="Pick a data file on the left, then bind it." />
        ) : (
          <div className="flex flex-col gap-2">
            {sources.map((source) => {
              const ref = `source:${source.id}`;
              const selected = selectedRef === ref;
              return (
                <Card
                  key={source.id}
                  selected={selected}
                  onSelect={() => onSelectRef(selected ? null : ref)}
                  header={
                    <div className="flex items-center gap-2">
                      <span className="truncate font-mono text-[12px] text-ink">{source.id}</span>
                      <Chip tone="relation">{source.format}</Chip>
                      <span className="ml-auto">
                        <ProblemBadge problems={byRefIndex[ref] ?? []} ref={ref} compact />
                      </span>
                    </div>
                  }
                >
                  <div className="flex flex-col gap-1.5 pt-1">
                    <Field label="table" htmlFor={`source-${source.id}-table`}>
                      <Select
                        id={`source-${source.id}-table`}
                        value={source.table}
                        options={tables}
                        onChange={(event) => patch(source.id, { table: event.target.value })}
                      />
                    </Field>
                    <Field label="format" htmlFor={`source-${source.id}-format`}>
                      <Select
                        id={`source-${source.id}-format`}
                        value={source.format}
                        options={FORMATS.map((format) => ({ value: format, label: format }))}
                        onChange={(event) =>
                          patch(source.id, { format: event.target.value as SourceFormat })
                        }
                      />
                    </Field>
                    <Field
                      label="location"
                      htmlFor={`source-${source.id}-location`}
                      hint={source.layout ? `layout ${source.layout}` : undefined}
                    >
                      <TextInput
                        id={`source-${source.id}-location`}
                        mono
                        value={source.location}
                        onChange={(event) => patch(source.id, { location: event.target.value })}
                      />
                    </Field>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
        <DeleteDialog
          pending={pendingDelete}
          onCancel={() => setPendingDelete(null)}
          onConfirm={() => {
            if (target) apply((draft) => removeSourceCascade(draft, target.id));
            onSelectRef(null);
            setPendingDelete(null);
          }}
        />
      </Panel>
    </div>
  );
}
