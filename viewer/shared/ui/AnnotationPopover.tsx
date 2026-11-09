"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { MessageSquareText } from "lucide-react";
import { enrichAnnotations } from "@/lib/annotations";
import type { AnnotationContext, AnnotationDTO, MetaGraphIndex } from "@/lib/types";

interface AnnotationPopoverProps {
  annotations?: AnnotationDTO[];
  context: AnnotationContext;
  metaGraph: MetaGraphIndex;
  compact?: boolean;
}

const POPOVER_WIDTH = 300;

export function AnnotationPopover({
  annotations,
  context,
  metaGraph,
  compact = false,
}: AnnotationPopoverProps) {
  const enriched = useMemo(
    () => enrichAnnotations(annotations, context, metaGraph),
    [annotations, context, metaGraph],
  );
  const anchorRef = useRef<HTMLSpanElement>(null);
  const closeTimer = useRef<number | undefined>(undefined);
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });

  const reposition = useCallback(() => {
    const anchor = anchorRef.current;
    if (!anchor || typeof window === "undefined") return;
    const rect = anchor.getBoundingClientRect();
    const left = Math.max(
      8,
      Math.min(rect.left, window.innerWidth - POPOVER_WIDTH - 8),
    );
    const estimatedHeight = Math.min(320, 72 + enriched.length * 88);
    const below = rect.bottom + 8;
    const top =
      below + estimatedHeight > window.innerHeight
        ? Math.max(8, rect.top - estimatedHeight - 8)
        : below;
    setPosition({ top, left });
  }, [enriched.length]);

  const cancelClose = useCallback(() => {
    if (closeTimer.current !== undefined) {
      window.clearTimeout(closeTimer.current);
      closeTimer.current = undefined;
    }
  }, []);

  const show = useCallback(() => {
    cancelClose();
    reposition();
    setOpen(true);
  }, [cancelClose, reposition]);

  const scheduleClose = useCallback(() => {
    cancelClose();
    if (typeof window !== "undefined") {
      closeTimer.current = window.setTimeout(() => setOpen(false), 140);
    }
  }, [cancelClose]);

  useEffect(() => {
    if (!open) return;
    const handler = () => reposition();
    window.addEventListener("scroll", handler, true);
    window.addEventListener("resize", handler);
    return () => {
      window.removeEventListener("scroll", handler, true);
      window.removeEventListener("resize", handler);
    };
  }, [open, reposition]);

  useEffect(() => {
    return () => {
      if (closeTimer.current !== undefined) {
        window.clearTimeout(closeTimer.current);
      }
    };
  }, []);

  if (!enriched.length) return null;

  const popover =
    open && typeof document !== "undefined"
      ? createPortal(
          <div
            data-testid="annotation-popover"
            role="tooltip"
            className="fixed z-[100] max-h-[70vh] w-[300px] overflow-y-auto rounded-xl border border-line bg-panel-raised p-3 text-left shadow-2xl shadow-black/60"
            style={{ top: position.top, left: position.left }}
            onMouseEnter={cancelClose}
            onMouseLeave={scheduleClose}
          >
            {enriched.map((annotation) => (
              <div
                key={`${annotation.key}-${JSON.stringify(annotation.arguments)}`}
                className="space-y-1 border-t border-line-soft pt-2 first:border-t-0 first:pt-0"
              >
                <p className="font-mono text-[11px] text-accent">{annotation.key}</p>
                {annotation.argumentList.length ? (
                  <p className="text-[11px] text-muted">
                    {annotation.argumentList
                      .map(({ key, value }) => `${key}=${String(value)}`)
                      .join(" · ")}
                  </p>
                ) : null}
                {annotation.description ? (
                  <p className="text-xs leading-relaxed text-zinc-300">
                    {annotation.description}
                  </p>
                ) : null}
                {annotation.examples.length ? (
                  <p className="text-[11px] leading-relaxed text-zinc-400">
                    <span className="text-faint">examples </span>
                    {annotation.examples.slice(0, 4).map(String).join(" · ")}
                  </p>
                ) : null}
                {annotation.counts ? (
                  <p className="font-mono text-[10px] text-faint">
                    {Object.entries(annotation.counts)
                      .filter(([, value]) => value !== undefined)
                      .map(([key, value]) => `${key}=${value}`)
                      .join(" · ")}
                  </p>
                ) : null}
              </div>
            ))}
          </div>,
          document.body,
        )
      : null;

  return (
    <>
      <span
        ref={anchorRef}
        data-testid="annotation-anchor"
        className="nodrag inline-flex"
        onMouseEnter={show}
        onMouseLeave={scheduleClose}
        onFocus={show}
        onBlur={(event) => {
          const next = event.relatedTarget;
          if (!(next instanceof Node) || !anchorRef.current?.contains(next)) {
            setOpen(false);
          }
        }}
      >
        <button
          type="button"
          data-testid="annotation-pill"
          className="inline-flex items-center gap-1 rounded-full border border-line bg-panel-soft px-2 py-0.5 text-[10px] font-medium tracking-wide text-muted transition hover:border-accent/60 hover:text-accent"
          aria-label={`${enriched.length} annotation${enriched.length === 1 ? "" : "s"}`}
          aria-expanded={open}
        >
          <MessageSquareText className="size-3" aria-hidden />
          {compact
            ? enriched.length
            : enriched.map((annotation) => annotation.label).join(" · ")}
        </button>
      </span>
      {popover}
    </>
  );
}
