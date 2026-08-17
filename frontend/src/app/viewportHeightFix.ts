/**
 * CSS `dvh` was supposed to track the real, current mobile viewport height
 * (toolbar collapsed/expanded) — see AppShell.module.css's and
 * tokens.css's own comments: two earlier rounds of dvh/vh patches on
 * `.app`/`body` already tried to fix exactly this ("either a black gap or
 * a .topbar that stops sticking"), and it resurfaced anyway (confirmed via
 * a screen recording: real page content ends cleanly, but the document
 * scrolls on for another 1-2 screens of empty space below it — `dvh`
 * itself is producing a value taller than the real viewport on that
 * device/browser). Rather than trust the CSS unit again, compute the
 * height in JS — window.innerHeight is always the actual current
 * viewport, no unit-support/timing gap to fall over — and expose it as a
 * CSS variable that body/.app read instead of `dvh`.
 */
function setRealViewportHeight(): void {
  const height = window.visualViewport?.height ?? window.innerHeight;
  document.documentElement.style.setProperty("--vh100", `${height}px`);
}

export function installViewportHeightFix(): void {
  setRealViewportHeight();
  window.addEventListener("resize", setRealViewportHeight);
  window.addEventListener("orientationchange", setRealViewportHeight);
  window.visualViewport?.addEventListener("resize", setRealViewportHeight);
}
