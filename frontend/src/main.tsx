import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import AdminPanel from "./AdminPanel";
import App from "./App";
import EventsDock from "./EventsDock";
import "./styles.css";
import "./community.css";
import "./events-drawer.css";

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
        <EventsDock />
        <AdminPanel />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
