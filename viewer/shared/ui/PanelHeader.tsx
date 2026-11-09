"use client";

import type { ReactNode } from "react";
import { cx } from "@/shared/ui/theme";

export interface PanelHeaderProps {
  title: string;
  icon?: ReactNode;
  meta?: ReactNode;
  children?: ReactNode;
  actions?: ReactNode;
  testId?: string;
  className?: string;
}

/**
 * The header of one tiled panel. It belongs to the panel, not to a global bar.
 *
 * The panel owns both this header and the body beneath it; every panel uses
 * exactly one. The row of aligned headers across a task is an arrangement of
 * panel-local headers, not a workspace-level toolbar.
 */
export function PanelHeader({
  title,
  icon,
  meta,
  children,
  actions,
  testId,
  className,
}: PanelHeaderProps) {
  return (
    <div
      data-testid={testId}
      data-area={title}
      data-level="panel-header"
      className={cx(
        "flex h-8 shrink-0 items-center gap-2 border-b border-line-soft bg-panel-raised px-3",
        className,
      )}
    >
      {icon ? (
        <span className="flex size-3.5 shrink-0 items-center justify-center text-faint">
          {icon}
        </span>
      ) : null}
      <span className="shrink-0 text-[11.5px] font-semibold tracking-normal text-ink-soft">
        {title}
      </span>
      {meta ? (
        <span className="tnum min-w-0 truncate font-mono text-[10.5px] text-faint">
          {meta}
        </span>
      ) : null}
      {children ? (
        <div className="flex min-w-0 items-center gap-0.5">{children}</div>
      ) : null}
      {actions ? (
        <div className="ml-auto flex shrink-0 items-center gap-1">{actions}</div>
      ) : null}
    </div>
  );
}
