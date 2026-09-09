import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../gameApi";
import VillageView from "./VillageView";

const village = {
  places: [
    {
      id: "bar",
      name_ru: "бар",
      name_de: "Bar",
      kind: "npcs" as const,
      art: "bar",
      hotspot: { x: 0.1, y: 0.5, w: 0.2, h: 0.25 },
    },
  ],
};

function renderVillage() {
  return render(
    <MemoryRouter initialEntries={["/dorf"]}>
      <Routes>
        <Route path="/dorf" element={<VillageView />} />
        <Route path="/dorf/:placeId" element={<p>Ort geöffnet</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("VillageView", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("zeigt die Karte", async () => {
    vi.spyOn(api, "getVillage").mockResolvedValue(village);
    renderVillage();
    expect(await screen.findByAltText("Das Dorf")).toBeInTheDocument();
  });

  it("setzt die Klickfläche auf die Anteile aus dem Inhalt", async () => {
    vi.spyOn(api, "getVillage").mockResolvedValue(village);
    renderVillage();
    const button = await screen.findByRole("button", { name: /бар/ });
    expect(button.style.left).toBe("10%");
    expect(button.style.top).toBe("50%");
    expect(button.style.width).toBe("20%");
    expect(button.style.height).toBe("25%");
    // Prozentangaben beziehen sich auf den naechsten positionierten
    // Vorfahren. Ohne "relative" am Kartenrahmen wuerden sie sich auf ein
    // ganz anderes Element beziehen und die Flaechen saessen woanders,
    // obwohl die Inline-Werte oben unveraendert blieben.
    expect(screen.getByTestId("village-map")).toHaveClass("relative");
  });

  it("öffnet den Ort beim Klick", async () => {
    vi.spyOn(api, "getVillage").mockResolvedValue(village);
    renderVillage();
    fireEvent.click(await screen.findByRole("button", { name: /бар/ }));
    expect(await screen.findByText("Ort geöffnet")).toBeInTheDocument();
  });

  it("meldet einen Ladefehler statt leer zu bleiben", async () => {
    vi.spyOn(api, "getVillage").mockRejectedValue(new Error("kaputt"));
    renderVillage();
    expect(await screen.findByText(/konnte nicht geladen/)).toBeInTheDocument();
  });

  it("bleibt bedienbar, wenn die Karte fehlt", async () => {
    vi.spyOn(api, "getVillage").mockResolvedValue(village);
    renderVillage();
    const map = await screen.findByAltText("Das Dorf");
    fireEvent.error(map);
    // Ohne Bild braucht die Klickfläche einen sichtbaren Namen, sonst ist der
    // Ort nicht mehr zu finden — Abschnitt 6 der Spec. "sr-only" liefert
    // ebenfalls einen zugänglichen Namen, ist aber nicht sichtbar — darum
    // muss die Beschriftung selbst geprüft werden, nicht nur der Knopf.
    const button = await screen.findByRole("button", { name: /бар/ });
    expect(button).toBeVisible();
    const label = within(button).getByText("бар");
    expect(label).toBeVisible();
    expect(label).not.toHaveClass("sr-only");
    expect(screen.getByTestId("village-map")).toHaveClass("bg-slate-200");
  });
});

describe("VillageView — Namensliste", () => {
  it("verzichtet auf die Liste, solange die Karte da ist", async () => {
    // Die Gebaeude tragen ihre Schilder im Bild; die Liste waere dieselbe
    // Angabe ein zweites Mal.
    vi.spyOn(api, "getVillage").mockResolvedValue(village);
    renderVillage();
    await screen.findByAltText("Das Dorf");
    expect(screen.queryByRole("list")).toBeNull();
  });

  it("zeigt die Liste, wenn das Kartenbild fehlt", async () => {
    vi.spyOn(api, "getVillage").mockResolvedValue(village);
    renderVillage();
    fireEvent.error(await screen.findByAltText("Das Dorf"));
    expect(screen.getByRole("list")).toBeInTheDocument();
  });
});
