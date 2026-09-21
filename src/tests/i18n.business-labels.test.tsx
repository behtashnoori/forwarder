import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { I18nProvider, useI18n } from "@/i18n";

const values = [
  "operational_shipment.created",
  "route_plan.replanned",
  "operational_delay.created",
  "operational_delay.resolved",
  "operational_exception.created",
  "operational_exception.resolved",
  "PENDING",
  "COMPLETED",
  "reported",
  "verified",
  "corrected",
];

function Labels() {
  const { businessLabel, transportLabel } = useI18n();
  return <>{values.map((value) => <p key={value} data-testid={value}>{businessLabel(value)}</p>)}<p data-testid="unknown">{businessLabel("INTERNAL_FUTURE_CODE")}</p><p data-testid="road-mode">{transportLabel("road")}</p><p data-testid="rail-catalog">{transportLabel("Rail Transport")}</p><p data-testid="land-catalog">{transportLabel("Land Transport")}</p><p data-testid="air-catalog">{transportLabel("Air Freight")}</p><p data-testid="sea-catalog">{transportLabel("Sea Freight")}</p><p data-testid="combined-catalog">{transportLabel("Combined Transport")}</p></>;
}

describe("governed shipment-detail business labels", () => {
  it("maps persisted names and statuses without leaking unknown technical codes", () => {
    window.localStorage.setItem("forwarder.language", "fa");
    render(<I18nProvider><Labels /></I18nProvider>);
    for (const value of values) expect(screen.getByTestId(value)).not.toHaveTextContent(value);
    expect(screen.getByTestId("unknown")).toHaveTextContent("عنوان ثبت‌شده");
    expect(screen.getByTestId("unknown")).not.toHaveTextContent("INTERNAL_FUTURE_CODE");
    expect(screen.getByTestId("road-mode")).toHaveTextContent("جاده‌ای");
    expect(screen.getByTestId("rail-catalog")).toHaveTextContent("حمل ریلی");
    expect(screen.getByTestId("land-catalog")).toHaveTextContent("حمل زمینی");
    expect(screen.getByTestId("air-catalog")).toHaveTextContent("حمل هوایی");
    expect(screen.getByTestId("sea-catalog")).toHaveTextContent("حمل دریایی");
    expect(screen.getByTestId("combined-catalog")).toHaveTextContent("حمل ترکیبی");
    expect(screen.queryByText("road")).not.toBeInTheDocument();
  });
});
