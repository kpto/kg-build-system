"use client";

import {
  ArrowLeft,
  ArrowRight,
  Boxes,
  CircleDot,
  Database,
  FileText,
  Network,
  X,
} from "lucide-react";

import { useWorkbench } from "./store";
import type { WorkbenchTab } from "./types";

function tabIcon(tab: WorkbenchTab) {
  const Icon =
    tab.selection.kind === "graph"
      ? Network
      : tab.selection.kind === "property"
        ? CircleDot
        : tab.selection.kind === "asset"
          ? Database
          : tab.selection.kind === "node" || tab.selection.kind === "edge"
            ? Boxes
            : FileText;
  return <Icon aria-hidden className="size-3" />;
}

export function EditorTabs() {
  const { state, actions } = useWorkbench();
  const canBack = state.historyIndex > 0;
  const canForward = state.historyIndex < state.history.length - 1;

  return (
    <div className="wb-tabbar" data-testid="editor-tabs">
      <div className="wb-tabnav" role="group" aria-label="Tab history">
        <button
          type="button"
          className="wb-tabnav-button"
          onClick={actions.back}
          disabled={!canBack}
          aria-label="Back"
          title="Back (Alt+Left)"
          data-testid="tab-back"
        >
          <ArrowLeft aria-hidden className="size-3.5" />
        </button>
        <button
          type="button"
          className="wb-tabnav-button"
          onClick={actions.forward}
          disabled={!canForward}
          aria-label="Forward"
          title="Forward (Alt+Right)"
          data-testid="tab-forward"
        >
          <ArrowRight aria-hidden className="size-3.5" />
        </button>
      </div>

      <div className="wb-tabs" role="tablist" aria-label="Open editors">
        {state.tabs.map((tab) => {
          const active = tab.id === state.activeTabId;
          return (
            <div
              key={tab.id}
              className="wb-tab"
              data-active={active ? "true" : undefined}
              data-pinned={tab.pinned ? "true" : undefined}
            >
              <button
                type="button"
                role="tab"
                aria-selected={active}
                className="wb-tab-label"
                title={`${tab.title} · ${tab.selection.kind ?? "document"}`}
                onClick={() => actions.activateTab(tab.id)}
                data-testid={`tab-${tab.id}`}
              >
                {tabIcon(tab)}
                <span className="wb-tab-title">{tab.title}</span>
              </button>
              {tab.pinned ? null : (
                <button
                  type="button"
                  className="wb-tab-close"
                  aria-label={`Close ${tab.title}`}
                  title={`Close ${tab.title}`}
                  onClick={() => actions.closeTab(tab.id)}
                >
                  <X aria-hidden className="size-3" />
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
