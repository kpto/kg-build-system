"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import { cx } from "@/shared/ui/theme";

export interface SectionProps {
  title: string;
  /** The question this section answers; used as its accessible name. */
  question: string;
  count?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  collapsible?: boolean;
  defaultOpen?: boolean;
  /** Controlled disclosure state. Omit to keep the state inside the section. */
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  /** The disclosure control's stable test id. */
  toggleTestId?: string;
  /** Mount the body only while open. Closed sections do not mount their tree. */
  lazy?: boolean;
  testId?: string;
  className?: string;
  bodyClassName?: string;
}

/**
 * One question inside a panel. Flat, separated by a rule, never a card.
 */
export function Section({
  title,
  question,
  count,
  actions,
  children,
  collapsible = false,
  defaultOpen = true,
  open: openProp,
  onOpenChange,
  toggleTestId,
  lazy = false,
  testId,
  className,
  bodyClassName,
}: SectionProps) {
  const [uncontrolledOpen, setUncontrolledOpen] = useState(defaultOpen);
  const open = openProp ?? uncontrolledOpen;

  function toggle() {
    const next = !open;
    if (openProp === undefined) setUncontrolledOpen(next);
    onOpenChange?.(next);
  }

  const body = lazy && !open ? null : children;

  return (
    <details
      open={open}
      data-testid={testId}
      data-level="section"
      aria-label={question}
      className={cx("ui-section group/section", className)}
    >
      <summary
        data-testid={toggleTestId}
        data-collapsible={collapsible ? "true" : undefined}
        aria-expanded={collapsible ? open : undefined}
        onClick={(event) => {
          event.preventDefault();
          if (collapsible) toggle();
        }}
        className={cx(
          "ui-section-header list-none",
          collapsible && "cursor-pointer",
        )}
      >
        {collapsible ? (
          <ChevronRight
            aria-hidden
            className={cx(
              "size-3 shrink-0 text-faint transition-transform",
              open && "rotate-90",
            )}
          />
        ) : null}
        <span className="ui-section-title min-w-0 flex-1 truncate">{title}</span>
        {count !== undefined ? (
          <span className="ui-section-count shrink-0">{count}</span>
        ) : null}
        {actions ? (
          <span
            className="flex shrink-0 items-center gap-1"
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
            }}
          >
            {actions}
          </span>
        ) : null}
      </summary>
      <div className={cx("ui-section-body", bodyClassName)}>{body}</div>
    </details>
  );
}
