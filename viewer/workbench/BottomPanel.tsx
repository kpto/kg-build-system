"use client";

import { ChevronDown } from "lucide-react";

import { DetailBottom } from "@/detail/DetailFeature";
import { TopologyBottom } from "@/topology/TopologyFeature";
import {
  bottomTabLabel,
  bottomTabsFor,
  defaultBottomTab,
} from "./defaults";
import { useWorkbench } from "./store";
import { currentSelection, tabView } from "./types";

export interface BottomPanelProps {
  onCollapse(): void;
}

export function BottomPanel({ onCollapse }: BottomPanelProps) {
  const { state, actions } = useWorkbench();
  const view = tabView(currentSelection(state));
  const activeTab =
    state.layout.bottomTabs[view] ?? defaultBottomTab(view);
  const tabs = bottomTabsFor(view, activeTab);
  const Bottom = view === "graph" ? TopologyBottom : DetailBottom;

  return (
    <section
      className="wb-bottom"
      style={{ height: state.layout.bottomHeight }}
      aria-label="Workbench bottom panel"
      data-testid="bottom-panel"
    >
      <div className="wb-bottom-tabs" role="tablist" aria-label="Bottom panel tabs">
        {tabs.map((tab) => (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={activeTab === tab}
            className="wb-bottom-tab"
            data-active={activeTab === tab ? "true" : undefined}
            onClick={() => actions.setBottomTab(view, tab)}
          >
            {bottomTabLabel(tab)}
          </button>
        ))}
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
        <Bottom state={state} actions={actions} />
      </div>
    </section>
  );
}
