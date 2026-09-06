"use client";

import type { ReactNode } from "react";
import clsx from "clsx";

export interface EmptyStateProps {
  title: string;
  /** One sentence of what belongs here — never marketing copy. */
  body?: ReactNode;
  actions?: ReactNode;
  /** A form or list under the explanation, centred in the same column. */
  children?: ReactNode;
  icon?: ReactNode;
  className?: string;
}

/**
 * The empty state used by every area, including the no-workspace case the shell
 * shows before a document exists.
 */
export function EmptyState({ title, body, actions, children, icon, className }: EmptyStateProps) {
  return (
    <div
      className={clsx(
        "flex h-full min-h-[8rem] flex-col items-center justify-center gap-2 p-6 text-center",
        className,
      )}
    >
      {icon && <div className="text-faint">{icon}</div>}
      <p className="text-[13px] font-medium text-ink">{title}</p>
      {body && <p className="max-w-md text-[12px] leading-relaxed text-muted">{body}</p>}
      {actions && <div className="mt-1 flex items-center gap-2">{actions}</div>}
      {children && <div className="mt-2 w-full max-w-md text-left">{children}</div>}
    </div>
  );
}
