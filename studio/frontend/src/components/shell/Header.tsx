"use client";

import { forwardRef } from "react";
import clsx from "clsx";

import { Button, IconButton, PanelIcon, ListIcon, RedoIcon, SearchIcon, UndoIcon, Tooltip } from "@/components/ui";
import type { ProjectDocument } from "@/lib/ir";
import { documentCounts } from "@/lib/ir";
import type { Notice } from "@/lib/types";
import type { SocketState, StatusLight as StatusLightModel } from "@/stores/connectionStore";
import { StatusLight } from "./StatusLight";

export interface HeaderProps {
  document: ProjectDocument | null;
  revision: number;
  dirty: boolean;
  sending: boolean;
  mock: boolean;
  light: StatusLightModel;
  socket: SocketState;
  notices: Notice[];
  canUndo: boolean;
  canRedo: boolean;
  onUndo(): void;
  onRedo(): void;
  onDismissNotice(id: string): void;
  inspectorOpen: boolean;
  onToggleInspector(): void;
  problemsOpen: boolean;
  onToggleProblems(): void;
  problemCount: number;
  searchValue: string;
  onSearchChange(value: string): void;
  onSearchFocus(): void;
  paletteOpen: boolean;
}

const SOCKET_LABEL: Record<SocketState, string> = {
  open: "connected",
  connecting: "connecting",
  closed: "disconnected",
  error: "socket error",
  off: "offline",
};

/**
 * The shell header: what project this is, what revision the copy is at, whether the
 * backend is reachable, and the two global affordances (undo/redo, search).
 *
 * Everything here is a fact from the stores; the header owns no state of its own
 * except the search input's value, which the palette reads.
 */
