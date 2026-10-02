import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import LocalizedDateTimeInput from "@/components/LocalizedDateTimeInput";
import OccurrenceTimeAction from "@/components/OccurrenceTimeAction";

it("displays a seconds-bearing occurrence without substituting today's midnight", () => {
  const change = vi.fn();
  render(<LocalizedDateTimeInput value="2026-10-02T18:53:54" onChange={change} />);
  expect(screen.getByRole("button", { name: /18:53/ })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /18:53/ }));
  fireEvent.click(screen.getByRole("button", { name: "میلادی" }));
  expect(change).not.toHaveBeenCalled();
  expect(screen.getByRole("combobox", { name: "زمان ساعت" })).toHaveValue("18");
});

it("requires explicit successor occurrence time instead of retaining departure time", () => {
  const submit = vi.fn();
  const { rerender } = render(<OccurrenceTimeAction id="leg-1-time" action="ثبت حرکت" pending={false} onSubmit={submit} />);
  fireEvent.change(screen.getByLabelText("زمان وقوع"), { target: { value: "2026-10-02T18:53" } });
  fireEvent.click(screen.getByRole("button", { name: "ثبت حرکت" }));
  expect(submit).toHaveBeenCalledTimes(1);
  rerender(<OccurrenceTimeAction id="leg-1-time" action="ثبت رسیدن" pending={false} onSubmit={submit} />);
  fireEvent.click(screen.getByRole("button", { name: "ثبت رسیدن" }));
  expect(submit).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("alert")).toBeInTheDocument();
});
