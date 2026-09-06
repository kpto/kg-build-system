import clsx from "clsx";
import type { ReactElement, SVGProps } from "react";

/**
 * The seven area glyphs.
 *
 * Hand-drawn at 16 px on a 24 grid instead of pulling in an icon package: the shell
 * needs a dozen marks, they must sit on the 13 px density without optical
 * adjustments, and `stroke="currentColor"` keeps them on the token set.
 */

export type IconName =
  | "topology"
  | "contracts"
  | "projections"
  | "bindings"
  | "sources"
  | "modules"
  | "plan";

const PATHS: Record<IconName, ReactElement> = {
  topology: (
    <>
      <circle cx="5" cy="6" r="2.4" />
      <circle cx="19" cy="6" r="2.4" />
      <circle cx="12" cy="18" r="2.4" />
      <path d="M6.8 7.6 10.4 16M17.2 7.6 13.6 16M7.4 6h9.2" />
    </>
  ),
  contracts: (
    <>
      <rect x="3.5" y="4.5" width="17" height="15" rx="1.5" />
      <path d="M3.5 9.5h17M3.5 14.5h17M10 9.5v10" />
    </>
  ),
  projections: (
    <>
      <path d="M3.5 5h17l-6.6 7.4V19l-3.8 2v-8.6z" />
    </>
  ),
  bindings: (
    <>
      <path d="M9 4.5C6.8 4.5 7.6 9 5.5 9s-1.3 4.5.9 4.5M9 19.5c2.2 0 1.4-4.5 3.5-4.5s1.3-4.5-.9-4.5" />
      <path d="M14.5 8.5 18 12l-3.5 3.5" />
    </>
  ),
  sources: (
    <>
      <ellipse cx="12" cy="6" rx="7.5" ry="2.8" />
      <path d="M4.5 6v12c0 1.6 3.4 2.8 7.5 2.8s7.5-1.2 7.5-2.8V6" />
      <path d="M4.5 12c0 1.6 3.4 2.8 7.5 2.8s7.5-1.2 7.5-2.8" />
    </>
  ),
  modules: (
    <>
      <rect x="3.5" y="3.5" width="7" height="7" rx="1.2" />
      <rect x="13.5" y="3.5" width="7" height="7" rx="1.2" />
      <rect x="3.5" y="13.5" width="7" height="7" rx="1.2" />
      <path d="M14 17h6.5M17.2 13.8v6.4" />
    </>
  ),
  plan: (
    <>
      <rect x="2.5" y="9.5" width="5" height="5" rx="1.2" />
      <rect x="16.5" y="3.5" width="5" height="5" rx="1.2" />
      <rect x="16.5" y="15.5" width="5" height="5" rx="1.2" />
      <path d="M7.5 11.4c4 0 4.4-5.4 9-5.9M7.5 12.6c4 0 4.4 5.4 9 5.9" />
    </>
  ),
};

export interface IconProps extends SVGProps<SVGSVGElement> {
  name: IconName;
  size?: number;
}

export function Icon({ name, size = 16, className, ...rest }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      className={clsx("shrink-0", className)}
      {...rest}
    >
      {PATHS[name]}
    </svg>
  );
}

/* ------------------------------------------------------------------ state glyphs */

export function Dot({ className, pulse }: { className?: string; pulse?: boolean }) {
  return (
    <span
      aria-hidden
      className={clsx(
        "inline-block h-2 w-2 shrink-0 rounded-full",
        pulse && "animate-pulse",
        className,
      )}
    />
  );
}

export function SeverityMark({ severity }: { severity: "error" | "warning" | "info" }) {
  if (severity === "error") {
    return (
      <svg viewBox="0 0 24 24" width={13} height={13} aria-hidden className="shrink-0 text-danger">
        <circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" strokeWidth={1.6} />
        <path d="M12 7.5v6M12 16.4v.2" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" />
      </svg>
    );
  }
  if (severity === "warning") {
    return (
      <svg viewBox="0 0 24 24" width={13} height={13} aria-hidden className="shrink-0 text-warn">
        <path
          d="M12 4.2 21 19.2H3z"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.6}
          strokeLinejoin="round"
        />
        <path d="M12 9.6v4.4M12 16.8v.2" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" width={13} height={13} aria-hidden className="shrink-0 text-info">
      <circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" strokeWidth={1.6} />
      <path d="M12 11v5.2M12 7.8v.2" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" />
    </svg>
  );
}

/* ---------------------------------------------------------------- utility glyphs */

const base = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export const SearchIcon = ({ size = 14, className }: { size?: number; className?: string }) => (
  <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden className={clsx("shrink-0", className)}>
    <circle cx="10.5" cy="10.5" r="6" {...base} />
    <path d="m15.2 15.2 4 4" {...base} />
  </svg>
);

export const CloseIcon = ({ size = 14, className }: { size?: number; className?: string }) => (
  <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden className={clsx("shrink-0", className)}>
    <path d="m6 6 12 12M18 6 6 18" {...base} />
  </svg>
);

export const ChevronIcon = ({
  size = 14,
  open,
  className,
}: {
  size?: number;
  open?: boolean;
  className?: string;
}) => (
  <svg
    viewBox="0 0 24 24"
    width={size}
    height={size}
    aria-hidden
    className={clsx("shrink-0 transition-transform", open && "rotate-90", className)}
  >
    <path d="m9 5 7 7-7 7" {...base} />
  </svg>
);

export const UndoIcon = ({ size = 14, className }: { size?: number; className?: string }) => (
  <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden className={clsx("shrink-0", className)}>
    <path d="M4 9h9.5a5.5 5.5 0 0 1 0 11H8" {...base} />
    <path d="M7.5 5.5 4 9l3.5 3.5" {...base} />
  </svg>
);

export const RedoIcon = ({ size = 14, className }: { size?: number; className?: string }) => (
  <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden className={clsx("shrink-0", className)}>
    <path d="M20 9h-9.5a5.5 5.5 0 0 0 0 11H16" {...base} />
    <path d="M16.5 5.5 20 9l-3.5 3.5" {...base} />
  </svg>
);

export const PlusIcon = ({ size = 14, className }: { size?: number; className?: string }) => (
  <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden className={clsx("shrink-0", className)}>
    <path d="M12 5v14M5 12h14" {...base} />
  </svg>
);

export const RefreshIcon = ({ size = 14, className }: { size?: number; className?: string }) => (
  <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden className={clsx("shrink-0", className)}>
    <path d="M20 12a8 8 0 1 1-2.6-5.9" {...base} />
    <path d="M20 4v4.5h-4.5" {...base} />
  </svg>
);

export const PanelIcon = ({ size = 14, className }: { size?: number; className?: string }) => (
  <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden className={clsx("shrink-0", className)}>
    <rect x="3.5" y="4.5" width="17" height="15" rx="1.5" {...base} />
    <path d="M15 4.5v15" {...base} />
  </svg>
);

export const ListIcon = ({ size = 14, className }: { size?: number; className?: string }) => (
  <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden className={clsx("shrink-0", className)}>
    <path d="M8 7h12M8 12h12M8 17h12M4 7v.2M4 12v.2M4 17v.2" {...base} />
  </svg>
);
