import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../courseApi";
import type { TodayPlan, TodayStep } from "../courseTypes";
import TodayView from "./TodayView";

const review: TodayStep = {
  kind: "review",
  status: "next",
  minutes: 5,
  title_de: "Auffrischen",
  link: "/wiederholen",
};
const unit: TodayStep = {
  kind: "unit",
  status: "later",
  minutes: 11,
  unit_id: 46,
  title_de: "Wo ist die Apotheke?",
  detail_de: "Du suchst in einer fremden Stadt eine Apotheke.",
  link: "/kurs/46",
};
const listening: TodayStep = {
  kind: "listening",
  status: "later",
  minutes: 3,
  title_de: "Nach dem Weg gefragt",
  detail_de: null,
  known: false,
  link: "/hoeren?gespraech=21",
};

const plan: TodayPlan = {
  greeting: "normal",
  steps: [review, unit, listening],
  unit_skipped: null,
  next_unit_id: 46,
  finished: false,
  week_days: 0,
  offer_screening: false,
};

function renderWith(overrides: Partial<TodayPlan>) {
  vi.spyOn(api, "getToday").mockResolvedValue({ ...plan, ...overrides });
  return render(
    <MemoryRouter>
      <TodayView />
    </MemoryRouter>,
  );
}

describe("TodayView", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("zeigt den Tag als Checkliste mit Stand", async () => {
    renderWith({});
    const list = await screen.findByRole("list", { name: "Heute dran" });
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(items[0]).toHaveTextContent("Auffrischen");
    expect(items[0]).toHaveTextContent("als Nächstes");
    expect(items[0]).toHaveAttribute("aria-current", "step");
    expect(items[1]).toHaveTextContent("Einheit 46 · Wo ist die Apotheke?");
    expect(items[1]).toHaveTextContent("Du suchst in einer fremden Stadt eine Apotheke.");
    expect(items[1]).toHaveTextContent("danach");
    expect(items[1]).not.toHaveAttribute("aria-current");
    expect(items[2]).toHaveTextContent("Gespräch hören · Nach dem Weg gefragt");
  });

  it("nennt die Dauer statt einer Menge", async () => {
    renderWith({});
    expect(await screen.findByText("Etwa 19 Minuten.")).toBeInTheDocument();
    expect(screen.queryByText(/fällig/)).not.toBeInTheDocument();
  });

  it("hat genau einen Hauptknopf, der zum nächsten Schritt führt", async () => {
    renderWith({});
    const primary = await screen.findByRole("link", { name: "Los: Auffrischen · ca. 5 Min." });
    expect(primary).toHaveAttribute("href", "/wiederholen");
  });

  it("sagt „Weiter“, sobald etwas erledigt ist", async () => {
    renderWith({
      steps: [{ ...review, status: "done" }, { ...unit, status: "next" }, listening],
    });
    const primary = await screen.findByRole("link", { name: "Weiter: Einheit 46 · ca. 11 Min." });
    expect(primary).toHaveAttribute("href", "/kurs/46");
    expect(screen.getByText("Etwa 14 Minuten.")).toBeInTheDocument();
  });

  it("bietet die kurze Variante an, solange das Auffrischen offen ist", async () => {
    renderWith({});
    const short = await screen.findByRole("link", { name: "Nur 5 Minuten heute" });
    expect(short).toHaveAttribute("href", "/wiederholen");
  });

  it("bietet die kurze Variante nicht an, wenn nach dem Auffrischen nichts kommt", async () => {
    renderWith({ steps: [review] });
    await screen.findByRole("link", { name: /Los: Auffrischen/ });
    expect(screen.queryByRole("link", { name: "Nur 5 Minuten heute" })).not.toBeInTheDocument();
  });

  it("begrüßt nach einer Pause ohne Vorwurf und lässt die Einheit weg", async () => {
    renderWith({ greeting: "welcome_back", steps: [review, listening], unit_skipped: "pause" });
    expect(
      await screen.findByRole("heading", { name: "Schön, dass du wieder da bist." }),
    ).toBeInTheDocument();
    expect(screen.getByText("Heute keine neue Einheit — wir frischen erst auf.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Noch eine Einheit" })).toHaveAttribute(
      "href",
      "/kurs/46",
    );
  });

  it("erklärt, warum bei hohem Rückstand keine Einheit kommt", async () => {
    renderWith({ steps: [review], unit_skipped: "backlog" });
    expect(
      await screen.findByText(
        "Heute keine neue Einheit — erst das Wiederholen, sonst wird der Stapel morgen zu hoch.",
      ),
    ).toBeInTheDocument();
  });

  it("sagt, wenn alle Einheiten geschafft sind", async () => {
    renderWith({ steps: [review], unit_skipped: "all_done", next_unit_id: null });
    expect(
      await screen.findByText("Alle vorhandenen Einheiten sind geschafft — neue kommen bald."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Noch eine Einheit" })).not.toBeInTheDocument();
  });

  it("schließt den Tag ab, wenn alles erledigt ist", async () => {
    renderWith({
      steps: [
        { ...review, status: "done" },
        { ...unit, status: "done" },
        { ...listening, status: "done" },
      ],
      finished: true,
      next_unit_id: 47,
      week_days: 3,
    });
    expect(await screen.findByText("Fertig für heute.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /^(Los|Weiter):/ })).not.toBeInTheDocument();
    expect(screen.getAllByText("erledigt")).toHaveLength(3);
    expect(screen.getByRole("link", { name: "Noch eine Einheit" })).toHaveAttribute(
      "href",
      "/kurs/47",
    );
    expect(screen.getByText("Diese Woche an 3 Tagen geübt.")).toBeInTheDocument();
  });

  it("zählt einen einzelnen Übungstag in der Einzahl", async () => {
    renderWith({ week_days: 1 });
    expect(await screen.findByText("Diese Woche an 1 Tag geübt.")).toBeInTheDocument();
  });

  it("zeigt keine Wochenzeile ohne Übungstag", async () => {
    renderWith({ week_days: 0 });
    await screen.findByRole("list", { name: "Heute dran" });
    expect(screen.queryByText(/Diese Woche/)).not.toBeInTheDocument();
  });

  it("schickt Szenen mit dem Hinweis los, laut zu antworten", async () => {
    renderWith({
      steps: [
        {
          kind: "scene",
          status: "next",
          minutes: 4,
          title_de: "Bestellen bei Lena",
          detail_de: "Café",
          known: false,
          link: "/dorf/kafe?szene=kafe-01",
        },
      ],
    });
    const item = await screen.findByRole("listitem");
    expect(item).toHaveTextContent("Im Dorf · Bestellen bei Lena");
    expect(item).toHaveTextContent("Café — sag die Antwort laut, bevor du klickst.");
    expect(screen.getByRole("link", { name: "Los: Ins Dorf · ca. 4 Min." })).toHaveAttribute(
      "href",
      "/dorf/kafe?szene=kafe-01",
    );
  });

  it("macht ein bekanntes Gespräch zum Rückblick", async () => {
    renderWith({ steps: [{ ...listening, status: "next", known: true }] });
    expect(
      await screen.findByText("Kennst du schon — hör, wie viel du jetzt verstehst."),
    ).toBeInTheDocument();
  });

  it("bietet am Anfang die Einstufung an", async () => {
    renderWith({ offer_screening: true });
    expect(
      await screen.findByRole("link", { name: "Du kannst schon etwas Russisch? Einstufung · 2 Min." }),
    ).toHaveAttribute("href", "/einstufung");
  });

  it("führt immer auch zur Liste aller Einheiten", async () => {
    renderWith({});
    expect(await screen.findByRole("link", { name: "Alle Einheiten" })).toHaveAttribute(
      "href",
      "/kurs",
    );
  });

  it("meldet, wenn der Plan nicht geladen werden kann", async () => {
    vi.spyOn(api, "getToday").mockRejectedValue(new Error("weg"));
    render(
      <MemoryRouter>
        <TodayView />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Der Plan für heute konnte nicht geladen werden.")).toBeInTheDocument();
  });
});
