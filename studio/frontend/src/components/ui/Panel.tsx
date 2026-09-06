import type { ReactNode } from "react";
import clsx from "clsx";

/**
 * A titled region of the shell. Every dock, panel and feature surface is a Panel,
 * so the tool has one header rhythm (28 px) and one border language.
 */
export interface PanelProps {
  /** Set so a tab strip's `aria-controls` can point at the panel it owns. */
  id?: string;
  title?: ReactNode;
  /** Right-aligned controls: filters, counts, actions. */
  actions?: ReactNode;
  /** A second line under the title, kept quiet on purpose. */
  subtitle?: ReactNode;
  children?: ReactNode;
  className?: string;
  bodyClassName?: string;
  /** `false` removes the body padding for lists that manage their own. */
  padded?: boolean;
  role?: "region" | "complementary" | "navigation" | "toolbar";
}

export function Panel({
  id,
  title,
  actions,
  subtitle,
  children,
  className,
  bodyClassName,
  padded = true,
  role = "region",
}: PanelProps) {
  return (
    <section
      id={id}
      role={role}
      aria-label={typeof title === "string" ? title : undefined}
      className={clsx("flex min-h-0 min-w-0 flex-col bg-surface", className)}
    >
      {(title !== undefined || actions !== undefined) && (
        <header className="flex h-8 shrink-0 items-center gap-2 border-b border-edge px-2.5">
          <h2 className="truncate text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
            {title}
          </h2>
          {subtitle !== undefined && (
            <span className="truncate text-[11px] text-faint">{subtitle}</span>
          )}
          {actions !== undefined && (
            <div className="ml-auto flex shrink-0 items-center gap-1.5">{actions}</div>
          )}
        </header>
      )}
      <div className={clsx("min-h-0 flex-1 overflow-auto", padded && "p-2.5", bodyClassName)}>
        {children}
      </div>
    </section>
  );
}
