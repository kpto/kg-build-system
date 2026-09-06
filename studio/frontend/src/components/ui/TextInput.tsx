"use client";

import type { InputHTMLAttributes } from "react";
import clsx from "clsx";

import { CONTROL, CONTROL_MONO } from "./control";

export interface TextInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
  /** Monospace for ids, refs, paths and literal values. */
  mono?: boolean;
  invalid?: boolean;
}

export function TextInput({ className, mono, invalid, ...rest }: TextInputProps) {
  return (
    <input
      {...rest}
      aria-invalid={invalid || undefined}
      className={clsx(
        CONTROL,
        mono && CONTROL_MONO,
        invalid && "border-danger focus:border-danger",
        className,
      )}
    />
  );
}
