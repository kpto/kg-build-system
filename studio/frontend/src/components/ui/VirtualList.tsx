"use client";

import { useRef, useState, type ReactNode } from "react";
import clsx from "clsx";

export interface VirtualListProps<T> {
  items: readonly T[];
  /** Fixed row height in px; the panel is dense on purpose, so rows are uniform. */
  rowHeight: number;
  itemCount?: number;
  overscan?: number;
  className?: string;
  renderItem(item: T, index: number): ReactNode;
  keyOf(item: T, index: number): string;
  /** Rendered instead of the window when there is nothing to show. */
  empty?: ReactNode;
}

/**
 * A minimal fixed-height window list. The problems panel can hold thousands of
 * diagnostics and the palette can list every entity in the document, and neither
 * justifies pulling in a virtualiser dependency.
 */
export function VirtualList<T>({
  items,
  rowHeight,
  overscan = 8,
  className,
  renderItem,
  keyOf,
  empty,
}: VirtualListProps<T>) {
  const scroll = useRef<HTMLDivElement | null>(null);
  const [viewport, setViewport] = useState(0);

  const total = items.length * rowHeight;
  const top = scroll.current?.scrollTop ?? 0;
  const start = Math.max(0, Math.floor(top / rowHeight) - overscan);
  const visibleCount = Math.ceil((viewport || 480) / rowHeight) + overscan * 2;
  const end = Math.min(items.length, start + visibleCount);
  const slice = items.slice(start, end);

  if (items.length === 0) {
    return <div className={clsx("min-h-0 flex-1", className)}>{empty ?? null}</div>;
  }

  return (
    <div
      ref={(node) => {
        scroll.current = node;
        if (node && node.clientHeight !== viewport) setViewport(node.clientHeight);
      }}
      onScroll={(event) => {
        // Repaint on scroll by reading scrollTop during render; no state churn per pixel.
        setViewport(event.currentTarget.clientHeight);
      }}
      className={clsx("min-h-0 flex-1 overflow-auto", className)}
      role="list"
    >
      <div style={{ height: total, position: "relative" }}>
        <div style={{ transform: `translateY(${start * rowHeight}px)` }}>
          {slice.map((item, offset) => {
            const index = start + offset;
            return (
              <div key={keyOf(item, index)} role="listitem" style={{ height: rowHeight }}>
                {renderItem(item, index)}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
