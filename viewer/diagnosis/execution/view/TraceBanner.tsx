"use client";

import { GitBranch, X } from "lucide-react";
import type { StepId } from "@/lib/types";
import { theme } from "@/shared/ui/theme";

interface TraceBannerProps {
  focusStepId: StepId;
  onClear?: () => void;
}

export function TraceBanner({ focusStepId, onClear }: TraceBannerProps) {
  return (
    <div
      data-testid="trace-banner"
      role="status"
      className="absolute top-2 left-1/2 z-20 flex -translate-x-1/2 items-center gap-2 border border-line bg-panel px-2 py-1"
      style={{ borderLeft: `2px solid ${theme.selection}` }}
    >
      <GitBranch
        className="size-3 shrink-0"
        style={{ color: theme.selectionStrong }}
        aria-hidden
      />
      <span className="ui-field-label">trace</span>
      <span
        className="min-w-0 truncate font-mono text-[10px]"
        style={{ color: theme.selectionStrong }}
      >
        {focusStepId.join("/")}
      </span>
      <button
        type="button"
        data-testid="clear-focus"
        data-level="control"
        onClick={() => onClear?.()}
        className="ui-button ui-focus-ring ml-1"
      >
        <X className="size-3" aria-hidden />
        clear
      </button>
    </div>
  );
}
