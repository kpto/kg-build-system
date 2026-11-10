"use client";

import { Boxes, PanelBottom, PanelLeft, RotateCcw, Search, Settings } from "lucide-react";

import { useWorkbench } from "./store";

export interface TitleBarProps {
  onOpenPalette(): void;
  onOpenSettings(): void;
  sidebarVisible: boolean;
  bottomVisible: boolean;
  onToggleSidebar(): void;
  onToggleBottom(): void;
  onResetLayout(): void;
}

export function TitleBar({
  onOpenPalette,
  onOpenSettings,
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
      <div className="wb-brand" title="KG design viewer">
        <span className="wb-brand-mark" aria-hidden>
          <Boxes className="size-4" />
        </span>
        <span className="wb-brand-name">KG Design</span>
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
          aria-label="Reset the workbench layout"
          title="Reset the workbench layout"
        >
          <RotateCcw aria-hidden className="size-4" />
        </button>
        <button
          type="button"
          className="wb-icon-button"
          onClick={onOpenSettings}
          aria-label="Settings"
          title="Settings (Ctrl/Cmd+,)"
        >
          <Settings aria-hidden className="size-4" />
        </button>
      </div>
    </header>
  );
}
