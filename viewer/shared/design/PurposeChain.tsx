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

/**
 * A compact chain of purposes, one confined box per level.
 *
 * The record axis reads downward: graph → category → component → property.
 * Each box states only the purpose; a purpose longer than the box is clamped,
 * so the box never grows without bound and the rest of the text stays hidden.
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
      {levels.map((level, index) => {
        const current = Boolean(level.current);
        const interactive =
          !current && level.kind !== "graph" && Boolean(onOpen);
        const text = level.purpose ?? "No purpose is stated.";
        return (
          <div key={`${level.kind}:${level.name}`}>
            {index > 0 ? (
              <div className={styles.purposeConnector} aria-hidden>
                <ArrowDown size={12} strokeWidth={1.5} />
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
                  <span className={styles.purposeCurrent}>current</span>
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
  );
}
