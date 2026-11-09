"use client";

import type { ReactNode } from "react";
import {
  AlertOctagon,
  ArrowUpRight,
  Braces,
  Check,
  ChevronDown,
  CircleAlert,
  ClipboardCheck,
  ClipboardCopy,
  Code,
  Compass,
  Database,
  FileText,
  GitBranch,
  GitCompare,
  Grid3x3,
  Hammer,
  Info,
  ListTree,
  Map as MapIcon,
  Maximize,
  MessageCircleQuestion,
  Package,
  Pin,
  RotateCcw,
  Scale,
  Search,
  SlidersHorizontal,
  ZoomIn,
} from "lucide-react";
import type { IconToken, Tone } from "@/shared/model/hierarchy";
import type {
  AuditActionModel,
  AuditVerificationModel,
} from "@/audit/model/AuditModel";
import { cx, severityColor } from "@/shared/ui/theme";
import type { DecisionStatus, ReviewStatus, Severity } from "@/lib/reviewTypes";

/**
 * Icons are model tokens; this is the only place that translates a token into a
 * component. The model never imports lucide or JSX.
 */
export function AuditIcon({
  token,
  className = "size-3",
}: {
  token: IconToken;
  className?: string;
}) {
  const Icon = ICONS[token] ?? Info;
  return <Icon aria-hidden className={className} />;
}

const ICONS: Record<IconToken, typeof Info> = {
  map: MapIcon,
  explore: Compass,
  review: Scale,
  workflow: Hammer,
  blueprint: Package,
  lineage: GitBranch,
  outliner: ListTree,
  navigator: Compass,
  properties: SlidersHorizontal,
  audit: ClipboardCheck,
  fit: Maximize,
  read: FileText,
  copy: ClipboardCopy,
  search: Search,
  import: Package,
  zoom: ZoomIn,
  focus: Pin,
  reset: RotateCcw,
  collapse: ChevronDown,
  expand: ChevronDown,
  trace: GitBranch,
  branch: GitCompare,
  layers: Grid3x3,
  braces: Braces,
  asset: Database,
  binding: GitBranch,
  field: Braces,
  code: Code,
  info: CircleAlert,
  question: MessageCircleQuestion,
  warning: AlertOctagon,
  check: Check,
  open: ArrowUpRight,
};

const TONE_TEXT: Record<Tone, string> = {
  neutral: "text-muted",
  accent: "text-accent",
  selection: "text-selection",
  critical: "text-critical",
  high: "text-high",
  medium: "text-medium",
  low: "text-low",
  info: "text-info",
};

export function toneText(tone: Tone | undefined): string | undefined {
  return tone ? TONE_TEXT[tone] : undefined;
}

export function verificationText(
  tone: AuditVerificationModel["tone"],
): string {
  switch (tone) {
    case "amber":
      return "text-medium";
    case "red":
      return "text-critical";
    case "green":
      return "text-asset";
    default:
      return "text-muted";
  }
}

export type ActionVariant = "button" | "ghost" | "chip" | "dossier";

/**
 * One bound action. The view maps a view-bound kind to its local state; command
 * actions run the command carried by the model.
 *
 * `iconOnly` keeps the action in the tree and reachable by name while showing
 * only its icon; the caller supplies the reveal state (for example on row
 * hover).
 */
