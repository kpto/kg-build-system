"use client";

import { useEffect, useRef } from "react";

export interface ContextMenuItem {
  label: string;
  hint?: string;
  onSelect(): void;
}

export interface ContextMenuProps {
  x: number;
  y: number;
  label: string;
  items: ContextMenuItem[];
  onClose(): void;
}

/**
 * A transient pointer menu. It never owns workbench state: an item runs one
 * explicit command and closes the menu.
 */
export function ContextMenu({ x, y, label, items, onClose }: ContextMenuProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onPointerDown = (event: PointerEvent) => {
      if (ref.current?.contains(event.target as Node)) return;
      onClose();
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("pointerdown", onPointerDown, true);
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("blur", onClose);
    return () => {
      window.removeEventListener("pointerdown", onPointerDown, true);
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("blur", onClose);
    };
  }, [onClose]);

  const left =
    typeof window === "undefined" ? x : Math.min(x, window.innerWidth - 220);
  const top =
    typeof window === "undefined" ? y : Math.min(y, window.innerHeight - 120);

  return (
    <div
      ref={ref}
      role="menu"
      aria-label={label}
      className="context-menu-pop fixed z-[100] w-[212px] overflow-hidden rounded border border-line-strong bg-panel shadow-2xl"
      style={{ left, top }}
      data-testid="context-menu"
      onContextMenu={(event) => event.preventDefault()}
    >
      <p className="truncate border-b border-line-soft px-2 py-1 font-mono text-[9px] text-faint">
        {label}
      </p>
      {items.map((item) => (
        <button
          key={item.label}
          type="button"
          role="menuitem"
          className="flex w-full items-center justify-between gap-3 px-2 py-1.5 text-left text-[10.5px] text-muted hover:bg-panel-soft hover:text-text"
          onClick={() => {
            item.onSelect();
            onClose();
          }}
          data-testid="context-menu-item"
        >
          <span>{item.label}</span>
          {item.hint ? (
            <span className="font-mono text-[9px] text-faint">{item.hint}</span>
          ) : null}
        </button>
      ))}
    </div>
  );
}
