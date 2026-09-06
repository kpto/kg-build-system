import type { MouseEvent, ReactNode } from "react";
import clsx from "clsx";

/**
 * The `studio-card` utility plus the selection affordance every entity list uses.
 * Selection is communicated by the info ring (see the react-flow override in
 * globals.css) rather than by a background change, so a selected card still reads
 * as the same surface.
 */
export interface CardProps {
  children?: ReactNode;
  header?: ReactNode;
  footer?: ReactNode;
  selected?: boolean;
  /** Sets `aria-current` in addition to the ring, for assistive tech. */
  onSelect?(): void;
  className?: string;
  bodyClassName?: string;
  as?: "div" | "li" | "article";
}

export function Card({
  children,
  header,
  footer,
  selected = false,
  onSelect,
  className,
  bodyClassName,
  as: Tag = "div",
}: CardProps) {
  const interactive = onSelect !== undefined;
  const handle = (event: MouseEvent) => {
    if (!onSelect) return;
    event.preventDefault();
    onSelect();
  };
  return (
    <Tag
      className={clsx(
        "studio-card flex flex-col gap-1.5 p-2 text-left transition-colors",
        interactive && "cursor-pointer hover:border-edge-strong",
        selected && "border-info ring-1 ring-info",
        className,
      )}
      onClick={handle}
      onKeyDown={
        interactive
          ? (event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelect?.();
              }
            }
          : undefined
      }
      role={interactive ? "button" : undefined}
      tabIndex={interactive ? 0 : undefined}
      aria-current={interactive && selected ? "true" : undefined}
    >
      {header}
      <div className={clsx("min-w-0", bodyClassName)}>{children}</div>
      {footer}
    </Tag>
  );
}
