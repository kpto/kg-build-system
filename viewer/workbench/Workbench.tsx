"use client";

import { useCallback, useEffect, useMemo, useState, type CSSProperties } from "react";
import {
  CircleExclamationPoint,
  FileText,
  LoaderCircle,
  Network,
  RefreshCw,
} from "lucide-react";

import { buildViewerIndex } from "@/lib/indexes";
import {
  loadDefaultSnapshot,
  loadReferenceSnapshot,
} from "@/lib/load";
import type { ViewerIndex, ViewerSnapshot } from "@/lib/types";
import { BottomPanel } from "./BottomPanel";
import { CommandPalette } from "./CommandPalette";
import { defaultBottomTab } from "./defaults";
import { EditorArea } from "./EditorArea";
import { SettingsDialog } from "./SettingsDialog";
import { SideBar } from "./SideBar";
import { Splitter } from "./Splitter";
import { StatusBar } from "./StatusBar";
import { WorkbenchProvider, useWorkbench } from "./store";
import { TitleBar } from "./TitleBar";
import {
  DEFAULT_LAYOUT,
  MAX_BOTTOM,
  MAX_SIDEBAR,
  MIN_BOTTOM,
  MIN_SIDEBAR,
} from "./types";

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
      <header className="wb-gate-title">
        <span className="wb-brand-mark" aria-hidden>
          <span className="wb-brand-initial">K</span>
        </span>
        <span className="wb-brand-name">KG Design</span>
        <span className="wb-gate-title-note">viewer</span>
      </header>
      <div className="wb-gate-body">
        <div className="wb-gate-rail" aria-hidden>
          <Network className="size-[18px]" />
          <FileText className="size-[18px]" />
        </div>
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
              Open Targets is served gzipped; the first paint follows the
              decompression and index build.
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
            The default snapshot is served from <code>/api/snapshot</code> with a
            plain JSON fallback. Retry after checking the route.
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
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sidebarVisible, setSidebarVisible] = useState(true);
  const [bottomVisible, setBottomVisible] = useState(true);
  const [zoom, setZoom] = useState(1);

  const layout = state.layout;

  const openPalette = useCallback(() => {
    setSettingsOpen(false);
    setPaletteOpen(true);
  }, []);

  const openSettings = useCallback(() => {
    setPaletteOpen(false);
    setSettingsOpen(true);
  }, []);

  const resetLayout = useCallback(() => {
    actions.setLayout({
      sidebarWidth: DEFAULT_LAYOUT.sidebarWidth,
      bottomHeight: DEFAULT_LAYOUT.bottomHeight,
    });
    actions.setBottomTab("graph", defaultBottomTab("graph"));
    actions.setBottomTab("subject", defaultBottomTab("subject"));
  }, [actions]);

  useEffect(() => {
    const onKeyDown = (event: globalThis.KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const textEntry =
        target?.closest("input, textarea, select, [contenteditable='true']") ?? null;
      const command = event.metaKey || event.ctrlKey;

      if (command && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSettingsOpen(false);
        setPaletteOpen((open) => !open);
        return;
      }
      if (command && event.key === ",") {
        event.preventDefault();
        setPaletteOpen(false);
        setSettingsOpen(true);
        return;
      }
      if (textEntry) {
        if (event.key === "Escape") {
          setPaletteOpen(false);
          setSettingsOpen(false);
        }
        return;
      }
      if (command && event.key.toLowerCase() === "b") {
        event.preventDefault();
        setSidebarVisible((visible) => !visible);
        return;
      }
      if (command && event.key.toLowerCase() === "j") {
        event.preventDefault();
        setBottomVisible((visible) => !visible);
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
        setSettingsOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [actions]);

  const bodyStyle = useMemo<CSSProperties | undefined>(() => {
    if (zoom === 1) return undefined;
    return {
      zoom,
      width: `calc(100% / ${zoom})`,
      height: `calc((100vh - 60px) / ${zoom})`,
    };
  }, [zoom]);

  return (
    <div className="wb-shell ui-grain" data-testid="workbench">
      <TitleBar
        onOpenPalette={openPalette}
        onOpenSettings={openSettings}
        sidebarVisible={sidebarVisible}
        bottomVisible={bottomVisible}
        onToggleSidebar={() => setSidebarVisible((visible) => !visible)}
        onToggleBottom={() => setBottomVisible((visible) => !visible)}
        onResetLayout={resetLayout}
      />

      <div className="wb-body" style={bodyStyle}>
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
          <EditorArea />
          {bottomVisible ? (
            <>
              <Splitter
                orientation="horizontal"
                value={layout.bottomHeight}
                min={MIN_BOTTOM}
                max={MAX_BOTTOM}
                label="Resize bottom panel"
                onChange={(value) => actions.setLayout({ bottomHeight: value })}
              />
              <BottomPanel onCollapse={() => setBottomVisible(false)} />
            </>
          ) : null}
        </div>
      </div>

      <StatusBar
        zoom={zoom}
        onZoomIn={() => setZoom((value) => Math.min(1.3, Math.round((value + 0.1) * 10) / 10))}
        onZoomOut={() => setZoom((value) => Math.max(0.8, Math.round((value - 0.1) * 10) / 10))}
        onZoomReset={() => setZoom(1)}
      />

      {paletteOpen ? <CommandPalette onClose={() => setPaletteOpen(false)} /> : null}
      {settingsOpen ? <SettingsDialog onClose={() => setSettingsOpen(false)} /> : null}
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
        ? null
        : new URLSearchParams(window.location.search).get("snapshot");
    const reference = requested === "reference";

    (reference ? loadReferenceSnapshot() : loadDefaultSnapshot())
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

