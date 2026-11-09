"use client";

import { ACTIVITY_LABELS } from "./defaults";
import { getFeature } from "./features";
import { useWorkbench } from "./store";

export function SideBar() {
  const { state, actions } = useWorkbench();
  const feature = getFeature(state.activity);
  const Icon = feature.icon;
  const layout = state.functions[state.activity].layout;
  const stats = state.index.stats;

  return (
    <aside
      className="wb-sidebar"
      style={{ width: layout.sidebarWidth }}
      aria-label={`${ACTIVITY_LABELS[state.activity]} side bar`}
      data-testid="sidebar"
    >
      <header className="wb-sidebar-header">
        <Icon aria-hidden className="size-3.5" />
        <span className="wb-sidebar-title">{ACTIVITY_LABELS[state.activity]}</span>
        <span className="wb-sidebar-meta">
          {stats.topologyNodes}N · {stats.topologyEdges}E
        </span>
      </header>
      <div className="wb-sidebar-body thin-scrollbar">
        <feature.Sidebar
          state={state}
          actions={actions}
          activity={state.activity}
        />
      </div>
    </aside>
  );
}
