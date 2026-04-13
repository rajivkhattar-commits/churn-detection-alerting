import "@fontsource-variable/nunito/wght.css";
import "@fontsource-variable/montserrat/wght.css";
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import {
  applyDocumentTheme,
  effectiveTheme,
  getStoredPreference,
} from "./theme";
import "./styles.css";

applyDocumentTheme(effectiveTheme(getStoredPreference()));

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
