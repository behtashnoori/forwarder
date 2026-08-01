import { useEffect, useLayoutEffect, useRef } from "react";
import { useLocation, useNavigationType } from "react-router";

export interface RouteNavigationState {
  preserveScroll?: boolean;
  focusMainContent?: boolean;
  modal?: boolean;
  backgroundLocation?: unknown;
}

const HASH_RETRY_DELAYS_MS = [0, 50, 150, 300];
const USER_SCROLL_KEYS = new Set([
  "ArrowDown",
  "ArrowUp",
  "End",
  "Home",
  "PageDown",
  "PageUp",
  " ",
]);

function stickyHeaderOffset(): number {
  const stickyHeader = document.querySelector<HTMLElement>(
    'header.sticky, [data-sticky-header="true"]',
  );
  return stickyHeader?.getBoundingClientRect().height ?? 0;
}

function findHashTarget(hash: string): HTMLElement | null {
  if (!hash) return null;
  const id = decodeURIComponent(hash.slice(1));
  return document.getElementById(id) ?? document.getElementsByName(id).item(0);
}

function focusRouteContent(): void {
  const target = document.querySelector<HTMLElement>(
    '[data-route-focus="true"], main h1, main [role="heading"][aria-level="1"]',
  );
  if (!target) return;
  if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
  target.focus({ preventScroll: true });
}

/**
 * Central route-level scroll policy. Browser-native POP restoration remains enabled;
 * this component only handles new locations and explicit hash destinations.
 */
export default function RouteScrollManager() {
  const location = useLocation();
  const navigationType = useNavigationType();
  const previousPathname = useRef(location.pathname);

  useLayoutEffect(() => {
    const previous = previousPathname.current;
    previousPathname.current = location.pathname;

    const state = (location.state ?? {}) as RouteNavigationState;
    const isModalNavigation = state.modal === true || state.backgroundLocation != null;
    const changedPathname = previous !== location.pathname;

    if (
      navigationType !== "POP" &&
      changedPathname &&
      !location.hash &&
      !state.preserveScroll &&
      !isModalNavigation
    ) {
      window.scrollTo({ top: 0, left: 0, behavior: "auto" });
      if (state.focusMainContent) focusRouteContent();
    }
  }, [location.hash, location.key, location.pathname, location.state, navigationType]);

  useEffect(() => {
    if (!location.hash || navigationType === "POP") return;

    const state = (location.state ?? {}) as RouteNavigationState;
    if (state.preserveScroll || state.modal === true || state.backgroundLocation != null) return;

    let userInteracted = false;
    const markInteraction = () => {
      userInteracted = true;
    };
    const markKeyboardInteraction = (event: KeyboardEvent) => {
      if (USER_SCROLL_KEYS.has(event.key)) markInteraction();
    };

    window.addEventListener("wheel", markInteraction, { passive: true });
    window.addEventListener("touchmove", markInteraction, { passive: true });
    window.addEventListener("pointerdown", markInteraction, { passive: true });
    window.addEventListener("keydown", markKeyboardInteraction);

    const timers = HASH_RETRY_DELAYS_MS.map((delay) =>
      window.setTimeout(() => {
        if (userInteracted) return;
        const target = findHashTarget(location.hash);
        if (!target) return;
        const top = Math.max(0, window.scrollY + target.getBoundingClientRect().top - stickyHeaderOffset());
        window.scrollTo({ top, left: 0, behavior: "auto" });
      }, delay),
    );

    return () => {
      timers.forEach(window.clearTimeout);
      window.removeEventListener("wheel", markInteraction);
      window.removeEventListener("touchmove", markInteraction);
      window.removeEventListener("pointerdown", markInteraction);
      window.removeEventListener("keydown", markKeyboardInteraction);
    };
  }, [location.hash, location.key, location.state, navigationType]);

  return null;
}
