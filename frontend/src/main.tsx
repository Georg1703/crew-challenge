import "@fontsource-variable/nunito-sans/wght.css";
import "./styles/tokens.css";
import "./styles/global.css";
import "./i18n";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./app/App";
import { captureInstallPrompt } from "./pwa";
import { applyTheme, storedTheme } from "./shared/lib/theme";

// Before React renders: Chrome fires beforeinstallprompt only once, early; the theme avoids a
// flash of the wrong colors.
captureInstallPrompt();
applyTheme(storedTheme());

const root = document.getElementById("root");
if (!root) throw new Error("Missing #root element in index.html");

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
