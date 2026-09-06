"use client";

/**
 * Import data shape — the starter feature that turns a physical feed into contract
 * declarations. It lists the discovered data files (`GET /api/data/files`), lets the
 * author pick one and choose table vs table-group, previews the tables/structs
 * `/api/infer` would add against the current document, and folds them in on "add to
 * project". Offline (no backend) the list falls back to the mock fixture and the
 * preview is a documented sample shape, so the flow is developable; a live `/api/infer`
 * failure shows a clear disabled state rather than crashing.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import clsx from "clsx";

import { Button, Chip, EmptyState, IconButton, Panel, PlusIcon, RefreshIcon, Select } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { typeLabel, type ProjectDocument } from "@/lib/ir";
import type { DataFile } from "@/lib/types";
import { useDocumentStore } from "@/stores/documentStore";
import { notify } from "@/stores/connectionStore";
import { useSelectionStore } from "@/stores/selectionStore";
import { loadDataFiles } from "@/components/shell/useStudioSession";
import {
  applyImportPreview,
  buildImportPreview,
  offlineImportPreview,
  type ImportMode,
  type ImportPreview,
} from "./logic";

interface ImportShapePanelProps {
  document: ProjectDocument;
  onClose(): void;
}

export function ImportShapePanel({ document, onClose }: ImportShapePanelProps) {
  const mock = useDocumentStore((state) => state.mock);
  const apply = useDocumentStore((state) => state.apply);

  const [files, setFiles] = useState<readonly DataFile[]>([]);
  const [loadingFiles, setLoadingFiles] = useState(true);
  const [filesError, setFilesError] = useState<string | null>(null);
  const [picked, setPicked] = useState<string>("");
  const [mode, setMode] = useState<ImportMode>("table");

  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [inferring, setInferring] = useState(false);
  const [inferError, setInferError] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    let alive = true;
    loadDataFiles(mock)
      .then((raw) => {
        if (!alive) return;
        // `/api/data/files` wraps its array in `{files}`; the shared `api.dataFiles()`
        // is typed as a bare array, so unwrap defensively before rendering the list.
        const list = Array.isArray(raw) ? raw : ((raw as unknown as { files?: DataFile[] })?.files ?? []);
        setFiles(list);
      })
      .catch((cause: unknown) => alive && setFilesError(cause instanceof Error ? cause.message : String(cause)))
      .finally(() => alive && setLoadingFiles(false));
    return () => {
      alive = false;
    };
  }, [mock]);

  const selectedFile = useMemo(() => files.find((file) => file.location === picked) ?? null, [files, picked]);

  const runInfer = useCallback(async () => {
    if (!selectedFile) return;
    setInferring(true);
    setInferError(null);
    setPreview(null);
    try {
      const response = await api.infer({ location: selectedFile.location, mode });
      setOffline(false);
      setPreview(buildImportPreview(response, document, selectedFile.location, mode));
    } catch (cause: unknown) {
      // Unreachable backend (status 0) → offline sample preview; a real 4xx → disabled state.
      if (cause instanceof ApiError && cause.status === 0) {
        const fallback = offlineImportPreview(document, selectedFile.location, mode);
        if (fallback) {
          setOffline(true);
          setPreview(fallback);
        } else {
          setInferError(
            `The studio backend is unreachable, so this file cannot be inferred. Start the backend, or import one of the sample feeds (targets, publications) that carry an offline shape.`,
          );
        }
      } else {
        setInferError(cause instanceof Error ? cause.message : String(cause));
      }
    } finally {
      setInferring(false);
    }
  }, [selectedFile, mode, document]);

  const add = () => {
    if (!preview || preview.totalNew === 0) return;
    apply((draft) => applyImportPreview(draft, preview));
    const first = preview.newTables[0];
    notify({
      level: "info",
      text: `Added ${preview.newTables.length} table${preview.newTables.length === 1 ? "" : "s"} and ${preview.newStructs.length} struct${preview.newStructs.length === 1 ? "" : "s"} from ${preview.location}.`,
    });
    if (first) useSelectionStore.getState().selectAndReveal(`table:${first.id}`);
    onClose();
  };

  return (
    <Panel
      title="Import data shape"
      subtitle={loadingFiles ? "scanning data directory…" : `${files.length} file${files.length === 1 ? "" : "s"}`}
      actions={
        <IconButton size="sm" label="Close" icon={<span className="text-[13px]">×</span>} onClick={onClose} />
      }
    >
      <div className="flex flex-col gap-2">
        <div className="flex items-end gap-2">
          <label className="flex min-w-0 flex-1 flex-col gap-1">
            <span className="text-[11px] uppercase tracking-[0.06em] text-muted">data file</span>
            <Select
              aria-label="data file"
              placeholder={loadingFiles ? "loading…" : "choose a file"}
              value={picked}
              options={files.map((file) => ({ value: file.location, label: `${file.name} · ${file.location}` }))}
              onChange={(event) => {
                setPicked(event.target.value);
                setPreview(null);
                setInferError(null);
              }}
            />
          </label>
          <label className="flex w-40 flex-col gap-1">
            <span className="text-[11px] uppercase tracking-[0.06em] text-muted">as</span>
            <Select
              aria-label="import mode"
              value={mode}
              options={[
                { value: "table", label: "single table" },
                { value: "table_group", label: "table group" },
              ]}
              onChange={(event) => {
                setMode(event.target.value as ImportMode);
                setPreview(null);
              }}
            />
          </label>
          <Button
            variant="primary"
            icon={inferring ? <SpinnerIcon /> : <RefreshIcon />}
            disabled={!selectedFile || inferring}
            onClick={() => void runInfer()}
          >
            infer shape
          </Button>
        </div>

        {filesError && <p className="text-[12px] text-danger">Could not list data files: {filesError}</p>}

        {!selectedFile && !preview && (
          <EmptyState
            title="Pick a data file to infer its shape"
            body="The studio reads nothing off disk — inference runs on the backend (POST /api/infer) and folds the result into the document as tables and structs."
          />
        )}

        {inferError && (
          <div className="flex items-start gap-2 rounded-md border border-warn/50 bg-warn/10 p-2">
            <Chip tone="warn">disabled</Chip>
            <p className="min-w-0 flex-1 text-[12px] leading-snug text-ink">{inferError}</p>
          </div>
        )}

        {preview && <PreviewBody preview={preview} offline={offline} />}

        {preview && (
          <div className="flex items-center justify-end gap-2 border-t border-edge pt-2">
            <Button onClick={onClose}>cancel</Button>
            <Button
              variant="primary"
              icon={<PlusIcon />}
              disabled={preview.totalNew === 0}
              title={preview.totalNew === 0 ? "Nothing new to add — every declaration is already in the project" : undefined}
              onClick={add}
            >
              add to project ({preview.totalNew})
            </Button>
          </div>
        )}
      </div>
    </Panel>
  );
}

function SpinnerIcon() {
  return (
    <svg viewBox="0 0 24 24" width={13} height={13} aria-hidden className="shrink-0 animate-spin">
      <circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" strokeOpacity={0.25} strokeWidth={2} />
      <path d="M20 12a8 8 0 0 0-8-8" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
    </svg>
  );
}

function PreviewBody({ preview, offline }: { preview: ImportPreview; offline: boolean }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-[11px] uppercase tracking-[0.06em] text-muted">
        preview · {preview.location} → {preview.mode === "table_group" ? "table group" : "table"}
        {offline && <span className="ml-2 normal-case text-faint">(offline sample shape)</span>}
      </p>
      {preview.notes.length > 0 && (
        <ul className="flex flex-col gap-0.5">
          {preview.notes.map((note) => (
            <li key={note} className="text-[11px] leading-snug text-warn">{note}</li>
          ))}
        </ul>
      )}
      <div className="flex flex-col gap-1.5">
        {preview.newTables.length === 0 && preview.newStructs.length === 0 && (
          <p className="text-[12px] text-muted">This shape is already declared in the project — nothing to add.</p>
        )}
        {preview.newTables.map((table) => (
          <div key={table.id} className="studio-card p-2">
            <p className="flex items-center gap-2">
              <Chip tone={table.members?.length ? "category" : "node"}>{table.members?.length ? "table group" : "table"}</Chip>
              <span className="min-w-0 truncate font-mono text-[12px] text-ink">{table.name}</span>
              <span className="truncate font-mono text-[10px] text-faint">{table.declaration_name}</span>
            </p>
            <ul className="mt-1 flex flex-wrap gap-1">
              {(table.fields ?? []).map((field) => (
                <li key={field.name}>
                  <Chip title={typeLabel(field.logical_type)}>{`${field.name}: ${typeLabel(field.logical_type)}`}</Chip>
                </li>
              ))}
              {table.members?.map((member) => (
                <li key={member.ref}>
                  <Chip tone="category">{`▸ ${member.python_name}`}</Chip>
                </li>
              ))}
            </ul>
          </div>
        ))}
        {preview.newStructs.map((struct) => (
          <div key={struct.id} className="flex items-center gap-2 rounded-md border border-edge bg-raised px-2 py-1">
            <Chip tone="template">struct</Chip>
            <span className="min-w-0 truncate font-mono text-[12px] text-ink">{struct.name}</span>
            <span className="text-[11px] text-faint">{(struct.fields ?? []).length} members</span>
          </div>
        ))}
        {preview.existingTableIds.length > 0 && (
          <p className={clsx("text-[11px] text-faint")}>
            already present: {preview.existingTableIds.join(", ")}
          </p>
        )}
      </div>
    </div>
  );
}
