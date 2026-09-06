"use client";

import { type KeyboardEvent, type ReactNode } from "react";

export interface RowButtonProps {
  /** Run on click, Enter or Space — skipped when the click ended a drag-select. */
  onActivate(): void;
  /** Marks the row the surface is already on, for `aria-current`. */
  active?: boolean;
  className?: string;
  title?: string;
  children: ReactNode;
}

/**
 * A list row that activates like a button and selects like text.
 *
 * A native `<button>` consumes mousedown, so nothing inside it can be drag-selected,
 * and a diagnostic sitting in a button row cannot be copied out — which defeats the
 * point of a diagnostics surface. The button semantics (role, tab order, Enter and
 * Space) therefore live on a `<div>` instead.
 *
 * The click that follows a drag-select must not activate, or copying would move the
 * view somewhere else, so click activation is guarded on the selection being
 * collapsed. Keyboard activation is unconditional: a leftover selection says nothing
 * about an explicit key press. Content must stay non-interactive, since `role="button"`
 * owns its descendants.
 */
export function RowButton({ onActivate, active, className, title, children }: RowButtonProps) {
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    // Space scrolls the panel unless the row claims it; Enter is handled identically
    // so both keys read as one activation.
    event.preventDefault();
    onActivate();
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-current={active ? "true" : undefined}
      title={title}
      onClick={() => {
        // A collapsed (or absent) selection means the press was a click, not the tail
        // of a drag the user just made across this row's text.
        const selection = window.getSelection();
        if (selection === null || selection.isCollapsed) onActivate();
      }}
      onKeyDown={onKeyDown}
      className={className}
    >
      {children}
    </div>
  );
}
