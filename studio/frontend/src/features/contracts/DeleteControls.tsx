"use client";

/**
 * The delete controls shared by every declaration the contracts areas own —
 * tables, structs and projections — so "what still points at this?" is answered the
 * same way wherever the user asks it.
 */

import { Button, Chip, Modal } from "@/components/ui";
import type { Referrer } from "./logic";

export function DeleteButton({ label, onClick }: { label: string; onClick(): void }) {
  return (
    <Button size="sm" variant="danger" onClick={onClick}>
      delete {label}
    </Button>
  );
}

/**
 * The delete confirmation. When `pending` holds referrers the deletion is blocked and
 * the referrers are listed; when it is an empty array the delete proceeds.
 */
export function DeleteDialog({
  pending,
  onCancel,
  onConfirm,
}: {
  pending: Referrer[] | null;
  onCancel(): void;
  onConfirm(): void;
}) {
  if (pending === null) return null;
  const blocked = pending.length > 0;
  return (
    <Modal
      open
      onClose={onCancel}
      title={blocked ? "Cannot delete — still referenced" : "Confirm delete"}
      footer={
        blocked ? (
          <Button variant="primary" onClick={onCancel}>
            keep it
          </Button>
        ) : (
          <>
            <Button onClick={onCancel}>cancel</Button>
            <Button variant="danger" onClick={onConfirm}>
              delete
            </Button>
          </>
        )
      }
    >
      {blocked ? (
        <div className="flex flex-col gap-2">
          <p className="text-[12px] text-ink">
            This declaration is still referenced by {pending.length} item{pending.length === 1 ? "" : "s"}. Deleting it would dangle those
            references, so the delete is blocked. Remove or repoint them first.
          </p>
          <ul className="flex flex-col gap-1">
            {pending.map((referrer) => (
              <li key={`${referrer.ref}:${referrer.label}`} className="flex items-center gap-2 rounded border border-danger/40 bg-danger/10 px-2 py-1">
                <Chip tone="danger">{referrer.kind}</Chip>
                <span className="min-w-0 flex-1 truncate font-mono text-[11px] text-ink">{referrer.label}</span>
                <span className="shrink-0 font-mono text-[10px] text-faint">{referrer.ref}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-[12px] text-ink">Nothing references this declaration. Deleting removes it from the project.</p>
      )}
    </Modal>
  );
}
