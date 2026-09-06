import type { ReactNode } from "react";
import clsx from "clsx";

export type ChipTone = "neutral" | "node" | "relation" | "category" | "template" | "danger" | "warn" | "ok" | "info";

/**
 * `studio-chip` plus the vocabulary tones from globals.css. The tone is the
 * component kind (node / category / relation / template) or the problem severity —
 * never an ad-hoc colour.
 */
export interface ChipProps {
  children: ReactNode;
  tone?: ChipTone;
  /** Selected chips read as filled, unselected as outlined. */
  active?: boolean;
  onClick?(): void;
  onRemove?(): void;
  icon?: ReactNode;
  title?: string;
  className?: string;
  /** Remove the mono font for prose chips (filter labels). */
  plain?: boolean;
}

const TONE_CLASS: Record<ChipTone, string> = {
  neutral: "",
  node: "border-node/50 bg-node-soft text-node",
  relation: "border-relation/50 bg-relation-soft text-relation",
  category: "border-category/50 bg-raised text-category",
  template: "border-template/50 bg-raised text-template",
  danger: "border-danger/50 bg-danger/10 text-danger",
  warn: "border-warn/50 bg-warn/10 text-warn",
  ok: "border-ok/50 bg-ok/10 text-ok",
  info: "border-info/50 bg-info/10 text-info",
};

export function Chip({
  children,
  tone = "neutral",
  active = false,
  onClick,
  onRemove,
  icon,
  title,
  className,
  plain = false,
}: ChipProps) {
  const content = (
    <>
      {icon}
      <span className={clsx("truncate", plain && "font-sans text-[11px]")}>{children}</span>
      {onRemove && (
        <span
          aria-hidden
          className="-mr-1 text-faint hover:text-ink"
          onClick={(event) => {
            event.stopPropagation();
            onRemove();
          }}
        >
          ×
        </span>
      )}
    </>
  );

  const classes = clsx(
    "studio-chip max-w-full",
    !plain && "font-mono",
    TONE_CLASS[tone],
    active && "border-info text-ink ring-1 ring-info",
    onClick && "cursor-pointer hover:border-edge-strong",
    className,
  );

  if (onClick) {
    return (
      <button type="button" title={title} aria-pressed={active} className={classes} onClick={onClick}>
        {content}
      </button>
    );
  }
  return (
    <span title={title} className={classes}>
      {content}
    </span>
  );
}
