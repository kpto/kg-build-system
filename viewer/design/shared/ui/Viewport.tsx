"use client";

import type {
  ButtonHTMLAttributes,
  HTMLAttributes,
  MouseEventHandler,
  PointerEventHandler,
  ReactNode,
  Ref,
} from "react";

import type { ConceptKind } from "@/lib/concepts";
import { TabBanner, type TabBannerFact } from "./TabBanner";
import { cx } from "./theme";
import styles from "./viewport.module.css";

/**
 * One Blender-style frame for every visualisation surface.
 *
 * The frame owns the 30px area header, the canvas body and the bottom-left
 * navigation cluster. A view supplies its concept, name, live extent, actions
 * and renderer; it does not repeat frame chrome.
 */
export function ViewportFrame({
  concept,
  kicker,
  title,
  subtitle,
  facts,
  factsTestId,
  actions,
  actionsTestId,
  nav,
  testId,
  ariaLabel,
  bodyRef,
  bodyTestId,
  bodyClassName,
  onPointerDown,
  onContextMenu,
  children,
}: {
  concept: ConceptKind;
  kicker: string;
  title: string;
  subtitle?: ReactNode;
  facts?: TabBannerFact[];
  factsTestId?: string;
  actions?: ReactNode;
  actionsTestId?: string;
  nav?: ReactNode;
  testId?: string;
  ariaLabel?: string;
  bodyRef?: Ref<HTMLDivElement>;
  bodyTestId?: string;
  bodyClassName?: string;
  onPointerDown?: PointerEventHandler<HTMLDivElement>;
  onContextMenu?: MouseEventHandler<HTMLDivElement>;
  children: ReactNode;
}) {
  return (
    <div className={styles.viewport} data-testid={testId} aria-label={ariaLabel}>
      <TabBanner
        concept={concept}
        kicker={kicker}
        title={title}
        subtitle={subtitle}
        facts={facts}
        factsTestId={factsTestId}
        actions={actions}
        actionsTestId={actionsTestId}
      />

      <div
        ref={bodyRef}
        className={cx(styles.body, bodyClassName)}
        data-testid={bodyTestId}
        onPointerDown={onPointerDown}
        onContextMenu={onContextMenu}
      >
        {children}
        {nav}
      </div>
    </div>
  );
}

/** One header action style: quiet by default, blue when active or emphatic. */
export function ViewportAction({
  active,
  emphasis,
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  active?: boolean;
  emphasis?: boolean;
}) {
  return (
    <button
      type="button"
      {...props}
      className={cx(
        styles.action,
        emphasis &&
          "border-accent/60 bg-accent/10 text-accent-strong hover:border-accent hover:text-text",
        className,
      )}
      data-active={active}
    />
  );
}

/** The one navigation cluster: zoom out, percentage, zoom in and Fit. */
export function ViewportNav({
  zoom,
  onZoomOut,
  onZoomIn,
  onFit,
  label = "graph",
  testIds,
}: {
  zoom: number;
  onZoomOut(): void;
  onZoomIn(): void;
  onFit(): void;
  label?: string;
  testIds?: { out?: string; value?: string; in?: string; fit?: string };
}) {
  return (
    <div
      className={styles.nav}
      onPointerDown={(event) => event.stopPropagation()}
      onPointerMove={(event) => event.stopPropagation()}
      onPointerUp={(event) => event.stopPropagation()}
    >
      <button
        type="button"
        onClick={onZoomOut}
        aria-label={`Zoom out ${label}`}
        title="Zoom out"
        data-testid={testIds?.out}
      >
        −
      </button>
      <span className={styles.navOutput} data-testid={testIds?.value}>
        {Math.round(zoom * 100)}%
      </span>
      <button
        type="button"
        onClick={onZoomIn}
        aria-label={`Zoom in ${label}`}
        title="Zoom in"
        data-testid={testIds?.in}
      >
        +
      </button>
      <button
        type="button"
        onClick={onFit}
        aria-label={`Fit ${label}`}
        title={`Fit ${label}`}
        data-testid={testIds?.fit}
      >
        Fit
      </button>
    </div>
  );
}

/** A compact state chip that sits on a viewport canvas. */
export function ViewportChip({
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement>) {
  return <span className={cx(styles.chip, className)} {...props} />;
}

/** A quiet one-line hint on a viewport canvas, anchored bottom right. */
export function ViewportHint({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return <div className={cx(styles.hint, className)}>{children}</div>;
}
