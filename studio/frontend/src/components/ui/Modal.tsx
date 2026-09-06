"use client";

import { useEffect, useRef, type ReactNode } from "react";
import clsx from "clsx";

import { CloseIcon } from "./icons";

export interface ModalProps {
  open: boolean;
  onClose(): void;
  title: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  /** Widest surfaces (JSON, generated code) opt in to more room. */
  size?: "sm" | "md" | "lg";
}

/**
 * A single modal at a time; the shell's command palette and the "create project"
 * dialog both use it. Escape closes, focus moves in on open and returns to the
 * opener on close.
 */
export function Modal({ open, onClose, title, children, footer, size = "md" }: ModalProps) {
  const panel = useRef<HTMLDivElement | null>(null);
  const restore = useRef<Element | null>(null);

  useEffect(() => {
    if (!open) return;
    restore.current = document.activeElement;
    const first = panel.current?.querySelector<HTMLElement>(
      "input, select, textarea, button:not([data-modal-close])",
    );
    first?.focus();

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        onClose();
      }
    };
    document.addEventListener("keydown", onKey, true);
    return () => {
      document.removeEventListener("keydown", onKey, true);
      (restore.current as HTMLElement | null)?.focus?.();
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-canvas/70 p-8 pt-[12vh]"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === "string" ? title : undefined}
        className={clsx(
          "studio-card flex max-h-[70vh] w-full flex-col overflow-hidden",
          size === "sm" && "max-w-sm",
          size === "md" && "max-w-xl",
          size === "lg" && "max-w-4xl",
        )}
      >
        <header className="flex h-9 shrink-0 items-center gap-2 border-b border-edge px-3">
          <h2 className="truncate text-[12px] font-semibold text-ink">{title}</h2>
          <button
            type="button"
            data-modal-close
            onClick={onClose}
            aria-label="Close"
            className="ml-auto rounded p-1 text-muted hover:bg-raised hover:text-ink"
          >
            <CloseIcon size={14} />
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-auto p-3">{children}</div>
        {footer && (
          <footer className="flex shrink-0 items-center justify-end gap-2 border-t border-edge px-3 py-2">
            {footer}
          </footer>
        )}
      </div>
    </div>
  );
}
