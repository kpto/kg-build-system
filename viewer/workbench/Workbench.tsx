"use client";

import { useEffect, useState } from "react";
import { CircleExclamationPoint, LoaderCircle, RefreshCw } from "lucide-react";

import { buildViewerIndex } from "@/lib/indexes";
import { loadSnapshot } from "@/lib/load";
import type { ViewerIndex, ViewerSnapshot } from "@/lib/types";
import { CommandPalette } from "./CommandPalette";
import { EditorArea } from "./EditorArea";
import { SideBar } from "./SideBar";
import { Splitter } from "./Splitter";
import { WorkbenchProvider, useWorkbench } from "./store";
import { MAX_SIDEBAR, MIN_SIDEBAR } from "./types";

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
    <div className="wb-gate ui-grain" data-testid="loading">
      <div className="wb-gate-body">
        <div className="wb-gate-side" aria-hidden>
          <span className="wb-gate-block w-24" />
          <span className="wb-gate-block w-full" />
          <span className="wb-gate-block w-4/5" />
          <span className="wb-gate-block w-full" />
          <span className="wb-gate-block w-2/3" />
        </div>
        <main className="wb-gate-main" role="status" aria-live="polite">
          <div className="wb-gate-card">
            <LoaderCircle aria-hidden className="size-5 animate-spin text-selection" />
            <h1>Loading snapshot</h1>
            <p>Reading the compile-only graph and building indexes.</p>
            <p className="wb-gate-hint">
              The snapshot is read from the configured source; the first paint
              follows the transfer and index build.
            </p>
            {slow ? (
              <p className="wb-gate-slow">
                This is taking longer than usual. The page is still working; you
                can retry the request.
              </p>
            ) : null}
            <button type="button" className="wb-button" onClick={onRetry}>
              <RefreshCw aria-hidden className="size-3" />
              Retry now
            </button>
          </div>
        </main>
      </div>
      <footer className="wb-gate-status">
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
    <div className="wb-gate ui-grain" data-testid="load-error">
      <header className="wb-gate-title">
        <span className="wb-brand-mark" aria-hidden>
          <span className="wb-brand-initial">K</span>
        </span>
        <span className="wb-brand-name">KG Design</span>
        <span className="wb-gate-title-note">viewer</span>
      </header>
      <main className="wb-gate-main">
        <div className="wb-gate-card wb-gate-error">
          <CircleExclamationPoint aria-hidden className="size-6 text-rejected" />
          <h1>Could not load the workbench</h1>
          <p>{message}</p>
          <p className="wb-gate-hint">
            The viewer reads the configured <code>/snapshot</code> source, or a
            URL passed as <code>?snapshot=&lt;url&gt;</code>. Check that source
            and retry.
          </p>
          <button type="button" className="wb-button wb-button-primary" onClick={onRetry}>
            <RefreshCw aria-hidden className="size-3" />
            Retry snapshot
          </button>
        </div>
      </main>
      <footer className="wb-gate-status">
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
    <div className="wb-shell ui-grain" data-testid="workbench">
      <div className="wb-body">
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

        <div className="wb-main">
          <EditorArea
            sidebarVisible={sidebarVisible}
            onToggleSidebar={() => setSidebarVisible((visible) => !visible)}
          />
        </div>
      </div>

      {paletteOpen ? <CommandPalette onClose={() => setPaletteOpen(false)} /> : null}
    </div>
  );
}

export function Workbench() {
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | undefined>();
  const [loaded, setLoaded] = useState<LoadedWorkbench | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(undefined);
    setLoaded(null);

    const requested =
      typeof window === "undefined"
        ? ""
        : new URLSearchParams(window.location.search).get("snapshot") ?? "";

    loadSnapshot(requested)
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
  }, [attempt]);

  if (loading) {
    return <LoadingGate onRetry={() => setAttempt((value) => value + 1)} />;
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
      key={`${loaded.snapshot.name}:${attempt}`}
      snapshot={loaded.snapshot}
      index={loaded.index}
    >
      <WorkbenchShell />
    </WorkbenchProvider>
  );
}

