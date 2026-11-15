"use client";

import type { SemanticText } from "@/lib/types";
import { cx } from "@/shared/ui/theme";
import styles from "./design.module.css";

export interface DesignMeaningProps {
  claims: SemanticText[];
  /** Limitations owned by the subject's purpose. */
  limitations: SemanticText[];
  purpose?: string;
  /** Topology uses the compact card; Detail uses the full reading. */
  compact?: boolean;
  emptyText?: string;
}

function countLabel(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}

export function DesignMeaning({
  claims,
  limitations,
  purpose,
  compact = false,
  emptyText = "No meaning is attached to this subject.",
}: DesignMeaningProps) {
  const visibleClaims = compact ? claims.slice(0, 4) : claims;

  if (!purpose && !claims.length && !limitations.length) {
    return <p className={styles.meaningEmpty}>{emptyText}</p>;
  }

  return (
    <div className={cx(styles.meaning, compact && styles.meaningCompact)}>
      <div className={styles.meaningCounts}>
        <span>{countLabel(claims.length, "claim")}</span>
        <span>{countLabel(limitations.length, "limitation")}</span>
      </div>

      {purpose ? <p className={styles.meaningPurpose}>{purpose}</p> : null}

      {claims.length ? (
        <ul className={styles.meaningClaims}>
          {visibleClaims.map((claim) => (
            <li key={claim.text}>{claim.text}</li>
          ))}
          {visibleClaims.length < claims.length ? (
            <li className={styles.meaningMore}>
              {countLabel(claims.length - visibleClaims.length, "claim")} more
            </li>
          ) : null}
        </ul>
      ) : null}

      {limitations.length ? (
        <ul className={styles.meaningLimits}>
          {limitations.map((limitation) => (
            <li key={limitation.text}>{limitation.text}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
