"use client";

import type { ReactNode } from "react";
import { cx } from "@/shared/ui/theme";

export interface FieldProps {
  label: ReactNode;
  value: ReactNode;
  title?: string;
  tone?: string;
  className?: string;
}

/**
 * One value and its label. A field is evidence, not navigation.
 */
export function Field({ label, value, title, tone, className }: FieldProps) {
  return (
    <span data-level="field" title={title} className={cx("ui-field", className)}>
      <span className="ui-field-label">{label}</span>
      <span className={cx("ui-field-value", tone)}>{value}</span>
    </span>
  );
}
