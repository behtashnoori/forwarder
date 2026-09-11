import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it } from "vitest";
import ProtectedRoute from "../../components/ProtectedRoute";

describe("ProtectedRoute", () => {
  beforeEach(() => localStorage.clear());

  it("allows an authorized operational user", () => {
    localStorage.setItem("expert_user", JSON.stringify({ role: "business_expert" }));
    localStorage.setItem("expert_token", "test-token");
    render(<MemoryRouter initialEntries={["/operations/shipments"]}><Routes><Route path="/operations/shipments" element={<ProtectedRoute><p>authorized operations</p></ProtectedRoute>} /></Routes></MemoryRouter>);
    expect(screen.getByText("authorized operations")).toBeInTheDocument();
  });

  it("redirects an unauthenticated request to the public route", () => {
    render(<MemoryRouter initialEntries={["/operations/shipments"]}><Routes><Route path="/" element={<p>public index</p>} /><Route path="/operations/shipments" element={<ProtectedRoute><p>authorized operations</p></ProtectedRoute>} /></Routes></MemoryRouter>);
    expect(screen.getByText("public index")).toBeInTheDocument();
    expect(screen.queryByText("authorized operations")).not.toBeInTheDocument();
  });
});
