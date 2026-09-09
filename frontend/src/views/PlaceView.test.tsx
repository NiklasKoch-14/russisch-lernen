import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useParams, useSearchParams } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../gameApi";
import PlaceView from "./PlaceView";

const bar = {
  id: "bar",
  name_ru: "бар",
  name_de: "Bar",
  kind: "npcs" as const,
  art: "bar",
  npcs: [
    {
      id: "pjotr",
      name_ru: "Пётр",
      name_de: "Pjotr",
      about_de: "Sitzt jeden Abend am selben Platz.",
      art: "npc_pjotr",
      spot: { x: 0.03, y: 0.36, w: 0.14, h: 0.42 },
    },
  ],
};

const ohnePlatz = {
  id: "sasha",
  name_ru: "Са́ша",
  name_de: "Sascha",
  about_de: "Steht noch nirgends.",
  art: "npc_sasha",
  spot: null,
};

const started = {
  scene_id: "bar-01",
  seed: "bar-01:2026-09-08T10:00:00",
  title_de: "Der Mann am Tresen",
  intro_de: "Ein älterer Mann dreht sich zu dir um.",
  hint_unit: 15,
  npc: { id: "pjotr", name_ru: "Пётр", name_de: "Pjotr", art: "npc_pjotr" },
  turn_count: 2,
};

// Zeigt, welcher Seed tatsächlich in der Route ankommt — eine reine
// "Szene läuft"-Textzeile würde eine falsche oder fehlende Query
// unbemerkt durchlassen.
function SceneStub() {
  const [params] = useSearchParams();
  return <p>Szene läuft (seed={params.get("seed")})</p>;
}

// Zeigt die konkrete Einheiten-ID aus der Route — eine feste Textzeile wie
// "Einheit läuft" würde auch dann grün bleiben, wenn eine falsche ID
// eingesetzt wird.
function UnitStub() {
  const { unitId } = useParams();
  return <p>Einheit läuft (unitId={unitId})</p>;
}

