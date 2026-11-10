"use client";

import { ChevronDown } from "lucide-react";

import {
  ACTIVITY_LABELS,
  bottomTabLabel,
  bottomTabsFor,
  defaultBottomTab,
} from "./defaults";
import { getFeature } from "./features";
import { useWorkbench } from "./store";

export interface BottomPanelProps {
  onCollapse(): void;
}

export function BottomPanel({ onCollapse }: BottomPanelProps) {
  const { state, actions } = useWorkbench();
  const activity = state.activity;
  const feature = getFeature(activity);
  const activeTab =
    state.layout.bottomTabs[activity] ?? defaultBottomTab(activity);
  const tabs = bottomTabsFor(activity, activeTab);

  return (
    <section
      className="wb-bottom"
      style={{ height: state.layout.bottomHeight }}
      aria-label={`${ACTIVITY_LABELS[activity]} bottom panel`}
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
            onClick={() => actions.setBottomTab(activity, tab)}
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
        <feature.Bottom state={state} actions={actions} activity={activity} />
      </div>
    </section>
  );
}
