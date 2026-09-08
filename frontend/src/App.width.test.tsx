import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import * as api from "./courseApi";
import * as gameApi from "./gameApi";
import App from "./App";

// App bringt selbst keinen Router mit (den setzt main.tsx) — ein
// MemoryRouter im Test reicht, kein window.history.pushState noetig.
function renderAt(path: string) {
  vi.spyOn(api, "getCourse").mockResolvedValue({ stages: [] });
  vi.spyOn(gameApi, "getVillage").mockResolvedValue({ places: [] });
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe("Seitenbreite", () => {
  it("hält Kurs und Profil schmal", () => {
    renderAt("/kurs");
    expect(screen.getByRole("main")).toHaveClass("max-w-3xl");
  });

  it("gibt dem Dorf die volle Breite", () => {
    renderAt("/dorf");
    expect(screen.getByRole("main")).not.toHaveClass("max-w-3xl");
  });
});

describe("Kopfzeile im Dorf", () => {
  it("bleibt im Dorf sichtbar, nur breiter", () => {
    renderAt("/dorf");
    // Nutzeranforderung: die Kopfzeile mit Logo, Navigation und
    // Ton-Schalter darf im Dorf nicht verschwinden — sie waechst nur mit.
    expect(screen.getByText("Speaker")).toBeVisible();
    expect(screen.getByRole("navigation")).toBeVisible();
    expect(screen.getByRole("link", { name: "Dorf" })).toBeVisible();
    expect(screen.getByRole("switch")).toBeVisible();
  });
});
