import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import OperationsControlTower from "@/pages/OperationsControlTower";

vi.mock("@/control-tower/ControlTowerOperationalView", () => ({
  default: () => <main>منبع اختصاصی D1</main>,
}));

describe("existing Golden Control Tower route integration", () => {
  it("uses the dedicated D1 view for the existing no-props route", () => {
    render(<MemoryRouter><OperationsControlTower /></MemoryRouter>);
    expect(screen.getByText("منبع اختصاصی D1")).toBeVisible();
  });
});
