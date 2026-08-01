import { useEffect, useState } from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Link, MemoryRouter, Route, Routes, useLocation, useNavigate } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import RouteScrollManager from "@/components/RouteScrollManager";

function NavigationFixture({ asyncHash = false }: { asyncHash?: boolean | "auto" }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [hashReady, setHashReady] = useState(!asyncHash);

  useEffect(() => {
    if (asyncHash !== "auto") return;
    const timer = window.setTimeout(() => setHashReady(true), 75);
    return () => window.clearTimeout(timer);
  }, [asyncHash]);

  return (
    <>
      <RouteScrollManager />
      <nav>
        <Link to="/short">link short</Link>
        <Link to="/detail">detail</Link>
        <Link to="/long?filter=open">query</Link>
        <Link to="/short" state={{ preserveScroll: true }}>preserve</Link>
        <Link to="/long#cargo">hash</Link>
      </nav>
      <button onClick={() => navigate("/short")}>navigate short</button>
      <button onClick={() => navigate("/short", { replace: true })}>replace short</button>
      <button onClick={() => navigate(-1)}>back</button>
      <button onClick={() => setDialogOpen(true)}>open dialog</button>
      {dialogOpen && <div role="dialog"><button onClick={() => setDialogOpen(false)}>close dialog</button></div>}
      {asyncHash && !hashReady && <button onClick={() => setHashReady(true)}>render hash target</button>}
      {hashReady && <h2 id="cargo">Cargo</h2>}
      <main><h1>{location.pathname}{location.search}{location.hash}</h1></main>
    </>
  );
}

function renderFixture(initialEntries = ["/long"], initialIndex?: number, asyncHash: boolean | "auto" = false) {
  return render(
    <MemoryRouter initialEntries={initialEntries} initialIndex={initialIndex}>
      <Routes>
        <Route path="*" element={<NavigationFixture asyncHash={asyncHash} />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("RouteScrollManager", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    Object.defineProperty(window, "scrollY", { configurable: true, value: 900 });
  });

  it("resets a long page to a short page through Link", async () => {
    renderFixture();
    await userEvent.click(screen.getByRole("link", { name: "link short" }));
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, left: 0, behavior: "auto" });
  });

  it("resets through navigate() and replace navigation", async () => {
    const first = renderFixture();
    await userEvent.click(screen.getByRole("button", { name: "navigate short" }));
    expect(window.scrollTo).toHaveBeenCalledTimes(1);

    first.unmount();
    vi.mocked(window.scrollTo).mockClear();
    renderFixture();
    await userEvent.click(screen.getByRole("button", { name: "replace short" }));
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, left: 0, behavior: "auto" });
  });

  it("leaves browser POP restoration alone for list-detail-Back", async () => {
    renderFixture(["/long", "/detail"], 1);
    await userEvent.click(screen.getByRole("button", { name: "back" }));
    await waitFor(() => expect(screen.getByRole("heading", { level: 1 }).textContent).toContain("/long"));
    expect(window.scrollTo).not.toHaveBeenCalled();
  });

  it("preserves same-path query changes and explicit preserveScroll", async () => {
    renderFixture();
    await userEvent.click(screen.getByRole("link", { name: "query" }));
    expect(window.scrollTo).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("link", { name: "preserve" }));
    expect(window.scrollTo).not.toHaveBeenCalled();
  });

  it("positions a hash target below the sticky header", async () => {
    renderFixture();
    const target = screen.getByRole("heading", { level: 2 });
    vi.spyOn(target, "getBoundingClientRect").mockReturnValue({ top: 500 } as DOMRect);
    await userEvent.click(screen.getByRole("link", { name: "hash" }));
    await waitFor(() => expect(window.scrollTo).toHaveBeenCalledWith({ top: 1400, left: 0, behavior: "auto" }));
  });

  it("finds a late hash target but stops retrying after user interaction", async () => {
    renderFixture(["/short"], undefined, true);
    await userEvent.click(screen.getByRole("link", { name: "hash" }));
    fireEvent.wheel(window);
    await userEvent.click(screen.getByRole("button", { name: "render hash target" }));
    await act(() => new Promise((resolve) => setTimeout(resolve, 350)));
    expect(window.scrollTo).not.toHaveBeenCalled();
  });

  it("positions a hash target that appears during the bounded async window", async () => {
    renderFixture(["/short"], undefined, "auto");
    await userEvent.click(screen.getByRole("link", { name: "hash" }));
    const target = await screen.findByRole("heading", { level: 2 });
    vi.spyOn(target, "getBoundingClientRect").mockReturnValue({ top: 250 } as DOMRect);
    await waitFor(() => expect(window.scrollTo).toHaveBeenCalledWith({ top: 1150, left: 0, behavior: "auto" }));
  });

  it("supports optional main-heading focus without focusing body", async () => {
    function FocusFixture() {
      const navigate = useNavigate();
      return <><RouteScrollManager /><button onClick={() => navigate("/short", { state: { focusMainContent: true } })}>focus route</button><main><h1>Destination</h1></main></>;
    }
    render(<MemoryRouter initialEntries={["/long"]}><Routes><Route path="*" element={<FocusFixture />} /></Routes></MemoryRouter>);
    await userEvent.click(screen.getByRole("button", { name: "focus route" }));
    expect(document.activeElement).toBe(screen.getByRole("heading", { level: 1 }));
    expect(document.activeElement).not.toBe(document.body);
    expect(document.activeElement?.getAttribute("tabindex")).toBe("-1");
  });

  it("does not reset the page when a dialog opens and closes", async () => {
    renderFixture();
    await userEvent.click(screen.getByRole("button", { name: "open dialog" }));
    await userEvent.click(screen.getByRole("button", { name: "close dialog" }));
    expect(window.scrollTo).not.toHaveBeenCalled();
  });

  it.each([360, 390, 412])("uses the same bounded reset at %ipx mobile width", async (width) => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: width });
    renderFixture();
    await userEvent.click(screen.getByRole("link", { name: "link short" }));
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, left: 0, behavior: "auto" });
    expect(document.documentElement.style.overflowX).toBe("");
  });
});
