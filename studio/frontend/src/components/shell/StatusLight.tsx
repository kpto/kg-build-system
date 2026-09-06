"use client";

import clsx from "clsx";

import type { StatusLevel } from "@/stores/connectionStore";
import { Dot } from "@/components/ui";

const LEVEL_DOT: Record<StatusLevel, string> = {
  ok: "bg-ok",
  warn: "bg-warn",
  error: "bg-danger",
  unknown: "bg-faint",
};

const LEVEL_TEXT: Record<StatusLevel, string> = {
  ok: "text-ok",
  warn: "text-warn",
  error: "text-danger",
  unknown: "text-faint",
};

/**
 * The header status light: one dot, derived only from the status model. The tooltip
 * lists the per-tier counts so the number behind the colour is always reachable.
 */
export function StatusLight({
  level,
  label,
  lines,
  id = "status-light",
}: {
  level: StatusLevel;
  label: string;
  lines: readonly string[];
  id?: string;
}) {
  return (
    <span
      className="group/light relative inline-flex shrink-0 items-center gap-1.5"
      aria-describedby={id}
    >
      <Dot className={LEVEL_DOT[level]} pulse={level === "warn" && label === "generating"} />
      <span className={clsx("font-mono text-[11px]", LEVEL_TEXT[level])}>{label}</span>
      <span
        id={id}
        role="tooltip"
        className="pointer-events-none absolute left-0 top-full z-40 mt-1 hidden min-w-[13rem] whitespace-pre-wrap rounded-md border border-edge-strong bg-overlay px-2 py-1.5 font-mono text-[11px] leading-relaxed text-ink shadow-lg group-hover/light:block"
      >
        {lines.map((line) => (
          <span key={line} className="block">
            {line}
          </span>
        ))}
      </span>
    </span>
  );
}
