"use client";

import type { HTMLAttributes, ReactNode } from "react";
import { cx } from "@/shared/ui/theme";

export interface RowProps extends HTMLAttributes<HTMLElement> {
  children: ReactNode;
  selected?: boolean;
  active?: boolean;
  as?: "div" | "button";
  interactive?: boolean;
}

/**
 * One subject. A row is never a section and never contains another row.
 */
export function Row({
  children,
  selected,
  active,
  as = "div",
  interactive,
  className,
  ...rest
}: RowProps) {
  const Component = as;
  return (
    <Component
      data-level="row"
      data-selected={selected ? "true" : undefined}
      data-active={active ? "true" : undefined}
      className={cx(
        "ui-row",
        interactive && "cursor-pointer",
        className,
      )}
      {...rest}
    >
      {children}
    </Component>
  );
}
