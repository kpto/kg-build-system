"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";

export interface GraphViewport {
  scale: number;
  x: number;
  y: number;
}

/**
 * The shared pan/zoom viewport for every graph surface.
 *
 * The scene supplies its size in graph coordinates. This hook owns the
 * container measurement, fit, wheel zoom, drag pan and the click suppression
 * after a drag. The caller renders the scene; `GraphCanvas` adds the standard
 * toolbar, while the Workflow document composes its own toolbar and overlays
 * over the same viewport.
 */
export function useGraphViewport({
  width,
  height,
  minFitScale = 0.12,
}: {
  width: number;
  height: number;
  /** The lowest scale Fit may choose; a readable floor keeps text legible. */
  minFitScale?: number;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });
  const [view, setView] = useState<GraphViewport>({ scale: 1, x: 0, y: 0 });
  const dragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    x: number;
    y: number;
    moved: boolean;
  } | null>(null);
  const suppressClickRef = useRef(false);
  const cleanupDragRef = useRef<(() => void) | null>(null);

  useEffect(() => () => cleanupDragRef.current?.(), []);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      setSize({
        width: entry.contentRect.width,
        height: entry.contentRect.height,
      });
    });
    observer.observe(element);
    setSize({ width: element.clientWidth, height: element.clientHeight });
    return () => observer.disconnect();
  }, []);

  const fitView = useCallback(() => {
    if (!size.width || !size.height || !width || !height) return;
    const pad = 24;
    const scale = Math.max(
      minFitScale,
      Math.min(
        1.4,
        Math.min(
          (size.width - pad * 2) / width,
          (size.height - pad * 2) / height,
        ),
      ),
    );
    setView({
      scale,
      x: (size.width - width * scale) / 2,
      y: (size.height - height * scale) / 2,
    });
  }, [height, minFitScale, size.height, size.width, width]);

  useEffect(() => {
    fitView();
  }, [fitView]);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      const rect = element.getBoundingClientRect();
      const px = event.clientX - rect.left;
      const py = event.clientY - rect.top;
      setView((current) => {
        const next = Math.max(
          0.15,
          Math.min(3, current.scale * Math.exp(-event.deltaY * 0.0015)),
        );
        const ratio = next / current.scale;
        return {
          scale: next,
          x: px - ratio * (px - current.x),
          y: py - ratio * (py - current.y),
        };
      });
    };
    element.addEventListener("wheel", onWheel, { passive: false });
    return () => element.removeEventListener("wheel", onWheel);
  }, []);

  const zoomBy = (factor: number) => {
    setView((current) => {
      const next = Math.max(0.15, Math.min(3, current.scale * factor));
      const ratio = next / current.scale;
      const px = size.width / 2;
      const py = size.height / 2;
      return {
        scale: next,
        x: px - ratio * (px - current.x),
        y: py - ratio * (py - current.y),
      };
    });
  };

  const endDrag = () => {
    const drag = dragRef.current;
    if (!drag) return;
    dragRef.current = null;
    cleanupDragRef.current?.();
    cleanupDragRef.current = null;
    if (drag.moved) {
      suppressClickRef.current = true;
      window.setTimeout(() => {
        suppressClickRef.current = false;
      }, 0);
    }
  };

  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    if (dragRef.current) endDrag();
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      x: view.x,
      y: view.y,
      moved: false,
    };
    suppressClickRef.current = false;
    const onMove = (move: PointerEvent) => {
      const drag = dragRef.current;
      if (!drag || drag.pointerId !== move.pointerId) return;
      const dx = move.clientX - drag.startX;
      const dy = move.clientY - drag.startY;
      if (!drag.moved) {
        if (Math.abs(dx) <= 3 && Math.abs(dy) <= 3) return;
        drag.moved = true;
      }
      setView((current) => ({ ...current, x: drag.x + dx, y: drag.y + dy }));
    };
    const onUp = () => endDrag();
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp, { once: true });
    window.addEventListener("pointercancel", onUp, { once: true });
    cleanupDragRef.current = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
    };
  };

  /** True when the click that just ended was a drag, not a selection. */
  const shouldSuppressClick = (): boolean => {
    if (!suppressClickRef.current) return false;
    suppressClickRef.current = false;
    return true;
  };

  return {
    containerRef,
    size,
    view,
    fitView,
    zoomBy,
    onPointerDown,
    shouldSuppressClick,
  };
}

/**
 * A pannable and zoomable graph surface with the standard zoom/Fit toolbar.
 * The scene is supplied in graph coordinates; the viewport does not know what
 * the scene means.
 */
export function GraphCanvas({
  width,
  height,
  children,
  className,
  testId,
  ariaLabel,
  onBackgroundClick,
  minFitScale = 0.12,
}: {
  width: number;
  height: number;
  children: ReactNode;
  className?: string;
  testId?: string;
  ariaLabel?: string;
  onBackgroundClick?(): void;
  /** The lowest scale Fit may choose. A caller with a readable floor keeps
   * text legible and lets the user pan rather than shrinking the whole scene. */
  minFitScale?: number;
}) {
  const {
    containerRef,
    size,
    view,
    fitView,
    zoomBy,
    onPointerDown,
    shouldSuppressClick,
  } = useGraphViewport({ width, height, minFitScale });

  return (
    <div
      ref={containerRef}
      className={`relative overflow-hidden ${className ?? ""}`}
      data-testid={testId}
      onPointerDown={onPointerDown}
    >
      <svg
        className="block h-full w-full select-none"
        role="img"
        aria-label={ariaLabel}
        onClick={() => {
          if (shouldSuppressClick()) return;
          onBackgroundClick?.();
        }}
      >
        <g
          data-testid="graph-scene"
          transform={`translate(${view.x} ${view.y}) scale(${view.scale})`}
          opacity={size.width ? 1 : 0}
        >
          {children}
        </g>
      </svg>
      <div
        className="absolute bottom-2 left-2 z-10 flex items-stretch border border-line-soft bg-panel/95"
        onPointerDown={(event) => event.stopPropagation()}
        onPointerMove={(event) => event.stopPropagation()}
        onPointerUp={(event) => event.stopPropagation()}
      >
        <button
          type="button"
          onClick={() => zoomBy(1 / 1.25)}
          className="flex size-6 items-center justify-center border-r border-line text-muted hover:bg-panel-soft hover:text-text"
          aria-label="Zoom out graph"
          data-testid="graph-canvas-zoom-out"
        >
          −
        </button>
        <span className="flex w-11 items-center justify-center border-r border-line font-mono text-[10px] text-muted tabular-nums">
          {Math.round(view.scale * 100)}%
        </span>
        <button
          type="button"
          onClick={() => zoomBy(1.25)}
          className="flex size-6 items-center justify-center border-r border-line text-muted hover:bg-panel-soft hover:text-text"
          aria-label="Zoom in graph"
          data-testid="graph-canvas-zoom-in"
        >
          +
        </button>
        <button
          type="button"
          onClick={fitView}
          className="flex size-6 items-center justify-center text-muted hover:bg-panel-soft hover:text-text"
          aria-label="Fit graph"
          data-testid="graph-canvas-fit"
        >
          Fit
        </button>
      </div>
    </div>
  );
}
