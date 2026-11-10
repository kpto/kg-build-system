"use client";

import { useRef, type KeyboardEvent, type PointerEvent } from "react";

export interface SplitterProps {
  orientation: "vertical" | "horizontal";
  value: number;
  min: number;
  max: number;
  label: string;
  onChange(value: number): void;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/**
 * A keyboard-accessible panel splitter.
 *
 * `vertical` sits between the side bar and the editor and returns a width.
 * `horizontal` sits between an upper and a lower region and returns a height,
 * so dragging upward grows the upper region.
 */
export function Splitter({
  orientation,
  value,
  min,
  max,
  label,
  onChange,
}: SplitterProps) {
  const drag = useRef<{ start: number; value: number } | null>(null);

  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    event.preventDefault();
    drag.current = {
      start: orientation === "vertical" ? event.clientX : event.clientY,
      value,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (!drag.current) return;
    const delta =
      orientation === "vertical"
        ? event.clientX - drag.current.start
        : drag.current.start - event.clientY;
    onChange(clamp(drag.current.value + delta, min, max));
  };

  const endDrag = (event: PointerEvent<HTMLDivElement>) => {
    drag.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const step = event.shiftKey ? 48 : 16;
    let next: number | undefined;
    if (orientation === "vertical") {
      if (event.key === "ArrowLeft") next = value - step;
      else if (event.key === "ArrowRight") next = value + step;
      else if (event.key === "Home") next = min;
      else if (event.key === "End") next = max;
    } else {
      if (event.key === "ArrowUp") next = value + step;
      else if (event.key === "ArrowDown") next = value - step;
      else if (event.key === "Home") next = min;
      else if (event.key === "End") next = max;
    }
    if (next === undefined) return;
    event.preventDefault();
    onChange(clamp(next, min, max));
  };

  return (
    <div
      role="separator"
      aria-label={label}
      aria-orientation={orientation}
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={Math.round(value)}
      aria-valuetext={`${Math.round(value)} pixels`}
      tabIndex={0}
      className="wb-splitter"
      data-orientation={orientation}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      onKeyDown={onKeyDown}
    >
      <span className="wb-splitter-grip" aria-hidden />
    </div>
  );
}
