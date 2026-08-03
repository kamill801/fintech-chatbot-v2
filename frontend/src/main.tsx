import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { LedgerProvider } from "./ledger-context";
import { BrowserRouter } from "./router";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <LedgerProvider>
        <App />
      </LedgerProvider>
    </BrowserRouter>
  </StrictMode>,
);

if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => {
    void navigator.serviceWorker.register("/sw.js");
  });
}
