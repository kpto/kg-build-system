"use client";

import { RotateCcw, Trash2, X } from "lucide-react";

import {
  ACTIVITY_LABELS,
  defaultFunctionState,
} from "./defaults";
import {
  clearWorkbenchStorage,
  useWorkbench,
  workbenchStorageKey,
} from "./store";
import { ACTIVITY_ORDER } from "./defaults";

export interface SettingsDialogProps {
  onClose(): void;
}

const THEME_SWATCHES = [
  { label: "Surface", value: "#232323" },
  { label: "Selection", value: "#ff9f43" },
  { label: "Link", value: "#5aa9e6" },
  { label: "Accepted", value: "#7ac77a" },
  { label: "Open", value: "#d7a84a" },
  { label: "Rejected", value: "#e06c75" },
];

export function SettingsDialog({ onClose }: SettingsDialogProps) {
  const { state, actions } = useWorkbench();
  const activity = state.activity;

  const resetActivity = () => {
    actions.setLayout(activity, defaultFunctionState(activity).layout);
    onClose();
  };

  const resetAll = () => {
    clearWorkbenchStorage(state.snapshot.name);
    for (const id of ACTIVITY_ORDER) {
      actions.setLayout(id, defaultFunctionState(id).layout);
    }
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
              Every function keeps its side bar width, bottom height, chosen
              bottom tab, open editor tabs and selection under one key.
            </p>
            <dl className="wb-settings-facts">
              <div>
                <dt>Snapshot</dt>
                <dd className="wb-mono">{state.snapshot.name}</dd>
              </div>
              <div>
                <dt>Function</dt>
                <dd>{ACTIVITY_LABELS[activity]}</dd>
              </div>
              <div>
                <dt>Storage key</dt>
                <dd className="wb-mono">{workbenchStorageKey(state.snapshot.name, activity)}</dd>
              </div>
              <div>
                <dt>Side bar</dt>
                <dd className="wb-mono">
                  {state.functions[activity].layout.sidebarWidth}px
                </dd>
              </div>
              <div>
                <dt>Bottom panel</dt>
                <dd className="wb-mono">
                  {state.functions[activity].layout.bottomHeight}px ·{" "}
                  {state.functions[activity].layout.bottomTab}
                </dd>
              </div>
            </dl>
          </section>

          <section className="wb-settings-section">
            <h3>Theme</h3>
            <p>Blender dark surfaces with orange primary selection.</p>
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
            <h3>Reset layout</h3>
            <p>The reset changes layout and tabs; it never changes the snapshot.</p>
            <div className="wb-settings-actions">
              <button type="button" className="wb-button" onClick={resetActivity}>
                <RotateCcw aria-hidden className="size-3" />
                Reset {ACTIVITY_LABELS[activity]}
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
