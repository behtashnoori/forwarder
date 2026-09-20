import { useState } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import OperationalEventLocationSelector, {
  type OperationalEventLocation,
} from "@/components/OperationalEventLocationSelector";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  fetchTrackingLogisticsPoints: vi.fn(),
  fetchTrackingLocations: vi.fn(),
}));

function Harness() {
  const [value, setValue] = useState<OperationalEventLocation>({
    kind: "manual",
    locationText: "",
  });
  return <>
    <OperationalEventLocationSelector value={value} onChange={setValue} />
    <output>{JSON.stringify(value)}</output>
  </>;
}

describe("operational event location selector", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.fetchTrackingLogisticsPoints).mockResolvedValue({
      items: [{
        public_id: "private-1",
        fa_name: "انبار مرکزی",
        en_name: "Central warehouse",
        immutable_code: "PRIVATE-1",
        selector_kind: "organization_private",
        type: { code: "WAREHOUSE", label: "انبار" },
        country: { code: "IR", label: "ایران" },
        province: "تهران",
        city: "تهران",
      }],
      limit: 20,
      offset: 0,
      has_more: false,
    });
    vi.mocked(api.fetchTrackingLocations).mockResolvedValue({
      items: [{
        id: 8,
        name_fa: "بندر مرجع",
        name_en: "Reference port",
        country_code: "IR",
        location_type: "seaport",
        aliases: [],
        is_active: true,
      }],
    });
  });

  it("keeps global references separate and returns exact private identity", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const selector = screen.getByLabelText("انتخاب مکان رخداد");
    await waitFor(() => expect(selector).not.toBeDisabled());
    expect(selector).toHaveTextContent("انبار مرکزی / Central warehouse — نقطه خصوصی سازمان");
    expect(selector).toHaveTextContent("بندر مرجع / Reference port — مکان مرجع");

    await user.selectOptions(selector, "reference:8");
    expect(screen.getByRole("status")).toHaveTextContent('"kind":"reference","id":8');
    await user.selectOptions(selector, "private:private-1");
    expect(screen.getByRole("status")).toHaveTextContent(
      '"kind":"private","publicId":"private-1"',
    );
  });

  it("searches both bounded sources without accepting a tenant id", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await waitFor(() => expect(screen.getByLabelText("انتخاب مکان رخداد")).not.toBeDisabled());
    await user.type(screen.getByLabelText("جست‌وجوی مکان رخداد"), "مرکزی");
    await waitFor(() => {
      expect(api.fetchTrackingLogisticsPoints).toHaveBeenLastCalledWith("مرکزی");
      expect(api.fetchTrackingLocations).toHaveBeenLastCalledWith("مرکزی");
    });
  });
});
