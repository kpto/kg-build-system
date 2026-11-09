"use client";

import { Search, Settings } from "lucide-react";

import { ACTIVITY_LABELS } from "./defaults";
import { FEATURES } from "./features";
import { useWorkbench } from "./store";

export interface ActivityBarProps {
  onOpenPalette(): void;
  onOpenSettings(): void;
}

export function ActivityBar({ onOpenPalette, onOpenSettings }: ActivityBarProps) {
  const { state, actions } = useWorkbench();

  return (
    <nav className="wb-activitybar" aria-label="Workbench activities">
      <div className="wb-activity-group">
        {FEATURES.map((feature) => {
          const Icon = feature.icon;
          const active = state.activity === feature.id;
          return (
            <button
              key={feature.id}
              type="button"
              className="wb-activity-button"
              data-active={active ? "true" : undefined}
              aria-label={`${ACTIVITY_LABELS[feature.id]} activity`}
              aria-current={active ? "page" : undefined}
              title={ACTIVITY_LABELS[feature.id]}
              onClick={() => actions.setActivity(feature.id)}
              data-testid={`activity-${feature.id}`}
            >
              <Icon aria-hidden className="size-[18px]" />
              <span className="wb-activity-tooltip">{ACTIVITY_LABELS[feature.id]}</span>
            </button>
          );
        })}
      </div>

      <div className="wb-activity-group wb-activity-footer">
        <button
          type="button"
          className="wb-activity-button"
          aria-label="Search commands and subjects"
          title="Search commands and subjects"
          onClick={onOpenPalette}
        >
          <Search aria-hidden className="size-[18px]" />
          <span className="wb-activity-tooltip">Search</span>
        </button>
        <button
          type="button"
          className="wb-activity-button"
          aria-label="Workbench settings"
          title="Workbench settings"
          onClick={onOpenSettings}
        >
          <Settings aria-hidden className="size-[18px]" />
          <span className="wb-activity-tooltip">Settings</span>
        </button>
      </div>
    </nav>
  );
}
