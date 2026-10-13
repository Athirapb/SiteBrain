import React from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/inter";
import "@mdi/font/css/materialdesignicons.min.css";
import "./styles.css";
import App from "./App";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
