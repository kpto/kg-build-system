"use client";

import clsx from "clsx";

import type { Problem, ProblemSeverity } from "@/lib/types";
import { SEVERITY_RANK } from "@/lib/types";
import { SeverityMark } from "./icons";

export interface ProblemBadgeProps {
  /** Every problem attached to one ref (the store's `byRef` output). */
  problems: readonly Problem[];
  /** The ref this badge describes — used for the accessible name. */
  ref?: string | null;
  /** Show one dot for the worst severity instead of one per severity present. */
  compact?: boolean;
  className?: string;
  onClick?(): void;
}

const DOT: Record<ProblemSeverity, string> = {
  error: "bg-danger",
  warning: "bg-warn",
  info: "bg-info",
};

const TEXT: Record<ProblemSeverity, string> = {
  error: "text-danger",
  warning: "text-warn",
  info: "text-info",
};

export { SeverityMark as severityIcon };

/**
 * Per-ref problem badge: one dot per severity present plus the count.
 *
 * It renders nothing when the ref is clean, which is what makes it safe to drop
 * beside every row, card and slot without cluttering the surface.
 */
export function ProblemBadge({ problems, ref, compact, className, onClick }: ProblemBadgeProps) {
  if (problems.length === 0) return null;

  const counts = new Map<ProblemSeverity, number>();
  for (const problem of problems) {
    counts.set(problem.severity, (counts.get(problem.severity) ?? 0) + 1);
  }
  const ordered = (["error", "warning", "info"] as ProblemSeverity[]).filter((severity) =>
    counts.has(severity),
  );
  const worst = ordered[0] ?? "info";
  const summary = ordered
    .map((severity) => `${counts.get(severity)} ${severity}${(counts.get(severity) ?? 1) === 1 ? "" : "s"}`)
    .join(", ");
  const title = [
    ref ? `${ref}: ${summary}` : summary,
    ...[...problems]
      .sort((a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity])
      .slice(0, 4)
      .map((problem) => `${problem.severity}: ${problem.message}`),
  ].join("\n");
  const label = `${problems.length} problem${problems.length === 1 ? "" : "s"} on ${ref ?? "this item"}`;

  const body = (
    <>
      {(compact ? [worst] : ordered).map((severity) => (
        <span
          key={severity}
          aria-hidden
          className={clsx("h-1.5 w-1.5 rounded-full", DOT[severity])}
        />
      ))}
      <span className={clsx("font-mono text-[10px] leading-none", TEXT[worst])}>{problems.length}</span>
    </>
  );

  const classes = clsx(
    "inline-flex shrink-0 items-center gap-1 rounded border border-edge bg-raised px-1 py-0.5",
    onClick && "cursor-pointer hover:border-edge-strong",
    className,
  );

  return onClick ? (
    <button type="button" className={classes} onClick={onClick} title={title} aria-label={label}>
      {body}
    </button>
  ) : (
    <span className={classes} title={title} aria-label={label}>
      {body}
    </span>
  );
}

/** The severity glyph used by list rows; distinct shapes, not colour alone. */
export function SeverityGlyph({ severity }: { severity: ProblemSeverity }) {
  return <SeverityMark severity={severity} />;
}
