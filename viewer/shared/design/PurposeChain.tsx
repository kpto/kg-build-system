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

const INDENT = 26;

/**
 * The record-axis purpose chain, drawn as a descent.
 *
 * Each level steps in from the one above, and a single accent spine runs from
 * the graph root to the current declaration. The step and the spine state that
 * a local purpose is read under its parent and narrows it; every level keeps
 * its own text, so this is derivation, not copied meaning.
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
          const depth = index * INDENT;
          return (
            <div
              className={styles.purposeLevel}
              key={`${level.kind}:${level.name}`}
            >
              {index > 0 ? (
                <div
                  className={styles.purposeConnector}
                  style={{ marginLeft: `${depth + 130 - 7}px` }}
                  aria-hidden
                >
                  <span className={styles.purposeConnectorLine} />
                  <ArrowDown size={13} strokeWidth={1.8} />
                </div>
              ) : null}
              <div
                className={styles.purposeRow}
                data-current={current || undefined}
                style={{ paddingLeft: `${depth}px` }}
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
                  <div className={styles.purposeBox} title={text}>
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
