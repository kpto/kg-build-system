"use client";

/**
 * The one way the studio hands a complete string to the clipboard.
 *
 * Long values — a diagnostic, an IR ref — are shown clipped wherever they live in a
 * fixed-size row or card, and a drag-select can only ever reach the visible part. The
 * copy control sits *beside* such a row rather than inside it: a `role="button"` row
 * owns its descendants, so a control nested in it is unreachable. It says which of its
 * three outcomes happened rather than failing silently.
 */

import { useState } from "react";
import clsx from "clsx";

import { Button } from "./Button";

export interface CopyButtonProps {
  /** The whole string, however little of it the surface around it can show. */
  text: string;
  title: string;
  className?: string;
}

export function CopyButton({ text, title, className }: CopyButtonProps) {
  const [outcome, setOutcome] = useState<"idle" | "copied" | "blocked">("idle");

  const copy = () => {
    void writeText(text).then((ok) => {
      setOutcome(ok ? "copied" : "blocked");
      window.setTimeout(() => setOutcome("idle"), 1_200);
    });
  };

  return (
    <Button
      size="sm"
      variant="ghost"
      onClick={copy}
      title={title}
      className={clsx("shrink-0 self-center px-1.5 text-faint hover:text-ink", className)}
    >
      {outcome === "copied" ? "copied" : outcome === "blocked" ? "unavailable" : "copy"}
    </Button>
  );
}

/** Clipboard write, with a path that still works on a non-secure origin. */
export async function writeText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // The async clipboard needs a secure context; the dev server is reachable over a
    // LAN address, which is not one, so fall back to a throwaway selection.
    const field = document.createElement("textarea");
    field.value = text;
    field.setAttribute("readonly", "");
    field.style.position = "fixed";
    field.style.opacity = "0";
    document.body.appendChild(field);
    field.select();
    const copied =
      typeof document.execCommand === "function" ? document.execCommand("copy") : false;
    field.remove();
    return copied;
  }
}
