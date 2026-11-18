"use client";

import { useEffect, useMemo, useState } from "react";
import { CircleExclamationPoint, LoaderCircle, RefreshCw } from "lucide-react";

import type { ConceptTarget } from "@/lib/concepts";
import { buildViewerIndex } from "@/lib/indexes";
import { loadSnapshot } from "@/lib/load";
import type { ViewerIndex, ViewerSnapshot } from "@/lib/types";
import { ConceptNavigationProvider } from "@/shared/ui/ConceptNavigation";
import { ConceptPreviewProvider } from "@/shared/ui/ConceptPreview";
import { cx } from "@kbs/design";
import { CommandPalette } from "./CommandPalette";
import { EditorArea } from "./EditorArea";
import { SideBar } from "./SideBar";
import { Splitter } from "./Splitter";
import { previewForConceptTarget } from "./conceptPreview";
import { destinationForConceptTarget } from "./conceptTarget";
import { WorkbenchProvider, useWorkbench } from "./store";
import { MAX_SIDEBAR, MIN_SIDEBAR } from "./types";
import styles from "./workbench.module.css";

interface LoadedWorkbench {
  snapshot: ViewerSnapshot;
  index: ViewerIndex;
}

function LoadingGate({ onRetry }: { onRetry(): void }) {
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setSlow(true), 6000);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <div className={cx(styles.gate, "ui-grain")} data-testid="loading">
      <div className={styles.gateBody}>
        <div className={styles.gateSide} aria-hidden>
          <span className={cx(styles.gateBlock, "w-24")} />
          <span className={cx(styles.gateBlock, "w-full")} />
          <span className={cx(styles.gateBlock, "w-4/5")} />
          <span className={cx(styles.gateBlock, "w-full")} />
          <span className={cx(styles.gateBlock, "w-2/3")} />
        </div>
        <main className={styles.gateMain} role="status" aria-live="polite">
          <div className={styles.gateCard}>
            <LoaderCircle aria-hidden className="size-5 animate-spin text-selection" />
            <h1>Loading snapshot</h1>
            <p>Reading the compile-only graph and building indexes.</p>
            <p className={styles.gateHint}>
              The snapshot is read from the configured source; the first paint
              follows the transfer and index build.
            </p>
            {slow ? (
              <p className={styles.gateSlow}>
                This is taking longer than usual. The page is still working;
                you can retry the request.
              </p>
            ) : null}
            <button type="button" className={styles.button} onClick={onRetry}>
              <RefreshCw aria-hidden className="size-3" />
              Retry now
            </button>
          </div>
        </main>
      </div>
      <footer className={styles.gateStatus}>
        <span>snapshot loading</span>
        <span>compile-only</span>
      </footer>
    </div>
  );
}

function LoadErrorGate({
  message,
  onRetry,
}: {
  message: string;
  onRetry(): void;
}) {
  return (
    <div className={cx(styles.gate, "ui-grain")} data-testid="load-error">
      <header className={styles.gateTitle}>
        <span className={styles.brandMark} aria-hidden>
          <span className={styles.brandInitial}>K</span>
        </span>
        <span className={styles.brandName}>KG Design</span>
        <span className={styles.gateTitleNote}>viewer</span>
      </header>
      <main className={styles.gateMain}>
        <div className={cx(styles.gateCard, styles.gateError)}>
          <CircleExclamationPoint aria-hidden className="size-6 text-rejected" />
          <h1>Could not load the workbench</h1>
          <p>{message}</p>
          <p className={styles.gateHint}>
            The viewer reads the configured <code>/snapshot</code> source, or a
            URL passed as <code>?snapshot=&lt;url&gt;</code>. Check that source
            and retry.
          </p>
          <button type="button" className={cx(styles.button, styles.buttonPrimary)} onClick={onRetry}>
            <RefreshCw aria-hidden className="size-3" />
            Retry snapshot
          </button>
        </div>
      </main>
      <footer className={styles.gateStatus}>
        <span>snapshot unavailable</span>
        <span>no graph loaded</span>
      </footer>
    </div>
  );
}

