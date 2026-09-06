import type { KeyboardEvent, ReactNode } from "react";
import clsx from "clsx";

export interface TabItem<T extends string> {
  id: T;
  label: ReactNode;
  /** 1–7 style hint shown right-aligned. */
  hint?: string;
  disabled?: boolean;
  badge?: ReactNode;
}

/**
 * A roving-tabindex tablist (APG pattern). `onActivate` fires on click, on Enter or
 * Space, and on arrow navigation, so the shell's tab strip and the in-panel
 * sub-tabs behave identically.
 */
export interface TabsProps<T extends string> {
  items: readonly TabItem<T>[];
  value: T;
  onChange(id: T): void;
  ariaLabel: string;
  size?: "sm" | "md";
  className?: string;
}

export function Tabs<T extends string>({
  items,
  value,
  onChange,
  ariaLabel,
  size = "md",
  className,
}: TabsProps<T>) {
  const move = (event: KeyboardEvent, delta: number) => {
    const enabled = items.filter((item) => !item.disabled);
    if (enabled.length === 0) return;
    event.preventDefault();
    const current = enabled.findIndex((item) => item.id === value);
    const next = enabled[(current + delta + enabled.length) % enabled.length];
    if (next) onChange(next.id);
  };

  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      aria-orientation="horizontal"
      className={clsx("flex items-stretch gap-0.5 border-b border-edge bg-surface", className)}
      onKeyDown={(event) => {
        if (event.key === "ArrowRight") move(event, 1);
        else if (event.key === "ArrowLeft") move(event, -1);
      }}
    >
      {items.map((item) => {
        const selected = item.id === value;
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            id={`tab-${item.id}`}
            aria-selected={selected}
            aria-controls={`panel-${item.id}`}
            tabIndex={selected ? 0 : -1}
            disabled={item.disabled}
            onClick={() => onChange(item.id)}
            className={clsx(
              "relative flex items-center gap-1.5 border-b-2 px-2.5 text-muted transition-colors",
              "hover:text-ink disabled:cursor-not-allowed disabled:opacity-40",
              size === "sm" ? "h-7 text-[11px]" : "h-8 text-[12px]",
              selected ? "border-info text-ink" : "border-transparent",
            )}
          >
            <span className="truncate">{item.label}</span>
            {item.badge}
            {item.hint && (
              <kbd className="rounded border border-edge bg-raised px-1 font-mono text-[9px] text-faint">
                {item.hint}
              </kbd>
            )}
          </button>
        );
      })}
    </div>
  );
}
