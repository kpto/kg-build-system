// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TypePicker, fromTypeDraft, toTypeDraft } from "./TypePicker";
import { array, nullable, structRef, typeLabel, unit } from "@/lib/ir";
import type { LogicalType } from "@/lib/ir";

afterEach(cleanup);

const STRUCTS = [{ module: "kg_project.table.sites", qualname: "PremisesStruct", label: "premises" }];

/** A controlled harness, so clicking through the layers composes a real type. */
function Harness({
  initial,
  onValue,
}: {
  initial: LogicalType;
  onValue(value: LogicalType): void;
}) {
  const [value, setValue] = useState<LogicalType>(initial);
  return (
    <TypePicker
      value={value}
      structs={STRUCTS}
      onChange={(next) => {
        setValue(next);
        onValue(next);
      }}
    />
  );
}

describe("TypePicker", () => {
  it("composes Array[int | None] | None from an int base by picking the layers", () => {
    const onValue = vi.fn();
    render(<Harness initial={unit("int")} onValue={onValue} />);

    fireEvent.click(screen.getByRole("button", { name: "Array[…]" }));
    fireEvent.click(screen.getByRole("button", { name: "items | None" }));
    fireEvent.click(screen.getByRole("button", { name: "| None" }));

    expect(typeLabel(onValue.mock.calls.at(-1)?.[0] as LogicalType)).toBe("Array[int | None] | None");
    expect(screen.getByText("Array[int | None] | None")).toBeDefined();
  });

  it("emits the exact nested structure the backend model expects", () => {
    expect(fromTypeDraft({ nullable: true, array: true, itemNullable: true, base: unit("int") })).toEqual(
      nullable(array(nullable(unit("int")))),
    );
  });

  it("round-trips a type through the draft and back", () => {
    const type = nullable(array(nullable(structRef("kg_project.table.sites", "PremisesStruct"))));
    const draft = toTypeDraft(type);
    expect(draft?.kind).toBe("draft");
    if (draft?.kind === "draft") {
      expect(fromTypeDraft(draft)).toEqual(type);
    }
  });

  it("switches the base to a project struct and keeps the layers above it", () => {
    const onChange = vi.fn();
    render(<TypePicker value={nullable(unit("str"))} onChange={onChange} structs={STRUCTS} units={["int", "str"]} />);

    fireEvent.change(screen.getByLabelText("Base type"), {
      target: { value: "struct:kg_project.table.sites:PremisesStruct" },
    });
    expect(onChange).toHaveBeenLastCalledWith(
      nullable(structRef("kg_project.table.sites", "PremisesStruct")),
    );
  });

  it("shows a nested array as a labelled chip rather than flattening it", () => {
    render(<TypePicker value={array(array(unit("int")))} onChange={vi.fn()} />);
    expect(screen.getByText("Array[Array[int]]")).toBeDefined();
    expect(screen.getByLabelText("Replace type")).toBeDefined();
  });

  it("renders a placeholder for a type that is not there yet", () => {
    render(<TypePicker value={undefined} onChange={vi.fn()} />);
    expect(screen.getByLabelText("No type set")).toBeDefined();
  });
});
