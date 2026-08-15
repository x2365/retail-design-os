import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
// Self-hosted variable fonts (not a Google Fonts CDN link) — full weight
// axis in one file each, cyrillic subset included. See tokens.css for the
// --font-sans/--font-heading tokens that reference them.
import "@fontsource-variable/geologica/wght.css";
import "@fontsource-variable/unbounded/wght.css";
import "./styles/tokens.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
