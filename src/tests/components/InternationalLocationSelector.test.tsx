import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { beforeEach, expect, it, vi } from "vitest";
import { InternationalLocationSelector } from "@/components/InternationalLocationSelector";
import { fetchInternationalCityPage, type InternationalCity } from "@/lib/api";

vi.mock("@/lib/api", () => ({ fetchInternationalCityPage: vi.fn() }));
const point = (id: number): InternationalCity => ({ id, name: `Place ${id}`, name_en: `Place ${id}`, un_locode: `US${id}`, city_type: "city", is_major_port: false, is_major_airport: false });
const page = (id: number, offset = 0, has_more = false) => ({ items: [point(id)], offset, limit: 50, has_more });
function Harness() {
  const [selected, setSelected] = useState<InternationalCity | null>(null);
  return <InternationalLocationSelector countryId="1" locale="en" side="origin" selected={selected} onChange={setSelected} />;
}
beforeEach(() => vi.resetAllMocks());

it("uses bounded pages and retains selected identity after page and query changes", async () => {
  vi.mocked(fetchInternationalCityPage).mockResolvedValueOnce(page(1, 0, true)).mockResolvedValueOnce(page(51, 50)).mockResolvedValueOnce(page(99));
  render(<Harness />);
  await screen.findByRole("option", { name: /Place 1 / });
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "1" } });
  fireEvent.click(screen.getByRole("button", { name: "More locations" }));
  await screen.findByRole("option", { name: /Place 51 / });
  expect(fetchInternationalCityPage).toHaveBeenLastCalledWith(1, "", 50);
  expect(screen.getByRole("combobox")).toHaveValue("1");
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "US99" } });
  await screen.findByRole("option", { name: /Place 99 / });
  expect(fetchInternationalCityPage).toHaveBeenLastCalledWith(1, "US99", 0);
  expect(screen.getByRole("combobox")).toHaveValue("1");
});

it("separates lookup failure from an empty search and supports retry", async () => {
  vi.mocked(fetchInternationalCityPage).mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({ ...page(1), items: [] });
  render(<Harness />);
  await screen.findByRole("alert");
  expect(screen.queryByText("No locations match this search.")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByText("No locations match this search.");
});

it("discards a response from the prior country after remount", async () => {
  let finish!: (data: ReturnType<typeof page>) => void;
  vi.mocked(fetchInternationalCityPage).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; })).mockResolvedValueOnce(page(2));
  const props = { locale: "en", side: "origin" as const, selected: null, onChange: vi.fn() };
  const view = render(<InternationalLocationSelector key="1" countryId="1" {...props} />);
  await waitFor(() => expect(fetchInternationalCityPage).toHaveBeenCalled());
  view.rerender(<InternationalLocationSelector key="2" countryId="2" {...props} />);
  await screen.findByRole("option", { name: /Place 2 / });
  finish(page(1));
  await waitFor(() => expect(screen.queryByRole("option", { name: /Place 1 / })).not.toBeInTheDocument());
});
