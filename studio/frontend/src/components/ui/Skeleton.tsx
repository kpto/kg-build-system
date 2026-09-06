"use client";

import clsx from "clsx";

/**
 * A loading placeholder shaped like what is coming, so a slow `/api/index` does not
 * collapse the layout. `aria-busy` announces that content is pending.
 */
export interface SkeletonProps {
  className?: string;
  lines?: number;
  /** Height of each bar, in px. */
  height?: number;
}

export function Skeleton({ className, lines = 3, height = 12 }: SkeletonProps) {
  return (
    <div className={clsx("flex flex-col gap-1.5", className)} aria-busy="true" aria-live="polite">
      {Array.from({ length: lines }, (_, index) => (
        <div
          key={index}
          className="animate-pulse rounded bg-raised"
          style={{ height, width: `${100 - index * (45 / Math.max(1, lines))}%` }}
        />
      ))}
    </div>
  );
}
