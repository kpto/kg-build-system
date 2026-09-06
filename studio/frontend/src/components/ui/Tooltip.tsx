"use client";

import type { ReactNode } from "react";
import { useId, useState } from "react";
import clsx from "clsx";

export type TooltipSide = "top" | "bottom" | "left" | "right";

export interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  side?: TooltipSide;
  className?: string;
  /** Short labels render in mono (type labels, refs). */
  mono?: boolean;
}

const POSITION: Record<TooltipSide, string> = {
  top: "bottom-full left-1/2 mb-1 -translate-x-1/2",
  bottom: "top-full left-1/2 mt-1 -translate-x-1/2",
  left: "right-full top-1/2 mr-1 -translate-y-1/2",
  right: "left-full top-1/2 ml-1 -translate-y-1/2",
};

/**
 * Hover/focus tooltip. Deliberately CSS-driven visibility on top of real state, so
 * it appears on keyboard focus as well as on hover, and `role="tooltip"` plus
 * `aria-describedby` keeps it announced.
 */
export function Tooltip({ content, children, side = "top", className, mono }: TooltipProps) {
  const id = useId();
  const [open, setOpen] = useState(false);

  return (
    <span
      className={clsx("relative inline-flex min-w-0", className)}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocusCapture={() => setOpen(true)}
      onBlurCapture={() => setOpen(false)}
    >
      <span aria-describedby={open ? id : undefined} className="flex min-w-0">
        {children}
      </span>
      {open && (
        <span
          role="tooltip"
          id={id}
          className={clsx(
            "pointer-events-none absolute z-50 max-w-[22rem] whitespace-pre-wrap rounded-md border border-edge-strong",
            "bg-overlay px-2 py-1 text-[11px] leading-snug text-ink shadow-lg",
            mono && "font-mono",
            POSITION[side],
          )}
        >
          {content}
        </span>
      )}
    </span>
  );
}
