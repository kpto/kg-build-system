"use client";

import type { SemanticText } from "@/lib/types";
import { cx } from "@/shared/ui/theme";
import styles from "./meaning.module.css";

export interface DesignMeaningProps {
  claims: SemanticText[];
  /** Limitations owned by the subject's purpose. */
  limitations: SemanticText[];
  purpose?: string;
  /** Readings carried by a snapshot that predates the purpose model. */
  frames?: Array<{ text: string; limitations?: SemanticText[] }>;
  /** Topology uses the compact card; Detail uses the full reading. */
  compact?: boolean;
  emptyText?: string;
}

function countLabel(count: number, noun: string): string {
  if (count === 1) return `${count} ${noun}`;
  const plural = noun.endsWith("y")
    ? `${noun.slice(0, -1)}ies`
    : noun.endsWith("s")
      ? noun
      : `${noun}s`;
  return `${count} ${plural}`;
}

export function DesignMeaning({
  claims,
  limitations,
  purpose,
  frames = [],
  compact = false,
  emptyText = "Meaning omitted for this subject.",
}: DesignMeaningProps) {
  const visibleClaims = compact ? claims.slice(0, 4) : claims;
  const visibleFrames = compact ? frames.slice(0, 2) : frames;

  if (!purpose && !claims.length && !limitations.length && !frames.length) {
    return <p className={styles.meaningEmpty}>{emptyText}</p>;
  }

  const limitationCount =
    limitations.length +
    frames.reduce(
      (total, frame) => total + (frame.limitations?.length ?? 0),
      0,
    );

  return (
    <div className={cx(styles.meaning, compact && styles.meaningCompact)}>
      <div className={styles.meaningCounts}>
        <span>{countLabel(claims.length, "claim")}</span>
        <span>{countLabel(limitationCount, "limitation")}</span>
      </div>

      {purpose ? <p className={styles.meaningPurpose}>{purpose}</p> : null}

      {visibleFrames.map((frame, index) => (
        <div className={styles.meaningFrame} key={`${frame.text}:${index}`}>
          <p className={styles.meaningPurpose}>{frame.text}</p>
          <ul className={styles.meaningLimits}>
            {(frame.limitations ?? []).map((limitation) => (
              <li key={limitation.text}>{limitation.text}</li>
            ))}
          </ul>
        </div>
      ))}

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
