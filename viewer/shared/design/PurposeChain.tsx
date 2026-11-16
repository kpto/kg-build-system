"use client";

import { ArrowDown } from "lucide-react";

import { cx } from "@/shared/ui/theme";
import type { PurposeLevel } from "./meaning";
import styles from "./design.module.css";

export interface PurposeChainProps {
  levels: PurposeLevel[];
  onOpen?(level: PurposeLevel): void;
  emptyText?: string;
}

/** The root is the broad premise; each narrower purpose is 14% shorter. */
const WIDTH_STEP = 14;

/**
 * The record-axis purpose chain: labels on the left, a tapering purpose box on
 * the right.
 *
 * The root is the widest box; each level narrows it and steps in at the right
 * edge. A single accent spine marks the descent, and the current level is
 * tinted. Each box shows only the purpose, clamped, so a long purpose hides the
 * remainder. The scheme is derivation, not copied meaning.
 */
export function PurposeChain({
  levels,
  onOpen,
  emptyText = "Meaning omitted.",
}: PurposeChainProps) {
  if (!levels.length) {
    return <p className={styles.purposeEmpty}>{emptyText}</p>;
  }

  return (
    <div className={styles.purposeChain} aria-label="Purpose hierarchy">
      <header className={styles.purposeHead}>
        <span>Purpose hierarchy</span>
        <span>each level narrows the one above</span>
      </header>
      <div className={styles.purposeLevels}>
        {levels.map((level, index) => {
          const current = Boolean(level.current);
          const interactive =
            !current && level.kind !== "graph" && Boolean(onOpen);
          const text = level.purpose ?? "No purpose is stated.";
          const width = 100 - index * WIDTH_STEP;
          return (
            <div
              className={styles.purposeLevel}
              key={`${level.kind}:${level.name}`}
            >
              {index > 0 ? (
                <div className={styles.purposeConnectorRow} aria-hidden>
                  <span />
                  <div
                    className={styles.purposeConnectorCell}
                    style={{ width: `${width}%` }}
                  >
                    <span className={styles.purposeConnectorLine} />
                    <ArrowDown size={13} strokeWidth={1.8} />
                  </div>
                </div>
              ) : null}
              <div
                className={styles.purposeRow}
                data-current={current || undefined}
              >
                <div className={styles.purposeMeta}>
                  <span className={styles.purposeKind}>{level.label}</span>
                  <span className={styles.purposeName}>{level.name}</span>
                  {current ? (
                    <span className={styles.purposeTag} data-current>
                      current
                    </span>
                  ) : index === 0 ? (
                    <span className={styles.purposeTag}>root</span>
                  ) : null}
                </div>
                {interactive ? (
                  <button
                    type="button"
                    className={styles.purposeBox}
                    style={{ width: `${width}%` }}
                    onClick={() => onOpen?.(level)}
                    title={`${text} — open ${level.name}`}
                  >
                    <span
                      className={cx(
                        styles.purposeText,
                        !level.purpose && styles.purposeMissing,
                      )}
                    >
                      {text}
                    </span>
                  </button>
                ) : (
                  <div
                    className={styles.purposeBox}
                    style={{ width: `${width}%` }}
                    title={text}
                  >
                    <span
                      className={cx(
                        styles.purposeText,
                        !level.purpose && styles.purposeMissing,
                      )}
                    >
                      {text}
                    </span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
      <p className={styles.purposeNote}>
        A child reads under its parent and narrows it; every level keeps its own
        text, so the chain shows derivation, not copied meaning.
      </p>
    </div>
  );
}
