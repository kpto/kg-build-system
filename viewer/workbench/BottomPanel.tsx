"use client";

import { ChevronDown } from "lucide-react";

import { TopologyBottom } from "@/topology/TopologyFeature";
import { useWorkbench } from "./store";

export interface BottomPanelProps {
  onCollapse(): void;
}

export function BottomPanel({ onCollapse }: BottomPanelProps) {
  const { state, actions } = useWorkbench();

  return (
    <section
      className="wb-bottom"
      style={{ height: state.layout.bottomHeight }}
      aria-label="Workbench bottom panel"
      data-testid="bottom-panel"
    >
      <div className="wb-bottom-tabs" role="tablist" aria-label="Bottom panel tabs">
        <button
          type="button"
          role="tab"
          aria-selected="true"
          className="wb-bottom-tab"
          data-active="true"
        >
          Inspect
        </button>
        <span className="wb-bottom-spacer" />
        <button
          type="button"
          className="wb-icon-button wb-bottom-collapse"
          aria-label="Collapse bottom panel"
          title="Collapse bottom panel"
          onClick={onCollapse}
        >
          <ChevronDown aria-hidden className="size-3.5" />
        </button>
      </div>
      <div className="wb-bottom-body thin-scrollbar" data-testid="bottom-body">
        <TopologyBottom state={state} actions={actions} />
      </div>
    </section>
  );
}
