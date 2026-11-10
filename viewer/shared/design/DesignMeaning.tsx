"use client";

import { useState } from "react";
import { ChevronRight } from "lucide-react";

import type { SemanticText, SemanticsFrameDTO } from "@/lib/types";
import { cx } from "@/shared/ui/theme";
import styles from "./design.module.css";

export interface DesignMeaningProps {
  claims: SemanticText[];
  frames: SemanticsFrameDTO[];
  purpose?: string;
  /** Topology uses the compact card; Detail uses the full reading. */
  compact?: boolean;
  /** Include the purpose text above claims and frames. */
  showPurpose?: boolean;
  /** Counts and purpose only; used for the graph summary in sidebars. */
  summaryOnly?: boolean;
  emptyText?: string;
}

function countLabel(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}

export function GraphMeaning({
  claims,
  frames,
  purpose,
  emptyText = "No graph purpose is attached.",
}: {
  claims: SemanticText[];
  frames: SemanticsFrameDTO[];
  purpose?: string;
  emptyText?: string;
}) {
  return (
    <div className={styles.graphMeaning}>
      <DesignMeaning
        claims={claims}
        frames={frames}
        purpose={purpose}
        showPurpose
        summaryOnly
        emptyText={emptyText}
      />
    </div>
  );
}

export function DesignMeaning({
  claims,
  frames,
  purpose,
  compact = false,
  showPurpose = false,
  summaryOnly = false,
  emptyText = "No meaning is attached to this subject.",
}: DesignMeaningProps) {
  const [openFrames, setOpenFrames] = useState<string[]>([]);
  const limitations = frames.flatMap((frame) => frame.limitations ?? []);
  const visibleClaims = compact ? claims.slice(0, 4) : claims;

  if (summaryOnly) {
    if (!purpose && !claims.length && !frames.length) {
      return <p className={styles.meaningEmpty}>{emptyText}</p>;
    }
    return (
      <div className={cx(styles.meaning, styles.meaningCompact)}>
        <div className={styles.meaningCounts}>
          <span>{countLabel(claims.length, "claim")}</span>
          <span>{countLabel(frames.length, "frame")}</span>
          <span>{countLabel(limitations.length, "limitation")}</span>
        </div>
        {purpose ? (
          <p className={styles.meaningPurpose}>{purpose}</p>
        ) : null}
      </div>
    );
  }

  if (!purpose && !claims.length && !frames.length) {
    return <p className={styles.meaningEmpty}>{emptyText}</p>;
  }

  const toggleFrame = (text: string) => {
    setOpenFrames((current) =>
      current.includes(text)
        ? current.filter((value) => value !== text)
        : [...current, text],
    );
  };

  return (
    <div className={cx(styles.meaning, compact && styles.meaningCompact)}>
      <div className={styles.meaningCounts}>
        <span>{countLabel(claims.length, "claim")}</span>
        <span>{countLabel(frames.length, "frame")}</span>
        <span>{countLabel(limitations.length, "limitation")}</span>
      </div>

      {showPurpose && purpose ? (
        <p className={styles.meaningPurpose}>{purpose}</p>
      ) : null}

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

      {frames.length ? (
        <div className={styles.meaningFrames}>
          {frames.map((frame) => {
            const open = openFrames.includes(frame.text);
            const frameLimitations = frame.limitations ?? [];
            return (
              <div key={frame.text} className={styles.meaningFrame}>
                <button
                  type="button"
                  className={styles.meaningFrameHead}
                  aria-expanded={open}
                  onClick={() => toggleFrame(frame.text)}
                  disabled={!frameLimitations.length}
                >
                  <ChevronRight
                    aria-hidden
                    className={cx(
                      styles.meaningChevron,
                      open && styles.meaningChevronOpen,
                    )}
                  />
                  <span>{frame.text}</span>
                  <span className={styles.meaningFrameCount}>
                    {countLabel(frameLimitations.length, "limitation")}
                  </span>
                </button>
                {open ? (
                  <ul className={styles.meaningLimits}>
                    {frameLimitations.map((limitation) => (
                      <li key={limitation.text}>{limitation.text}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
