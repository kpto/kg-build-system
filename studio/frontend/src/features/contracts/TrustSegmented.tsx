"use client";

/**
 * The nullability trust control: a three-state segmented switch (declared /
 * enforced / defaulted) mirroring SOURCE_SCHEMA_TRUST_AND_NULLABILITY_SPEC §3. Each
 * segment explains, in one line and in a tooltip, what claiming that trust permits.
 */

import clsx from "clsx";

import { Tooltip } from "@/components/ui";
import type { NullabilityTrust } from "@/lib/ir";
import { TRUST_TIERS, trustTier } from "./logic";

const TONE: Record<NullabilityTrust, string> = {
  declared: "border-info/70 bg-info/15 text-ink",
  enforced: "border-ok/60 bg-ok/15 text-ink",
  defaulted: "border-edge-strong bg-overlay text-muted",
};

export interface TrustSegmentedProps {
  value: NullabilityTrust | undefined;
  onChange(next: NullabilityTrust): void;
  /** Present when the tier cannot honestly carry the field's type (non-null + defaulted). */
  warning?: string | null;
  idPrefix?: string;
}

export function TrustSegmented({ value, onChange, warning, idPrefix = "trust" }: TrustSegmentedProps) {
  const current = trustTier(value);
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <div role="radiogroup" aria-label="Nullability trust" className="inline-flex shrink-0 overflow-hidden rounded-md border border-edge">
        {TRUST_TIERS.map((tier) => {
          const active = tier.value === current.value;
          return (
            <Tooltip key={tier.value} content={<TrustTip tier={tier} />} side="top">
              <button
                type="button"
                role="radio"
                id={`${idPrefix}-${tier.value}`}
                aria-checked={active}
                title={tier.permits}
                onClick={() => onChange(tier.value)}
                className={clsx(
                  "h-6 px-2 text-[11px] transition-colors",
                  active ? TONE[tier.value] : "bg-raised text-muted hover:text-ink",
                  "border-r border-edge last:border-r-0",
                )}
              >
                {tier.label}
              </button>
            </Tooltip>
          );
        })}
      </div>
      <p className={clsx("truncate text-[11px]", warning ? "text-warn" : "text-faint")}>
        {warning ?? current.permits}
      </p>
    </div>
  );
}

function TrustTip({ tier }: { tier: (typeof TRUST_TIERS)[number] }) {
  return (
    <span className="block">
      <span className="font-semibold text-ink">{tier.label}</span> · renders <code className="font-mono text-info">{tier.renders}</code>
      <span className="mt-0.5 block text-muted">{tier.tooltip}</span>
    </span>
  );
}
