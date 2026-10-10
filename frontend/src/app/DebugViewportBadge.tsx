import { useEffect, useState } from "react";

/**
 * TEMPORARY diagnostic overlay — remove once the mobile phantom-scroll bug
 * (real content ends cleanly, document keeps scrolling for 1-2 more empty
 * screens below it, confirmed via two screen recordings on iPhone/Chrome)
 * is actually found. Every fix tried so far (dvh -> --vh100 JS viewport
 * height, translate="no", removeChild/insertBefore patch) still reproduces
 * identically, which means the guesses have been wrong — this puts the
 * real numbers (window.innerHeight vs. document/body/html scrollHeight,
 * and which single element's bottom edge is the outlier) directly on
 * screen instead of guessing blind from a video.
 */
export function DebugViewportBadge() {
  const [info, setInfo] = useState("");

  useEffect(() => {
    function update() {
      const html = document.documentElement;
      const body = document.body;
      const root = document.getElementById("root");
      let tallestSelector = "?";
      let tallestBottom = 0;
      document.querySelectorAll<HTMLElement>("body *").forEach((el) => {
        const rect = el.getBoundingClientRect();
        const bottom = rect.bottom + window.scrollY;
        if (bottom > tallestBottom && rect.height > 0) {
          tallestBottom = bottom;
          const cls =
            typeof el.className === "string" && el.className
              ? "." + el.className.split(" ")[0]
              : "";
          tallestSelector = el.tagName.toLowerCase() + cls;
        }
      });
      setInfo(
        `vh:${window.innerHeight} sy:${Math.round(window.scrollY)}\n` +
          `body:${body.scrollHeight} html:${html.scrollHeight} root:${root?.scrollHeight ?? "?"}\n` +
          `max-bottom:${Math.round(tallestBottom)} @ ${tallestSelector}`,
      );
    }
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    const id = setInterval(update, 1000);
    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
      clearInterval(id);
    };
  }, []);

  return (
    <div
      style={{
        position: "fixed",
        top: 4,
        left: 4,
        zIndex: 999999,
        background: "rgba(255, 0, 0, 0.85)",
        color: "#fff",
        fontSize: 10,
        fontFamily: "monospace",
        padding: "4px 6px",
        borderRadius: 4,
        whiteSpace: "pre",
        pointerEvents: "none",
        lineHeight: 1.3,
      }}
    >
      {info}
    </div>
  );
}
