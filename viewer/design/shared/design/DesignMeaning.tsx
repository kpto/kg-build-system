"use client";

import type { SemanticText } from "@/lib/types";
import styles from "./meaning.module.css";

export interface DesignMeaningProps {
  claims: SemanticText[];
  /** Limitations owned by the subject's purpose. */
  limitations: SemanticText[];
  purpose?: string;
  /** Readings carried by a snapshot that predates the purpose model. */
  frames?: Array<{ text: string; limitations?: SemanticText[] }>;
  emptyText?: string;
  /** Use the compact reading for a preview or another bounded surface. */
  compact?: boolean;
}

/**
 * The full meaning of a subject as an argument: its purpose leads, then the
 * contextless claims and the limitations that bound the purpose sit as two
 * labelled groups. The groups stack when the container is too narrow for two
 * readings.
 */
export function DesignMeaning({
  claims,
  limitations,
  purpose,
  frames = [],
  emptyText = "Meaning omitted for this subject.",
  compact = false,
}: DesignMeaningProps) {
  if (!purpose && !claims.length && !limitations.length && !frames.length) {
    return <p className={styles.meaningEmpty}>{emptyText}</p>;
  }

  return (
    <div className={compact ? `${styles.meaning} ${styles.meaningCompact}` : styles.meaning}>
      {purpose ? (
        <div className={styles.meaningPurposeLead}>
          <p className={styles.meaningLabel}>Purpose</p>
          <p className={styles.meaningPurpose}>{purpose}</p>
        </div>
      ) : null}

      {claims.length || limitations.length ? (
        <div className={styles.meaningEvidence}>
          {claims.length ? (
            <div className={styles.meaningGroup}>
              <div className={styles.meaningGroupHead}>
                <p className={styles.meaningLabel}>Claims</p>
                <span className={styles.meaningCount}>{claims.length}</span>
              </div>
              <ul className={styles.meaningClaims}>
                {claims.map((claim) => (
                  <li key={claim.text}>{claim.text}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {limitations.length ? (
            <div className={styles.meaningGroup}>
              <div className={styles.meaningGroupHead}>
                <p className={styles.meaningLabel}>Limitations</p>
                <span className={styles.meaningCount}>
                  {limitations.length}
                </span>
              </div>
              <ul className={styles.meaningLimits}>
                {limitations.map((limitation) => (
                  <li key={limitation.text}>{limitation.text}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}

      {frames.length ? (
        <div className={styles.meaningFrames}>
          {frames.map((frame, index) => (
            <div className={styles.meaningFrame} key={`${frame.text}:${index}`}>
              <p className={styles.meaningLabel}>Earlier reading</p>
              <p className={styles.meaningFrameText}>{frame.text}</p>
              {frame.limitations?.length ? (
                <ul className={styles.meaningLimits}>
                  {frame.limitations.map((limitation) => (
                    <li key={limitation.text}>{limitation.text}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
