"use client";

import clsx from "clsx";

export interface ToggleProps {
  checked: boolean;
  onChange(checked: boolean): void;
  /** Always visible; also the accessible name. */
  label: string;
  description?: string;
  disabled?: boolean;
  id?: string;
  className?: string;
}

/** A switch: `role="switch"` with the state on `aria-checked`. */
export function Toggle({
  checked,
  onChange,
  label,
  description,
  disabled = false,
  id,
  className,
}: ToggleProps) {
  return (
    <button
      type="button"
      id={id}
      role="switch"
      aria-checked={checked}
      aria-label={description ? `${label}. ${description}` : label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      title={description}
      className={clsx("group flex items-center gap-2 text-[12px] text-ink disabled:opacity-50", className)}
    >
      <span
        aria-hidden
        className={clsx(
          "relative h-4 w-7 shrink-0 rounded-full border transition-colors",
          checked ? "border-info bg-info/25" : "border-edge bg-raised",
        )}
      >
        <span
          className={clsx(
            "absolute top-0.5 h-2.5 w-2.5 rounded-full transition-all",
            checked ? "left-3.5 bg-info" : "left-0.5 bg-faint",
          )}
        />
      </span>
      <span className="truncate">{label}</span>
    </button>
  );
}