export const Header = forwardRef<HTMLInputElement, HeaderProps>(function Header(props, searchRef) {
  const {
    document,
    revision,
    dirty,
    sending,
    mock,
    light,
    socket,
    notices,
    canUndo,
    canRedo,
    onUndo,
    onRedo,
    onDismissNotice,
    inspectorOpen,
    onToggleInspector,
    problemsOpen,
    onToggleProblems,
    problemCount,
    searchValue,
    onSearchChange,
    paletteOpen,
  } = props;

  const counts = documentCounts(document);
  const saved = !dirty && !sending;

  return (
    <>
    <header className="flex h-11 shrink-0 items-center gap-3 border-b border-edge bg-surface px-3">
      <div className="flex min-w-0 items-baseline gap-2">
        <span className="shrink-0 font-mono text-[11px] uppercase tracking-[0.14em] text-faint">
          kg studio
        </span>
        <h1 className="truncate text-[13px] font-semibold text-ink">
          {document?.project.name ?? "No project"}
        </h1>
        <span className="shrink-0 font-mono text-[11px] text-muted">rev {revision}</span>
        {mock && (
          <span
            className="studio-chip shrink-0 border-template/60 bg-template/10 text-template"
            title="Loaded from the built-in sample project; writes are local only"
          >
            mock
          </span>
        )}
        {document && (
          <span className="hidden shrink-0 gap-1.5 font-mono text-[11px] text-faint xl:flex">
            {[
              `${counts.components} component${counts.components === 1 ? "" : "s"}`,
              `${counts.bindings} binding${counts.bindings === 1 ? "" : "s"}`,
              `${counts.tables} table${counts.tables === 1 ? "" : "s"}`,
              `${counts.projections} projection${counts.projections === 1 ? "" : "s"}`,
              `${counts.sources} source${counts.sources === 1 ? "" : "s"}`,
              `${counts.modules} module${counts.modules === 1 ? "" : "s"}`,
            ].join(" · ")}
          </span>
        )}
      </div>

      <div className="ml-auto flex shrink-0 items-center gap-2.5">
        <StatusLight level={light.level} label={light.label} lines={light.lines} />

        <span
          className={clsx(
            "font-mono text-[11px]",
            saved ? "text-faint" : sending ? "text-info" : "text-warn",
          )}
          title={
            saved
              ? "Every local edit is acknowledged by the backend"
              : sending
                ? "Saving the coalesced edit"
                : "Local edits not yet sent"
          }
        >
          {sending ? "saving…" : dirty ? "unsaved" : "saved"}
        </span>

        {!mock && (
          <span
            className={clsx(
              "font-mono text-[11px]",
              socket === "open" ? "text-ok" : socket === "connecting" ? "text-warn" : "text-faint",
            )}
            title={`WebSocket ${SOCKET_LABEL[socket]}`}
          >
            {SOCKET_LABEL[socket]}
          </span>
        )}

        <div
          role="search"
          className={clsx(
            "flex h-7 w-64 items-center gap-1.5 rounded-md border bg-raised px-2 transition-colors",
            paletteOpen ? "border-info" : "border-edge hover:border-edge-strong",
          )}
        >
          <SearchIcon className="text-faint" />
          <input
            ref={searchRef}
            type="search"
            value={searchValue}
            aria-label="Find IR entities, opens the command palette"
            placeholder="find entity…"
            autoComplete="off"
            spellCheck={false}
            onChange={(event) => onSearchChange(event.target.value)}
            className="min-w-0 flex-1 bg-transparent text-[12px] text-ink outline-none placeholder:text-faint [&::-webkit-search-cancel-button]:hidden"
          />
          <kbd className="rounded border border-edge bg-overlay px-1 font-mono text-[9px] text-faint">
            /
          </kbd>
        </div>

        <div className="flex items-center gap-1">
          <Tooltip content={canUndo ? "Undo (Ctrl+Z)" : "Nothing to undo"}>
            <IconButton label="Undo" icon={<UndoIcon />} disabled={!canUndo} onClick={onUndo} />
          </Tooltip>
          <Tooltip content={canRedo ? "Redo (Ctrl+Shift+Z)" : "Nothing to redo"}>
            <IconButton label="Redo" icon={<RedoIcon />} disabled={!canRedo} onClick={onRedo} />
          </Tooltip>
          <Tooltip content={problemsOpen ? "Hide problems" : "Show problems"}>
            <IconButton
              label="Problems"
              icon={<ListIcon />}
              active={problemsOpen}
              onClick={onToggleProblems}
            />
          </Tooltip>
          <Tooltip content={inspectorOpen ? "Hide inspector" : "Show inspector"}>
            <IconButton
              label="Inspector"
              icon={<PanelIcon />}
              active={inspectorOpen}
              onClick={onToggleInspector}
            />
          </Tooltip>
        </div>
      </div>

      <span className="sr-only">{problemCount} problems in total</span>
    </header>

      {/* Notices float over the canvas, anchored bottom-left so they never cover the
          inspector or the status line they are about. */}
      {notices.length > 0 && (
        <div
          role="status"
          aria-live="polite"
          className="pointer-events-none fixed bottom-10 left-14 z-40 flex w-[26rem] flex-col gap-1"
        >
          {notices.map((notice) => (
            <div
              key={notice.id}
              className={clsx(
                "studio-card flex items-start gap-2 px-2.5 py-2 text-[12px]",
                notice.level === "error" && "border-danger/60",
                notice.level === "warn" && "border-warn/60",
              )}
            >
              <span
                className={clsx(
                  "mt-1 h-1.5 w-1.5 shrink-0 rounded-full",
                  notice.level === "error" ? "bg-danger" : notice.level === "warn" ? "bg-warn" : "bg-info",
                )}
                aria-hidden
              />
              <p className="min-w-0 flex-1 leading-snug text-ink">{notice.text}</p>
              <Button size="sm" variant="ghost" onClick={() => onDismissNotice(notice.id)}>
                dismiss
              </Button>
            </div>
          ))}
        </div>
      )}
    </>
  );
});
