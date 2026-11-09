"use client";

import { Boxes, PanelBottom, PanelLeft, RotateCcw, Search } from "lucide-react";

import { ACTIVITY_LABELS } from "./defaults";
import { useWorkbench } from "./store";

export interface TitleBarProps {
  onOpenPalette(): void;
  sidebarVisible: boolean;
  bottomVisible: boolean;
  onToggleSidebar(): void;
  onToggleBottom(): void;
  onResetLayout(): void;
}

export function TitleBar({
  onOpenPalette,
  sidebarVisible,
  bottomVisible,
  onToggleSidebar,
  onToggleBottom,
  onResetLayout,
}: TitleBarProps) {
  const { state } = useWorkbench();
  const snapshot = state.snapshot;

  return (
    <header className="wb-titlebar" aria-label="Workbench title bar">
      <div className="wb-brand" title="KG Audit workbench">
        <span className="wb-brand-mark" aria-hidden>
          <Boxes className="size-4" />
        </span>
        <span className="wb-brand-name">KG Audit</span>
        <span className="wb-brand-crumb">{ACTIVITY_LABELS[state.activity]}</span>
      </div>

      <div className="wb-snapshot" title={snapshot.title}>
        <span className="wb-snapshot-name">{snapshot.name}</span>
        <span className="wb-snapshot-title">{snapshot.title}</span>
      </div>

      <button
        type="button"
        className="wb-command"
        onClick={onOpenPalette}
        aria-label="Search commands and subjects"
        title="Search commands and subjects (Ctrl/Cmd+K)"
        data-testid="command-trigger"
      >
        <Search aria-hidden className="size-3.5" />
        <span className="wb-command-placeholder">Search commands and subjects</span>
        <kbd className="wb-kbd">Ctrl K</kbd>
      </button>

      <div className="wb-layout-controls" role="group" aria-label="Layout controls">
        <button
          type="button"
          className="wb-icon-button"
          onClick={onToggleSidebar}
          aria-label={sidebarVisible ? "Hide side bar" : "Show side bar"}
          aria-pressed={sidebarVisible}
          title={sidebarVisible ? "Hide side bar (Ctrl/Cmd+B)" : "Show side bar (Ctrl/Cmd+B)"}
        >
          <PanelLeft aria-hidden className="size-4" />
        </button>
        <button
          type="button"
          className="wb-icon-button"
          onClick={onToggleBottom}
          aria-label={bottomVisible ? "Hide bottom panel" : "Show bottom panel"}
          aria-pressed={bottomVisible}
          title={bottomVisible ? "Hide bottom panel (Ctrl/Cmd+J)" : "Show bottom panel (Ctrl/Cmd+J)"}
        >
          <PanelBottom aria-hidden className="size-4" />
        </button>
        <button
          type="button"
          className="wb-icon-button"
          onClick={onResetLayout}
          aria-label="Reset this function's layout"
          title="Reset this function's layout"
        >
          <RotateCcw aria-hidden className="size-4" />
        </button>
      </div>
    </header>
  );
}
