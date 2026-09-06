"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Button, EmptyState, Field, Skeleton, TextInput } from "@/components/ui";
import { TAB_AREAS, type FeatureProps, type TabArea } from "@/lib/types";
import { areaForRef, useSelectionStore } from "@/stores/selectionStore";
import { statusLight, useConnectionStore } from "@/stores/connectionStore";
import {
  selectCanRedo,
  selectCanUndo,
  useDocumentStore,
} from "@/stores/documentStore";
import { problemsForArea, useProblemStore } from "@/stores/problemStore";
import { useIndexStore } from "@/stores/indexStore";
import { backendOrigin, useStudioSession } from "./useStudioSession";
import { CommandPalette } from "./CommandPalette";
import { Header } from "./Header";
import { InspectorDock } from "./InspectorDock";
import { NavRail } from "./NavRail";
import { ProblemsPanel } from "./ProblemsPanel";
import { FEATURE_AREAS } from "./featureAreas";

/**
 * The studio shell.
 *
 * It owns the frame (rail, header, feature area, inspector dock, problems panel), the
 * global key map and the split of `FeatureProps` handed to each area. It owns no
 * document logic: every write goes through the document store, every read through a
 * store selector, so an area can be replaced without touching this file.
 */
export function StudioShell() {
  const session = useStudioSession();
  const document = useDocumentStore((state) => state.document);
  const revision = useDocumentStore((state) => state.revision);
  const dirty = useDocumentStore((state) => state.dirty);
  const sending = useDocumentStore((state) => state.sending);
  const loading = useDocumentStore((state) => state.loading);
  const mock = useDocumentStore((state) => state.mock);
  const apply = useDocumentStore((state) => state.apply);
  const undo = useDocumentStore((state) => state.undo);
  const redo = useDocumentStore((state) => state.redo);
  const canUndo = useDocumentStore(selectCanUndo);
  const canRedo = useDocumentStore(selectCanRedo);

  // The light is derived, so it is memoised here rather than returned from a
  // selector: a selector that builds a new object per snapshot makes
  // `useSyncExternalStore` believe the store never settles.
  const status = useConnectionStore((state) => state.status);
  const generation = useConnectionStore((state) => state.generation);
  const socket = useConnectionStore((state) => state.socket);
  const notices = useConnectionStore((state) => state.notices);
  const dismissNotice = useConnectionStore((state) => state.dismissNotice);

  const area = useSelectionStore((state) => state.area);
  const setArea = useSelectionStore((state) => state.setArea);
  const selectedRef = useSelectionStore((state) => state.selectedRef);
  const select = useSelectionStore((state) => state.select);

  const allProblems = useProblemStore((state) => state.problems);
  const index = useIndexStore((state) => state.index);

  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [problemsOpen, setProblemsOpen] = useState(true);
  const [query, setQuery] = useState("");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const searchRef = useRef<HTMLInputElement | null>(null);
  const light = useMemo(
    () => statusLight(status, { generation, dirty }),
    [status, generation, dirty],
  );

  /* ------------------------------------------------------------ global key map */

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing =
        target !== null &&
        (target.isContentEditable ||
          target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.tagName === "SELECT");

      const meta = event.ctrlKey || event.metaKey;
      if (meta && event.key.toLowerCase() === "z") {
        event.preventDefault();
        if (event.shiftKey) redo();
        else undo();
        return;
      }
      if (meta && event.key.toLowerCase() === "y") {
        event.preventDefault();
        redo();
        return;
      }
      if (typing) {
        if (event.key === "Escape") (target as HTMLInputElement).blur();
        return;
      }
      if (event.key === "/") {
        event.preventDefault();
        setPaletteOpen(true);
        searchRef.current?.focus();
        return;
      }
      if (event.key === "Escape") {
        setPaletteOpen(false);
        return;
      }
      // 1–7 select the seven areas; they are unmodified digits only, so the browser's
      // own Ctrl+1..7 tab switching stays intact.
      if (!meta && event.altKey === false) {
        const position = Number.parseInt(event.key, 10);
        if (Number.isInteger(position) && position >= 1 && position <= TAB_AREAS.length) {
          event.preventDefault();
          const tab = TAB_AREAS[position - 1];
          if (tab) setArea(tab);
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [undo, redo, setArea]);

  /* ------------------------------------------------------------- FeatureProps */

  const onSelectRef = useCallback(
    (ref: string | null) => {
      select(ref);
      const owner = areaForRef(ref);
      if (owner && owner !== area) setArea(owner);
    },
    [select, setArea, area],
  );

  const areaProblems = useMemo(
    () => problemsForArea(useProblemStore.getState(), area),
    [allProblems, area],
  );

  const perAreaProblems = useMemo(() => {
    const state = useProblemStore.getState();
    const out: Partial<Record<TabArea, { errors: number; warnings: number }>> = {};
    for (const tab of TAB_AREAS) {
      const list = problemsForArea(state, tab);
      out[tab] = {
        errors: list.filter((problem) => problem.severity === "error").length,
        warnings: list.filter((problem) => problem.severity === "warning").length,
      };
    }
    return out;
  }, [allProblems]);

  const featureProps: FeatureProps | null = useMemo(
    () =>
      document
        ? {
            document,
            index,
            problems: areaProblems,
            selectedRef,
            onSelectRef,
            apply,
          }
        : null,
    [document, index, areaProblems, selectedRef, onSelectRef, apply],
  );

  /* --------------------------------------------------------------- rendering */

  if (session.mock === null || (loading && !document)) {
    return (
      <div className="flex h-full flex-col gap-3 p-6">
        <div className="h-8 w-64 rounded bg-raised" />
        <Skeleton lines={8} height={14} />
      </div>
    );
  }

  const Feature = FEATURE_AREAS[area];

  return (
    <div className="flex h-full min-h-0 w-full flex-col bg-canvas">
      <Header
        ref={searchRef}
        document={document}
        revision={revision}
        dirty={dirty}
        sending={sending}
        mock={mock}
        light={light}
        socket={session.mock ? "off" : socket}
        notices={notices}
        canUndo={canUndo}
        canRedo={canRedo}
        onUndo={undo}
        onRedo={redo}
        onDismissNotice={dismissNotice}
        inspectorOpen={inspectorOpen}
        onToggleInspector={() => setInspectorOpen((value) => !value)}
        problemsOpen={problemsOpen}
        onToggleProblems={() => setProblemsOpen((value) => !value)}
        problemCount={allProblems.length}
        searchValue={query}
        onSearchChange={(value) => {
          setQuery(value);
          setPaletteOpen(true);
        }}
        onSearchFocus={() => setPaletteOpen(true)}
        paletteOpen={paletteOpen}
      />

      <div className="flex min-h-0 flex-1">
        <NavRail area={area} onSelect={setArea} badges={perAreaProblems} />

        <main className="flex min-w-0 flex-1 flex-col">
          {featureProps && document ? (
            <div
              key={area}
              id={`panel-${area}`}
              role="tabpanel"
              aria-labelledby={`rail-${area}`}
              className="flex min-h-0 flex-1 flex-col"
            >
              <Feature {...featureProps} />
            </div>
          ) : (
            <NoProject session={session} />
          )}

          <ProblemsPanel
            open={problemsOpen}
            onToggle={() => setProblemsOpen((value) => !value)}
            onClose={() => setProblemsOpen(false)}
          />
        </main>

        {document && (
          <InspectorDock
            document={document}
            selectedRef={selectedRef}
            open={inspectorOpen}
            onToggle={() => setInspectorOpen((value) => !value)}
            onSelectRef={onSelectRef}
            apply={apply}
          />
        )}
      </div>

      {document && (
        <CommandPalette
          open={paletteOpen}
          query={query}
          onQueryChange={setQuery}
          document={document}
          problems={allProblems}
          onClose={() => {
            setPaletteOpen(false);
            searchRef.current?.blur();
          }}
        />
      )}
    </div>
  );
}

/**
 * The no-workspace state: the backend is unreachable or has no project yet. Both are
 * fixed the same way — `POST /api/workspace` — so the shell offers exactly one action
 * and never renders a half-editor with nothing behind it.
 */
function NoProject({ session }: { session: ReturnType<typeof useStudioSession> }) {
  const [root, setRoot] = useState("/tmp/kg-studio-project");
  const [name, setName] = useState("New project");
  const [pkg, setPkg] = useState("kg_project");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const create = async () => {
    setBusy(true);
    setFailure(null);
    try {
      await session.createProject({ project_root: root, package: pkg, name });
    } catch (error) {
      setFailure(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  };

  const offline = Boolean(session.error);

  return (
    <EmptyState
      className="h-full"
      title={offline ? "The studio backend is not reachable" : "No project open"}
      body={
        offline ? (
          <span>
            Nothing answered at <code className="font-mono text-info">{backendOrigin}</code>. Start
            it with <code className="font-mono text-info">kg-studio serve --project &lt;dir&gt;</code>,
            reload this page — or load the built-in sample project with{" "}
            <code className="font-mono text-info">?mock=1</code> to work without a backend at all.
          </span>
        ) : (
          <span>
            Create a project to start authoring: the studio writes{" "}
            <code className="font-mono text-info">project.ir.json</code> at that root and generates
            the Python project from it.
          </span>
        )
      }
      actions={
        <>
          <Button
            variant="primary"
            disabled={busy || offline}
            title={offline ? "Needs a backend to write the workspace into" : "POST /api/workspace"}
            onClick={() => void create()}
          >
            {busy ? "creating…" : "Create project"}
          </Button>
          <Button onClick={session.reload}>Retry connection</Button>
        </>
      }
    >
      <div className="flex w-96 flex-col gap-1.5">
        <Field label="project root" htmlFor="new-project-root">
          <TextInput id="new-project-root" mono value={root} onChange={(event) => setRoot(event.target.value)} />
        </Field>
        <Field label="name" htmlFor="new-project-name">
          <TextInput id="new-project-name" value={name} onChange={(event) => setName(event.target.value)} />
        </Field>
        <Field label="package" htmlFor="new-project-package" hint="snake_case import path of the generated project">
          <TextInput id="new-project-package" mono value={pkg} onChange={(event) => setPkg(event.target.value)} />
        </Field>
        {failure && <p className="text-[12px] text-danger">{failure}</p>}
      </div>
    </EmptyState>
  );
}