export function ActionButton({
  action,
  onActivate,
  variant = "button",
  label,
  className,
  iconOnly = false,
}: {
  action: AuditActionModel;
  onActivate?: (action: AuditActionModel) => void;
  variant?: ActionVariant;
  label?: ReactNode;
  className?: string;
  iconOnly?: boolean;
}) {
  if (variant === "dossier") {
    return (
      <button
        type="button"
        data-testid={action.testId}
        disabled={action.disabled}
        onClick={() => (onActivate ? onActivate(action) : action.run?.())}
        title={action.title ?? action.label}
        className={cx(
          "flex min-h-9 w-full items-start gap-2 rounded-[3px] px-2 py-1.5 text-left text-muted transition-colors hover:bg-panel-soft hover:text-text",
          action.primary && "text-accent-strong",
          className,
        )}
      >
        {action.icon ? (
          <AuditIcon token={action.icon} className="mt-0.5 size-3.5 shrink-0" />
        ) : null}
        <span className="min-w-0">
          <span className="block text-[12px] leading-tight">
            {label ?? action.label}
          </span>
          {action.hint ? (
            <span className="mt-0.5 block text-[11px] leading-snug text-faint">
              {action.hint}
            </span>
          ) : null}
        </span>
      </button>
    );
  }

  if (variant === "chip") {
    return (
      <button
        type="button"
        data-testid={action.testId}
        disabled={action.disabled}
        onClick={(event) => {
          event.stopPropagation();
          if (onActivate) onActivate(action);
          else action.run?.();
        }}
        title={action.title ?? action.label}
        className={cx(
          "max-w-full cursor-pointer truncate rounded-[2px] px-1 text-left text-[11px] text-muted underline-offset-2 hover:bg-panel-soft hover:text-accent-strong hover:underline",
          toneText(action.tone),
          className,
        )}
      >
        {label ?? action.label}
      </button>
    );
  }

  if (iconOnly) {
    return (
      <button
        type="button"
        data-testid={action.testId}
        disabled={action.disabled}
        aria-label={action.label}
        title={action.title ?? action.label}
        onClick={(event) => {
          event.stopPropagation();
          if (onActivate) onActivate(action);
          else action.run?.();
        }}
        className={cx("ui-icon-button size-6", className)}
      >
        {action.icon ? <AuditIcon token={action.icon} className="size-3" /> : null}
      </button>
    );
  }

  return (
    <button
      type="button"
      data-testid={action.testId}
      disabled={action.disabled}
      aria-pressed={action.pressed}
      title={action.title ?? action.label}
      onClick={(event) => {
        event.stopPropagation();
        if (onActivate) onActivate(action);
        else action.run?.();
      }}
      className={cx(
        "ui-button h-[26px] min-h-0 px-2 text-[11px]",
        variant === "ghost"
          ? "ui-button-ghost hover:text-accent"
          : undefined,
        className,
      )}
    >
      {action.icon ? <AuditIcon token={action.icon} className="size-3" /> : null}
      {label ?? action.label}
    </button>
  );
}

const REVIEW_STATUS_TONE: Record<ReviewStatus, string> = {
  open: "border-accent/45 bg-accent/10 text-accent",
  acknowledged: "border-medium/40 bg-medium/10 text-medium",
  waived: "border-line bg-panel-soft text-muted",
  resolved: "border-asset/40 bg-asset/10 text-asset",
};

const REVIEW_STATUS_DOT: Record<ReviewStatus, string> = {
  open: "bg-accent",
  acknowledged: "bg-medium",
  waived: "bg-faint",
  resolved: "bg-asset",
};

const DECISION_STATUS_TONE: Record<DecisionStatus, string> = {
  open: "border-accent/45 bg-accent/10 text-accent",
  proposed: "border-medium/40 bg-medium/10 text-medium",
  accepted: "border-asset/40 bg-asset/10 text-asset",
  rejected: "border-critical/40 bg-critical/10 text-critical",
};

const DECISION_STATUS_DOT: Record<DecisionStatus, string> = {
  open: "bg-accent",
  proposed: "bg-medium",
  accepted: "bg-asset",
  rejected: "bg-critical",
};

export function StatusBadge({
  status,
}: {
  status: ReviewStatus | DecisionStatus;
}) {
  const review = status in REVIEW_STATUS_TONE;
  const tone = review
    ? REVIEW_STATUS_TONE[status as ReviewStatus]
    : DECISION_STATUS_TONE[status as DecisionStatus];
  const dot = review
    ? REVIEW_STATUS_DOT[status as ReviewStatus]
    : DECISION_STATUS_DOT[status as DecisionStatus];
  return (
    <span className={cx("ui-chip lowercase text-[10.5px]", tone)}>
      <span aria-hidden className={cx("size-1 rounded-full", dot)} />
      {status}
    </span>
  );
}

export function SeverityDot({
  severity,
  className = "",
}: {
  severity: Severity;
  className?: string;
}) {
  return (
    <span
      aria-hidden
      style={{ backgroundColor: severityColor[severity] }}
      className={cx("inline-block size-1.5 shrink-0 rounded-full", className)}
    />
  );
}

/** Empty is a state of the section body, not a bordered card. */
export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <p className="px-3 py-3 text-[11.5px] leading-relaxed text-faint">
      {children}
    </p>
  );
}
