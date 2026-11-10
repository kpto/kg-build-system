import type { ReactNode } from "react";

import styles from "../detail.module.css";

export interface DetailDocumentProps {
  kicker: string;
  title: string;
  subtitle?: ReactNode;
  icon?: ReactNode;
  testId?: string;
  children: ReactNode;
}

/**
 * The shared chrome of a detail document: sticky top bar, title block and one
 * padded body. Node, property, asset and step documents use the same surface.
 */
export function DetailDocument({
  kicker,
  title,
  subtitle,
  icon,
  testId,
  children,
}: DetailDocumentProps) {
  return (
    <div className={styles.root} data-testid={testId}>
      <header className={styles.topbar}>
        <div className={styles.titleBlock}>
          <p className={styles.kicker}>
            {icon}
            {kicker}
          </p>
          <h1 className={styles.title}>{title}</h1>
          {subtitle ? <p className={styles.subtitle}>{subtitle}</p> : null}
        </div>
      </header>
      <div className={styles.body}>{children}</div>
    </div>
  );
}

export interface DetailPanelProps {
  title: string;
  meta?: ReactNode;
  className?: string;
  children: ReactNode;
}

export function DetailPanel({
  title,
  meta,
  className,
  children,
}: DetailPanelProps) {
  return (
    <section className={`${styles.panel} ${className ?? ""}`}>
      <header className={styles.panelHead}>
        <h2>{title}</h2>
        {meta ? <span className={styles.panelMeta}>{meta}</span> : null}
      </header>
      <div className={styles.panelBody}>{children}</div>
    </section>
  );
}

export function DetailEmptyState({ children }: { children: ReactNode }) {
  return <p className={styles.empty}>{children}</p>;
}