function renderPlace(path = "/dorf/bar") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/dorf/:placeId" element={<PlaceView />} />
        <Route path="/dorf/:placeId/szene/:sceneId" element={<SceneStub />} />
        <Route path="/kurs/:unitId" element={<UnitStub />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("PlaceView", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("stellt die Leute im Raum auf, mit sichtbarem Namen", async () => {
    vi.spyOn(api, "getPlace").mockResolvedValue(bar);
    renderPlace();
    const button = await screen.findByRole("button", { name: /Пётр/ });
    // Der Name muss als sichtbarer Text im Knopf stehen, nicht nur als
    // zugänglicher Name — sonst könnte er auch von unsichtbarem Text
    // (z. B. sr-only) kommen, während auf dem Bildschirm nichts steht.
    const nameLabel = within(button).getByText("Пётр");
    expect(nameLabel).toBeVisible();
    expect(nameLabel).not.toHaveClass("sr-only");
    // Und zwar an seinem Platz im Raumbild, nicht in einer Liste darunter.
    expect(button.style.left).toBe("3%");
    expect(screen.getByTestId("place-stage")).toContainElement(button);
  });

  it("faellt auf die Liste zurueck, wenn es zum Raum kein Bild gibt", async () => {
    vi.spyOn(api, "getPlace").mockResolvedValue(bar);
    renderPlace();
    fireEvent.error(await screen.findByAltText("Bar"));
    const entry = await screen.findByRole("button", { name: /Пётр/ });
    expect(within(entry).getByText(/Sitzt jeden Abend/)).toBeVisible();
  });

  it("fuehrt Leute ohne Platz unter dem Bild auf", async () => {
    // Sonst waere jemand ohne `spot` gar nicht erreichbar.
    vi.spyOn(api, "getPlace").mockResolvedValue({
      ...bar,
      npcs: [...bar.npcs, ohnePlatz],
    });
    const start = vi.spyOn(api, "startScene").mockResolvedValue(started);
    renderPlace();
    const entry = await screen.findByRole("button", { name: /Са́ша/ });
    expect(screen.getByTestId("place-stage")).not.toContainElement(entry);
    fireEvent.click(entry);
    expect(start).toHaveBeenCalledWith("bar", "sasha");
  });

  it("startet beim Anklicken einer Person eine Szene mit ihrer ID", async () => {
    vi.spyOn(api, "getPlace").mockResolvedValue(bar);
    const start = vi.spyOn(api, "startScene").mockResolvedValue(started);
    renderPlace();
    fireEvent.click(await screen.findByRole("button", { name: /Пётр/ }));
    expect(start).toHaveBeenCalledWith("bar", "pjotr");
    expect(await screen.findByText(/Szene läuft/)).toBeInTheDocument();
  });

  it("hängt den von der Szene gelieferten Seed als Query an die Route", async () => {
    vi.spyOn(api, "getPlace").mockResolvedValue(bar);
    vi.spyOn(api, "startScene").mockResolvedValue(started);
    renderPlace();
    fireEvent.click(await screen.findByRole("button", { name: /Пётр/ }));
    // Ohne korrekten Seed in der URL könnte die Szenenansicht (Aufgabe 10)
    // später eine andere Zufallsvariante laden als die, die der Server
    // schon vorbereitet hat.
    expect(
      await screen.findByText(`Szene läuft (seed=${started.seed})`),
    ).toBeInTheDocument();
  });

  it("startet beim Laden direkt eine Szene, wenn der Ort ein Laden ist", async () => {
    vi.spyOn(api, "getPlace").mockResolvedValue({ ...bar, kind: "shopping", npcs: [] });
    const start = vi.spyOn(api, "startScene").mockResolvedValue(started);
    renderPlace();
    fireEvent.click(await screen.findByRole("button", { name: /Einkaufen/ }));
    expect(start).toHaveBeenCalledWith("bar", undefined);
    // Ein Laden zeigt keine Personenauswahl — sonst wäre es kein
    // direkter Einstieg, wie es für "shopping" gefordert ist.
    expect(screen.queryByRole("button", { name: /Пётр/ })).not.toBeInTheDocument();
  });

  it("führt beim Sprachkurs sichtbar in die nächste offene Einheit", async () => {
    vi.spyOn(api, "getPlace").mockResolvedValue({
      ...bar,
      kind: "course",
      npcs: [],
      next_unit_id: 7,
    });
    renderPlace();
    const button = await screen.findByRole("button", { name: /Einheit 7/ });
    expect(within(button).getByText(/Einheit 7/)).toBeVisible();
    fireEvent.click(button);
    // Es muss genau die gemeldete nächste Einheit (7) geöffnet werden —
    // nicht irgendeine Kursroute.
    expect(await screen.findByText("Einheit läuft (unitId=7)")).toBeInTheDocument();
  });

  it("bietet keine begehbare Einheit an, wenn der Kurs schon fertig ist", async () => {
    vi.spyOn(api, "getPlace").mockResolvedValue({
      ...bar,
      kind: "course",
      npcs: [],
      next_unit_id: null,
    });
    const start = vi.spyOn(api, "startScene");
    renderPlace();
    const button = await screen.findByRole("button", { name: /geschafft/ });
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(start).not.toHaveBeenCalled();
    // Bei einem Klick auf den deaktivierten Knopf darf keine Kurs- oder
    // Szenenroute geöffnet werden.
    expect(screen.queryByText(/Einheit läuft/)).not.toBeInTheDocument();
  });
});

describe("PlaceView — einheitlicher Zuschnitt", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("zeigt den Laden in derselben Buehne wie die Bar", async () => {
    // Vorher stand das Bild dort in einer anderen Huelle und war schmaler.
    vi.spyOn(api, "getPlace").mockResolvedValue({ ...bar, kind: "shopping", npcs: [] });
    renderPlace();
    await screen.findByRole("button", { name: /Einkaufen/ });
    expect(screen.getByTestId("place-stage")).toBeInTheDocument();
  });

  it("stellt Weiterweg und Rueckweg als gleichrangige Knoepfe nebeneinander", async () => {
    // Vorher klebte ein unterstrichener Link direkt am Knopf.
    vi.spyOn(api, "getPlace").mockResolvedValue({ ...bar, kind: "shopping", npcs: [] });
    renderPlace();
    const actions = await screen.findByTestId("place-actions");
    const back = within(actions).getByRole("button", { name: /Zurück ins Dorf/ });
    expect(within(actions).getByRole("button", { name: /Einkaufen/ })).toBeVisible();
    expect(back.className).not.toMatch(/underline/);
  });
});
