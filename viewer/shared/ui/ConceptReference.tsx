import type { CSSProperties } from "react";

import type { ConceptReference } from "@/lib/concepts";
import { ConceptGlyph } from "./ConceptMark";
import { concepts } from "./concepts";

/**
 * One navigable concept reference. The same component renders an asset, table
 * or projection wherever a reference appears; the concept's icon and colour
 * come from the canonical registry.
 */
export function ConceptReferenceChip({
  reference,
  onOpen,
  className,
  showIcon = true,
}: {
  reference: ConceptReference;
  onOpen?(): void;
  className?: string;
  showIcon?: boolean;
}) {
  const definition = concepts[reference.concept];
  const style = {
    "--concept-color": definition.color,
    borderColor:
      "color-mix(in srgb, var(--concept-color) 45%, var(--color-line-soft))",
    backgroundColor:
      "color-mix(in srgb, var(--concept-color) 10%, transparent)",
    color: definition.color,
  } as CSSProperties;
  const classes = [
    "inline-flex max-w-full items-center gap-1 rounded border px-1.5 py-0.5 font-mono text-[9px]",
    onOpen ? "cursor-pointer hover:underline" : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");
  const content = (
    <>
      {showIcon ? (
        <ConceptGlyph
          concept={reference.concept}
          className="size-3 shrink-0"
        />
      ) : null}
      <span className="min-w-0 truncate">{reference.name}</span>
    </>
  );

  if (!onOpen) {
    return (
      <span
        className={classes}
        style={style}
        data-concept={reference.concept}
      >
        {content}
      </span>
    );
  }

  return (
    <button
      type="button"
      className={classes}
      style={style}
      data-concept={reference.concept}
      title={`Open ${definition.label.toLowerCase()} ${reference.name}`}
      onClick={onOpen}
    >
      {content}
    </button>
  );
}
