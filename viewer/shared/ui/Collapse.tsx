"use client";

import type { ReactNode } from "react";

import { cx } from "./theme";

/**
 * One expansion rule for every collapsible body.
 *
 * The body stays mounted so its natural height is known; a grid row animates
 * from `0fr` to `1fr`. The clip hides the collapsed content and `inert` keeps
 * it out of focus order while closed.
 */
export function Collapse({
  open,
  children,
  className,
  clipClassName,
  testId,
}: {
  open: boolean;
  children: ReactNode;
  className?: string;
  clipClassName?: string;
  testId?: string;
}) {
  return (
    <div
      className={cx("wb-collapse", className)}
      data-open={open ? "true" : "false"}
      data-testid={testId}
    >
      <div
        className={cx("wb-collapse-clip", clipClassName)}
        inert={open ? undefined : true}
      >
        {children}
      </div>
    </div>
  );
}
