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
  const { businessLabel } = useI18n();
  return <>{values.map((value) => <p key={value} data-testid={value}>{businessLabel(value)}</p>)}<p data-testid="unknown">{businessLabel("INTERNAL_FUTURE_CODE")}</p></>;
}

describe("governed shipment-detail business labels", () => {
  it("maps persisted names and statuses without leaking unknown technical codes", () => {
    window.localStorage.setItem("forwarder.language", "fa");
    render(<I18nProvider><Labels /></I18nProvider>);
    for (const value of values) expect(screen.getByTestId(value)).not.toHaveTextContent(value);
    expect(screen.getByTestId("unknown")).toHaveTextContent("عنوان ثبت‌شده");
    expect(screen.getByTestId("unknown")).not.toHaveTextContent("INTERNAL_FUTURE_CODE");
  });
});
