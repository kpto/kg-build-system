import type {
  ComponentPropsWithoutRef,
  ReactNode,
} from "react";

import { cx } from "./theme";
import styles from "./primitives.module.css";

/** A bordered feature surface. */
export function Panel({
  as: Tag = "div",
  className,
  ...props
}: ComponentPropsWithoutRef<"div"> & { as?: "div" | "aside" | "section" }) {
  return <Tag className={cx(styles.panel, className)} {...props} />;
}

/** The raised header of a panel. */
export function PanelHeader({
  as: Tag = "div",
  className,
  ...props
}: ComponentPropsWithoutRef<"div"> & { as?: "div" | "header" }) {
  return <Tag className={cx(styles.panelHeader, className)} {...props} />;
}

/** A small uppercase field label. */
export function Label({
  className,
  ...props
}: ComponentPropsWithoutRef<"span">) {
  return <span className={cx(styles.label, className)} {...props} />;
}

/** A faint mono count or identifier. */
export function Meta({
  className,
  ...props
}: ComponentPropsWithoutRef<"span">) {
  return <span className={cx(styles.meta, className)} {...props} />;
}

/** A list row. */
export function Row({
  className,
  ...props
}: ComponentPropsWithoutRef<"div">) {
  return <div className={cx(styles.row, className)} {...props} />;
}

/** A list row that navigates. */
export function RowButton({
  className,
  type = "button",
  ...props
}: ComponentPropsWithoutRef<"button">) {
  return (
    <button
      type={type}
      className={cx(styles.row, styles.rowButton, className)}
      {...props}
    />
  );
}

/** One label/value pair. */
export function Field({
  label,
  value,
  className,
}: {
  label: ReactNode;
  value: ReactNode;
  className?: string;
}) {
  return (
    <div className={cx(styles.field, className)}>
      <span className={styles.fieldLabel}>{label}</span>
      <span className={styles.fieldValue}>{value}</span>
    </div>
  );
}

/** A quiet control. */
export function Control({
  className,
  type = "button",
  ...props
}: ComponentPropsWithoutRef<"button">) {
  return (
    <button type={type} className={cx(styles.control, className)} {...props} />
  );
}

/** A single-line field. */
export function Input({
  className,
  ...props
}: ComponentPropsWithoutRef<"input">) {
  return <input className={cx(styles.input, className)} {...props} />;
}

export function Select({
  className,
  ...props
}: ComponentPropsWithoutRef<"select">) {
  return <select className={cx(styles.input, className)} {...props} />;
}

export function Empty({
  className,
  ...props
}: ComponentPropsWithoutRef<"p">) {
  return <p className={cx(styles.empty, className)} {...props} />;
}

export function Hint({
  className,
  ...props
}: ComponentPropsWithoutRef<"p">) {
  return <p className={cx(styles.hint, className)} {...props} />;
}

export function Kbd({
  className,
  ...props
}: ComponentPropsWithoutRef<"kbd">) {
  return <kbd className={cx(styles.kbd, className)} {...props} />;
}
