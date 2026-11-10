"use client";

import { RotateCcw, Trash2, X } from "lucide-react";

import {
  clearWorkbenchStorage,
  useWorkbench,
  workbenchStorageKey,
} from "./store";
import { DEFAULT_LAYOUT, activeDocument } from "./types";

export interface SettingsDialogProps {
  onClose(): void;
}

const THEME_SWATCHES = [
  { label: "Surface", value: "#232323" },
  { label: "Selection", value: "#ff9f43" },
  { label: "Link", value: "#5aa9e6" },
  { label: "Positive", value: "#7ac77a" },
  { label: "Attention", value: "#d7a84a" },
  { label: "Negative", value: "#e06c75" },
];

const SHORTCUTS = [
  { keys: "Ctrl/Cmd K", action: "Command palette" },
  { keys: "Ctrl/Cmd B", action: "Toggle side bar" },
  { keys: "Ctrl/Cmd J", action: "Toggle bottom panel" },
  { keys: "Alt ← / Alt →", action: "Back / forward" },
  { keys: "Mouse 3 / 4", action: "Back / forward documents" },
  { keys: "Ctrl/Cmd ,", action: "Settings" },
];

export function SettingsDialog({ onClose }: SettingsDialogProps) {
  const { state, actions } = useWorkbench();
  const document = activeDocument(state);

  const resetLayout = () => {
    actions.setLayout({
      sidebarWidth: DEFAULT_LAYOUT.sidebarWidth,
      bottomHeight: DEFAULT_LAYOUT.bottomHeight,
    });
    onClose();
  };

  const resetAll = () => {
    clearWorkbenchStorage(state.snapshot.name);
    actions.setLayout({
      sidebarWidth: DEFAULT_LAYOUT.sidebarWidth,
      bottomHeight: DEFAULT_LAYOUT.bottomHeight,
    });
    onClose();
  };

  return (
    <div
      className="wb-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className="wb-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Workbench settings"
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            event.preventDefault();
            onClose();
          }
        }}
        data-testid="settings-dialog"
      >
        <header className="wb-dialog-head">
          <div>
            <p className="wb-kicker">Workbench</p>
            <h2>Settings</h2>
          </div>
          <button
            type="button"
            className="wb-icon-button"
            aria-label="Close settings"
            title="Close settings"
            onClick={onClose}
            autoFocus
          >
            <X aria-hidden className="size-4" />
          </button>
        </header>

        <div className="wb-dialog-body thin-scrollbar">
          <section className="wb-settings-section">
            <h3>Stable panels</h3>
            <p>
              The workbench keeps one side bar width, bottom height, bottom tab
              per document view and one editor tab strip under one key.
            </p>
            <dl className="wb-settings-facts">
              <div>
                <dt>Snapshot</dt>
                <dd className="wb-mono">{state.snapshot.name}</dd>
              </div>
              <div>
                <dt>Document</dt>
                <dd>{document.kind === "graph" ? "Graph" : "Subject"}</dd>
              </div>
              <div>
                <dt>Storage key</dt>
                <dd className="wb-mono">{workbenchStorageKey(state.snapshot.name)}</dd>
              </div>
              <div>
                <dt>Side bar</dt>
                <dd className="wb-mono">
                  {state.layout.sidebarWidth}px
                </dd>
              </div>
              <div>
                <dt>Bottom panel</dt>
                <dd className="wb-mono">{state.layout.bottomHeight}px</dd>
              </div>
            </dl>
          </section>

          <section className="wb-settings-section">
            <h3>Theme</h3>
            <p>Dark surfaces with orange primary selection.</p>
            <div className="wb-swatch-grid">
              {THEME_SWATCHES.map((swatch) => (
                <span key={swatch.label} className="wb-swatch">
                  <span
                    className="wb-swatch-chip"
                    style={{ background: swatch.value }}
                    aria-hidden
                  />
                  <span>{swatch.label}</span>
                  <span className="wb-mono">{swatch.value}</span>
                </span>
              ))}
            </div>
          </section>

          <section className="wb-settings-section">
            <h3>Shortcuts</h3>
            <dl className="wb-settings-facts">
              {SHORTCUTS.map((shortcut) => (
                <div key={shortcut.keys}>
                  <dt className="wb-mono">{shortcut.keys}</dt>
                  <dd>{shortcut.action}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section className="wb-settings-section">
            <h3>Reset layout</h3>
            <p>The reset changes layout and tabs; it never changes the snapshot.</p>
            <div className="wb-settings-actions">
              <button type="button" className="wb-button" onClick={resetLayout}>
                <RotateCcw aria-hidden className="size-3" />
                Reset workbench layout
              </button>
              <button type="button" className="wb-button wb-button-danger" onClick={resetAll}>
                <Trash2 aria-hidden className="size-3" />
                Clear saved workbench
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
