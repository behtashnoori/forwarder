import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { beforeEach, expect, it, vi } from "vitest";
import { InternationalLocationSelector } from "@/components/InternationalLocationSelector";
import { fetchInternationalCityPage, type InternationalCity } from "@/lib/api";

vi.mock("@/lib/api", () => ({ fetchInternationalCityPage: vi.fn() }));

const point = (id: number, fallback = false): InternationalCity => ({
  id,
  name: `Place ${id}`,
  name_en: `Place ${id}`,
  un_locode: `US${String(id).padStart(3, "0")}`,
  city_type: "city",
  is_major_port: false,
  is_major_airport: false,
  name_fa_is_fallback: fallback,
});
const page = (id: number, offset = 0, hasMore = false) => ({
  items: [point(id)],
  offset,
  limit: 50,
  has_more: hasMore,
});

function Harness({ locale = "en" }: { locale?: "fa" | "en" }) {
  const [selected, setSelected] = useState<InternationalCity | null>(null);
  return (
    <InternationalLocationSelector
      countryId="1"
      locale={locale}
      side="origin"
      selected={selected}
      onChange={setSelected}
    />
  );
}

beforeEach(() => vi.resetAllMocks());

it("uses bounded pages and retains the selected identity across page and query changes", async () => {
  vi.mocked(fetchInternationalCityPage)
    .mockResolvedValueOnce(page(1, 0, true))
    .mockResolvedValueOnce(page(51, 50))
    .mockResolvedValueOnce(page(99));
  render(<Harness />);
  await screen.findByRole("option", { name: /Place 1/ });
  fireEvent.change(screen.getByLabelText("Select origin location"), {
    target: { value: "1" },
  });
  fireEvent.click(screen.getByRole("button", { name: "More locations" }));
  await screen.findByRole("option", { name: /Place 51/ });
  expect(fetchInternationalCityPage).toHaveBeenLastCalledWith(1, "", 50);
  expect(screen.getByLabelText("Select origin location")).toHaveValue("1");
  fireEvent.change(screen.getByLabelText("Search origin location"), {
    target: { value: "US099" },
  });
  await screen.findByRole("option", { name: /Place 99/ });
  expect(fetchInternationalCityPage).toHaveBeenLastCalledWith(1, "US099", 0);
  expect(screen.getByLabelText("Select origin location")).toHaveValue("1");
});

it("distinguishes lookup failure from an empty search and supports retry", async () => {
  vi.mocked(fetchInternationalCityPage)
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce({ ...page(1), items: [] });
  render(<Harness />);
  await screen.findByRole("alert");
  expect(screen.queryByText("No locations match this search.")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByText("No locations match this search.");
});

it("discards a response from a prior country and marks fallback Persian labels honestly", async () => {
  let finish!: (value: ReturnType<typeof page>) => void;
  vi.mocked(fetchInternationalCityPage)
    .mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }))
    .mockResolvedValueOnce({ ...page(2), items: [point(2, true)] });
  const props = { locale: "fa" as const, side: "origin" as const, selected: null, onChange: vi.fn() };
  const view = render(<InternationalLocationSelector key="1" countryId="1" {...props} />);
  await waitFor(() => expect(fetchInternationalCityPage).toHaveBeenCalled());
  view.rerender(<InternationalLocationSelector key="2" countryId="2" {...props} />);
  expect(await screen.findByRole("option", { name: /Place 2.*نام منبع/ })).toBeInTheDocument();
  finish(page(1));
  await waitFor(() => expect(screen.queryByRole("option", { name: /Place 1/ })).not.toBeInTheDocument());
});
