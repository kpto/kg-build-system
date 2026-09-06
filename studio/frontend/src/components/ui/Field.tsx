"use client";

import type { ReactNode } from "react";
import clsx from "clsx";

/**
 * Label + control, the only sanctioned way to put a control in a form surface.
 *
 * The label is always associated with the control — pass the control's `id` as
 * `htmlFor`. `hint` and `error` render in the same grid cell so they stay attached to
 * the field they describe; `error` wins the slot and recolours it.
 */
export interface FieldProps {
  label: ReactNode;
  /** The control's `id`; a generated one is used when omitted. */
  htmlFor?: string;
  hint?: ReactNode;
  /** The control. Give it the same `id` as `htmlFor`. */
  children: ReactNode;
  /** Right-aligned unit or type text, e.g. the resulting type of a slot. */
  suffix?: ReactNode;
  required?: boolean;
  error?: ReactNode;
  className?: string;
  /** Stack vertically instead of the label-left layout tables use. */
  stack?: boolean;
}

export function Field({
  label,
  htmlFor,
  hint,
  children,
  suffix,
  required = false,
  error,
  className,
  stack = false,
}: FieldProps) {
  const id = htmlFor;
  const labelId = id ? `${id}-label` : undefined;
  const describedBy = hint !== undefined || error !== undefined ? `${id ?? "field"}-hint` : undefined;

  return (
    <div
      className={clsx(
        "min-w-0 gap-1",
        stack ? "flex flex-col" : "grid grid-cols-[6.5rem_1fr] items-center",
        className,
      )}
    >
      <label
        {...(id ? { htmlFor: id } : {})}
        id={labelId}
        className="truncate text-[11px] font-medium uppercase tracking-[0.06em] text-muted"
      >
        {label}
        {required && (
          <span className="ml-0.5 text-danger" aria-hidden>
            *
          </span>
        )}
      </label>
      {/* The wrapper carries the grouping semantics, so the label and description reach
          assistive tech whether or not the control inside it takes the id. */}
      <div
        role="group"
        aria-labelledby={labelId}
        aria-describedby={describedBy}
        className="flex min-w-0 items-center gap-2"
      >
        <div className="flex min-w-0 flex-1 flex-col">{children}</div>
        {suffix !== undefined && (
          <span className="shrink-0 font-mono text-[11px] text-faint">{suffix}</span>
        )}
      </div>
      {(hint !== undefined || error !== undefined) && (
        <p
          id={describedBy}
          className={clsx(
            "truncate text-[11px]",
            stack ? "" : "col-span-2 pl-[6.5rem]",
            error ? "text-danger" : "text-faint",
          )}
        >
          {error ?? hint}
        </p>
      )}
    </div>
  );
}
