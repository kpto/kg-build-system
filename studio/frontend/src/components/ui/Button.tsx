"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";
import clsx from "clsx";

type Variant = "default" | "primary" | "ghost" | "danger";

const VARIANT: Record<Variant, string> = {
  default: "border-edge bg-raised text-ink hover:border-edge-strong hover:bg-overlay",
  primary: "border-info/60 bg-info/15 text-ink hover:bg-info/25",
  ghost: "border-transparent bg-transparent text-muted hover:bg-raised hover:text-ink",
  danger: "border-danger/50 bg-danger/10 text-danger hover:bg-danger/20",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  icon?: ReactNode;
  size?: "sm" | "md";
}

export function Button({
  variant = "default",
  icon,
  size = "md",
  className,
  children,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      type={type}
      className={clsx(
        "inline-flex shrink-0 items-center gap-1.5 rounded-md border font-medium transition-colors",
        size === "sm" ? "h-6 px-1.5 text-[11px]" : "h-7 px-2.5 text-[12px]",
        "disabled:cursor-not-allowed disabled:opacity-40",
        VARIANT[variant],
        className,
      )}
    >
      {icon}
      <span className="truncate">{children}</span>
    </button>
  );
}

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Required: the accessible name, since the button shows only a glyph. */
  label: string;
  icon: ReactNode;
  variant?: Variant;
  active?: boolean;
  size?: "sm" | "md";
}

export function IconButton({
  label,
  icon,
  variant = "ghost",
  active,
  size = "md",
  className,
  type = "button",
  ...rest
}: IconButtonProps) {
  return (
    <button
      {...rest}
      type={type}
      aria-label={label}
      title={label}
      aria-pressed={active}
      className={clsx(
        "inline-flex shrink-0 items-center justify-center rounded-md border transition-colors",
        size === "sm" ? "h-6 w-6" : "h-7 w-7",
        "disabled:cursor-not-allowed disabled:opacity-40",
        VARIANT[variant],
        active && "border-info text-ink",
        className,
      )}
    >
      {icon}
    </button>
  );
}
