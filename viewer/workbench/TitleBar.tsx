"use client";

import { Boxes, Database, FolderOpen, PanelLeft, Search, Settings } from "lucide-react";

import { useWorkbench } from "./store";

export interface TitleBarProps {
  onOpenPalette(): void;
  onOpenSettings(): void;
  onOpenWorkflowFile(): void;
  sidebarVisible: boolean;
  onToggleSidebar(): void;
}

export function TitleBar({
  onOpenPalette,
  onOpenSettings,
  onOpenWorkflowFile,
  sidebarVisible,
  onToggleSidebar,
}: TitleBarProps) {
  const { state } = useWorkbench();
  const snapshot = state.snapshot;
  const built = (snapshot.report?.published_artifacts.length ?? 0) > 0;

  return (
    <header className="wb-titlebar" aria-label="Workbench title bar">
      <div className="wb-brand" title="KG design viewer">
        <span className="wb-brand-mark" aria-hidden>
          <Boxes className="size-4" />
        </span>
        <span className="wb-brand-name">KG Design</span>
      </div>

      <span className="wb-snapshot" title={snapshot.title}>
        <Database aria-hidden className="size-3" />
        <span className="wb-snapshot-name">{snapshot.name}</span>
        <span
          className="wb-snapshot-mode"
          title={
            built
              ? "Snapshot carries a build report"
              : "Compile-only snapshot: it carries no execution report"
          }
        >
          {built ? "built" : "compiled"}
        </span>
      </span>

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
          onClick={onOpenWorkflowFile}
          aria-label="Open workflow file"
          title="Open a workflow or snapshot JSON file"
          data-testid="open-workflow-file"
        >
          <FolderOpen aria-hidden className="size-4" />
        </button>
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
