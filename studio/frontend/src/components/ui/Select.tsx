"use client";

import type { SelectHTMLAttributes } from "react";
import clsx from "clsx";

import { CONTROL } from "./control";

export interface SelectOption {
  readonly value: string;
  readonly label: string;
  readonly disabled?: boolean;
  /** Group heading; consecutive grouped options render under one heading. */
  readonly group?: string;
}

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  options: readonly SelectOption[];
  /** Rendered as the first, non-selectable entry. */
  placeholder?: string;
  invalid?: boolean;
}

export function Select({ options, placeholder, className, invalid, ...rest }: SelectProps) {
  // Grouping preserves document order; a group heading is emitted once only.
  const rendered: React.ReactNode[] = [];
  let openGroup: string | null = null;
  for (const option of options) {
    if ((option.group ?? null) !== openGroup) {
      openGroup = option.group ?? null;
      if (openGroup) rendered.push(<option key={`gap-${rendered.length}`} disabled value={`__gap-${rendered.length}`}>{openGroup}</option>);
    }
    rendered.push(
      <option key={`${option.group ?? ""}:${option.value}`} value={option.value} disabled={option.disabled}>
        {option.label}
      </option>,
    );
  }

  return (
    <select
      {...rest}
      aria-invalid={invalid || undefined}
      className={clsx(
        CONTROL,
        "cursor-pointer appearance-none bg-[length:0] pr-6",
        invalid && "border-danger",
        className,
      )}
    >
      {placeholder !== undefined && <option value="">{placeholder}</option>}
      {rendered}
    </select>
  );
}
