"use client";

import { Keyboard, X } from "lucide-react";

interface ShortcutSheetViewProps {
  open: boolean;
  onClose: () => void;
}

const shortcuts: Array<[string, string]> = [
  ["/", "Focus search"],
  ["m", "Topology map"],
  ["w", "Workflow view"],
  ["b", "Explorer / blueprint"],
  ["l", "Lineage view"],
  ["r", "Review view"],
  ["f", "Fit the active graph"],
  ["j / k", "Next / previous finding"],
  ["Enter", "Open the selected finding's subject"],
  ["?", "Toggle this sheet"],
  ["Esc", "Close the sheet or clear trace focus"],
];

/**
 * The keyboard-shortcut sheet. It is presentation-only: the controller owns
 * whether it is open because shortcuts are handled at window level.
 */
export function ShortcutSheetView({ open, onClose }: ShortcutSheetViewProps) {
  if (!open) return null;
  return (
    <div
      data-testid="shortcut-sheet"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-6 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-xl border border-line bg-panel-raised p-5 shadow-2xl shadow-black/50"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Keyboard className="size-4 text-accent" aria-hidden />
            <h2 className="text-sm font-semibold text-zinc-100">Keyboard shortcuts</h2>
          </div>
          <button
            type="button"
            data-testid="close-shortcuts"
            onClick={onClose}
            className="rounded border border-line p-1 text-muted hover:border-zinc-500 hover:text-zinc-200"
            aria-label="Close shortcuts"
          >
            <X className="size-3.5" aria-hidden />
          </button>
        </div>
        <dl className="mt-4 space-y-2">
          {shortcuts.map(([key, description]) => (
            <div key={key} className="flex items-center justify-between gap-4">
              <dt className="font-mono text-[10px] text-zinc-300">{key}</dt>
              <dd className="text-right text-[11px] text-muted">{description}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-4 border-t border-line-soft pt-3 text-[10px] leading-relaxed text-faint">
          Shortcuts are ignored while typing in search or a note field.
        </p>
      </div>
    </div>
  );
}