function WorkbenchShell() {
  const { state, actions } = useWorkbench();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [sidebarVisible, setSidebarVisible] = useState(true);

  const layout = state.layout;
  const conceptPreview = useMemo(
    () => ({
      preview: (target: ConceptTarget) =>
        previewForConceptTarget(state.index, target),
    }),
    [state.index],
  );

  const conceptNavigation = useMemo(
    () => ({
      open: (
        target: ConceptTarget,
        options?: { background?: boolean },
      ) => {
        const destination = destinationForConceptTarget(state.index, target);
        if (!destination) return;
        if (destination.kind === "graph") {
          if (!options?.background) actions.showGraph({});
          return;
        }
        if (destination.kind === "workflow") {
          if (!options?.background) actions.showWorkflow();
          return;
        }
        actions.openTab(
          options?.background
            ? { selection: destination.selection, background: true }
            : { selection: destination.selection, preview: true },
        );
      },
    }),
    [actions, state.index],
  );

  useEffect(() => {
    const onKeyDown = (event: globalThis.KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const textEntry =
        target?.closest("input, textarea, select, [contenteditable='true']") ?? null;
      const command = event.metaKey || event.ctrlKey;

      if (command && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((open) => !open);
        return;
      }
      if (textEntry) {
        if (event.key === "Escape") setPaletteOpen(false);
        return;
      }
      if (command && event.key.toLowerCase() === "b") {
        event.preventDefault();
        setSidebarVisible((visible) => !visible);
        return;
      }
      if (event.altKey && event.key === "ArrowLeft") {
        event.preventDefault();
        actions.back();
        return;
      }
      if (event.altKey && event.key === "ArrowRight") {
        event.preventDefault();
        actions.forward();
        return;
      }
      if (event.key === "Escape") {
        setPaletteOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [actions]);

  // Mouse back/forward buttons are document navigation, like a browser.
  useEffect(() => {
    const onMouseDown = (event: globalThis.MouseEvent) => {
      if (event.button === 3 || event.button === 4) event.preventDefault();
    };
    const onMouseUp = (event: globalThis.MouseEvent) => {
      if (event.button === 3) {
        event.preventDefault();
        actions.back();
      } else if (event.button === 4) {
        event.preventDefault();
        actions.forward();
      }
    };
    window.addEventListener("mousedown", onMouseDown);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousedown", onMouseDown);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [actions]);

  return (
    <ConceptPreviewProvider value={conceptPreview}>
      <ConceptNavigationProvider navigation={conceptNavigation}>
        <div className={cx(styles.shell, "ui-grain")} data-testid="workbench">
          <div className={styles.body}>
            {sidebarVisible ? (
              <>
                <SideBar />
                <Splitter
                  orientation="vertical"
                  value={layout.sidebarWidth}
                  min={MIN_SIDEBAR}
                  max={MAX_SIDEBAR}
                  label="Resize side bar"
                  onChange={(value) => actions.setLayout({ sidebarWidth: value })}
                />
              </>
            ) : null}

            <div className={styles.main}>
              <EditorArea
                sidebarVisible={sidebarVisible}
                onToggleSidebar={() => setSidebarVisible((visible) => !visible)}
              />
            </div>
          </div>

          {paletteOpen ? (
            <CommandPalette onClose={() => setPaletteOpen(false)} />
          ) : null}
        </div>
      </ConceptNavigationProvider>
    </ConceptPreviewProvider>
  );
}

export function Workbench() {
  const [attempt, setAttempt] = useState(0);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | undefined>();
  const [loaded, setLoaded] = useState<LoadedWorkbench | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const requestedUrl = useMemo(
    () =>
      typeof window === "undefined"
        ? ""
        : new URLSearchParams(window.location.search).get("snapshot") ?? "",
    [],
  );
  useEffect(() => {
    if (!mounted) return;
    let active = true;
    setLoading(true);
    setError(undefined);
    setLoaded(null);

    loadSnapshot(requestedUrl)
      .then((snapshot) => {
        if (!active) return;
        setLoaded({
          snapshot,
          index: buildViewerIndex(snapshot),
        });
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setError(reason instanceof Error ? reason.message : String(reason));
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [attempt, mounted, requestedUrl]);

  if (loading) {
    return (
      <LoadingGate onRetry={() => setAttempt((value) => value + 1)} />
    );
  }
  if (error || !loaded) {
    return (
      <LoadErrorGate
        message={error ?? "No snapshot was loaded."}
        onRetry={() => setAttempt((value) => value + 1)}
      />
    );
  }

  return (
    <WorkbenchProvider
      key={`${loaded.snapshot.name}:${attempt}:${revision}`}
      snapshot={loaded.snapshot}
      index={loaded.index}
    >
      <WorkbenchShell />
    </WorkbenchProvider>
  );
}

