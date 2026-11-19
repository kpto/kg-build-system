import type { CSSProperties, ReactNode } from "react";

import type { ConceptKind } from "@/lib/concepts";
import { ConceptMark } from "./ConceptMark";
import { cx } from "@kbs/design";
import styles from "./tabBanner.module.css";

export interface TabBannerFact {
  label: string;
  value: ReactNode;
  title?: string;
}

export interface TabBannerProps {
  concept: ConceptKind;
  kicker: string;
  title: string;
  subtitle?: ReactNode;
  facts?: TabBannerFact[];
  actions?: ReactNode;
  actionsTestId?: string;
  testId?: string;
  factsTestId?: string;
  className?: string;
}

/**
 * The one banner above a tab's editor. Every tab — detail, Graph or Workflow —
 * states the same three things in the same order: what the document is, its
 * overview facts, and its view actions.
 */
export function TabBanner({
  concept,
  kicker,
  title,
  subtitle,
  facts = [],
  actions,
  actionsTestId,
  testId,
  factsTestId,
  className,
}: TabBannerProps) {
  return (
    <header className={cx(styles.banner, className)} data-testid={testId}>
      <div className={styles.identity}>
        <ConceptMark concept={concept} className={styles.mark} />
        <div className={styles.titles}>
          <p className={styles.kicker}>{kicker}</p>
          <h1 className={styles.title}>{title}</h1>
          {subtitle ? <p className={styles.subtitle}>{subtitle}</p> : null}
        </div>
      </div>

      {facts.length ? (
        <dl className={styles.overview} data-testid={factsTestId}>
          {facts.map((fact) => (
            <div className={styles.fact} key={fact.label}>
              <dt className={styles.factLabel}>{fact.label}</dt>
              <dd className={styles.factValue} title={fact.title}>
                {fact.value}
              </dd>
            </div>
          ))}
        </dl>
      ) : (
        <span className={styles.overview} data-testid={factsTestId} />
      )}

      {actions ? (
        <div className={styles.actions} data-testid={actionsTestId}>
          {actions}
        </div>
      ) : null}
    </header>
  );
}
