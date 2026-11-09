"use client";

import { ChevronDown } from "lucide-react";

import {
  ACTIVITY_LABELS,
  bottomTabLabel,
  bottomTabsFor,
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
  const layout = state.functions[activity].layout;
  const tabs = bottomTabsFor(activity, layout.bottomTab);

  return (
    <section
      className="wb-bottom"
      style={{ height: layout.bottomHeight }}
      aria-label={`${ACTIVITY_LABELS[activity]} bottom panel`}
      data-testid="bottom-panel"
    >
      <div className="wb-bottom-tabs" role="tablist" aria-label="Bottom panel tabs">
        {tabs.map((tab) => (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={layout.bottomTab === tab}
            className="wb-bottom-tab"
            data-active={layout.bottomTab === tab ? "true" : undefined}
            onClick={() => actions.setLayout(activity, { bottomTab: tab })}
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
