import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CanonicalLocationPicker from "@/components/CanonicalLocationPicker";
import {
  createExpertLocation, fetchCanonicalAdmin1, fetchCanonicalCities, fetchCanonicalCountries,
  listLogisticsPoints, listLogisticsPointTypes,
} from "@/lib/api";

vi.mock("@/lib/api", () => ({
  createExpertLocation: vi.fn(), fetchCanonicalAdmin1: vi.fn(), fetchCanonicalCities: vi.fn(),
  fetchCanonicalCountries: vi.fn(), listLogisticsPoints: vi.fn(), listLogisticsPointTypes: vi.fn(),
}));

const point = {
  public_id: "point-1", immutable_code: "LOC-1", fa_name: "انبار مشتری", en_name: null,
  is_active: true, version: 1, point_type: null, governance_state: "PENDING_REVIEW" as const,
  country: { code: "IR", fa_name: "ایران", en_name: "Iran" },
  province: { code: "04", name_fa: "اصفهان" }, city: { code: "418863", name_fa: "اصفهان" },
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(fetchCanonicalCountries).mockResolvedValue({ items: [{ id: 1, code: "IR", name_fa: "ایران", name_en: "Iran" }] });
  vi.mocked(listLogisticsPointTypes).mockResolvedValue({ items: [] });
  vi.mocked(fetchCanonicalAdmin1).mockResolvedValue({ items: [{ source_id: 10, geoname_id: 418862, code: "04", name_fa: "اصفهان", name_en: "Isfahan" }] });
  vi.mocked(fetchCanonicalCities).mockResolvedValue({ items: [{ source_id: 20, geoname_id: 418863, name_fa: "اصفهان", name_en: "Isfahan", latitude: "32.65", longitude: "51.67" }] });
  vi.mocked(listLogisticsPoints).mockResolvedValue({ items: [point], page: 1, pages: 1, total: 1 });
  vi.mocked(createExpertLocation).mockResolvedValue({ item: point });
});

async function chooseCity(onChange: ReturnType<typeof vi.fn>) {
  render(<CanonicalLocationPicker label="مبدأ" value={null} onChange={onChange} />);
  await screen.findByRole("option", { name: "ایران · IR" });
  fireEvent.change(screen.getByLabelText("مبدأ کشور"), { target: { value: "1" } });
  await screen.findByRole("option", { name: "اصفهان" });
  fireEvent.change(screen.getByLabelText("مبدأ استان"), { target: { value: "418862" } });
  await screen.findByRole("option", { name: "اصفهان / Isfahan" });
  fireEvent.change(screen.getByLabelText("مبدأ شهر"), { target: { value: "418863" } });
}

describe("canonical location picker", () => {
  it("walks the governed hierarchy and emits structured city and organization identities", async () => {
    const onChange = vi.fn();
    await chooseCity(onChange);
    await waitFor(() => expect(onChange).toHaveBeenLastCalledWith({ country_id: 1, source_type: "city", source_id: 20 }));
    await screen.findByRole("option", { name: "انبار مشتری · در انتظار بررسی" });
    fireEvent.change(screen.getByLabelText("مبدأ مکان سازمان"), { target: { value: "point-1" } });
    expect(onChange).toHaveBeenLastCalledWith({ country_id: 1, source_type: "logistics_point", source_id: "point-1" });
  });

  it("creates a minimally named expert location and makes it immediately usable", async () => {
    const onChange = vi.fn();
    await chooseCity(onChange);
    fireEvent.click(await screen.findByRole("button", { name: "افزودن مکان تازه" }));
    fireEvent.change(screen.getByLabelText("نام مکان"), { target: { value: "انبار مشتری" } });
    fireEvent.click(screen.getByRole("button", { name: "ایجاد و استفاده فوری" }));
    await waitFor(() => expect(createExpertLocation).toHaveBeenCalledWith({
      name: "انبار مشتری", city_geoname_id: 418863, point_type_public_id: null,
      address: null, description: null,
    }));
    expect(onChange).toHaveBeenLastCalledWith({ country_id: 1, source_type: "logistics_point", source_id: "point-1" });
  });
});
