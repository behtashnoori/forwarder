import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it } from "vitest";
import ApplicationNavigation from "@/components/ApplicationNavigation";

describe("shared application navigation", () => {
  beforeEach(() => { sessionStorage.clear(); localStorage.setItem("expert_user", JSON.stringify({authority:"EXPERT"})); });
  it("falls back to the canonical authenticated home", async () => { render(<MemoryRouter initialEntries={["/operations/shipments"]}><ApplicationNavigation/><Routes><Route path="/expert" element={<p>expert home</p>}/></Routes></MemoryRouter>); await userEvent.click(screen.getByRole("button",{name:"بازگشت"})); expect(screen.getByText("expert home")).toBeInTheDocument(); });
  it("uses the canonical admin home", async () => { localStorage.setItem("expert_user", JSON.stringify({authority:"ORGANIZATION_ADMIN"})); render(<MemoryRouter initialEntries={["/anything"]}><ApplicationNavigation/><Routes><Route path="/admin" element={<p>admin home</p>}/></Routes></MemoryRouter>); await userEvent.click(screen.getByRole("button",{name:"خانه"})); expect(screen.getByText("admin home")).toBeInTheDocument(); });
});
