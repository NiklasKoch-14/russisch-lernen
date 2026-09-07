import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as speech from "../audio/SpeechContext";
import * as api from "../courseApi";
import UnitView from "./UnitView";

const unit = {
  id: 5,
  stage: 1,
  title_de: "Hallo und tschüss",
  scenario_de: "Du triffst jemanden.",
  grammar_focus: {
    id: "f",
    title_de: "Locker oder förmlich?",
    explanation_de: "Zu Fremden sagst du здра́вствуйте.",
  },
  new_words: [],
  solved_exercise_ids: [],
  exercises: [
    {
      id: "5-3",
      type: "build_sentence" as const,
      audio_prompt: false,
      prompt_de: "Auf Wiedersehen!",
      tiles: [
        { index: 0, text: "свида́ния", translit: "svidánija" },
        { index: 1, text: "до", translit: "do" },
      ],
    },
    {
      id: "5-4",
      type: "build_sentence" as const,
      audio_prompt: false,
      prompt_de: "Vielen Dank!",
      tiles: [{ index: 0, text: "спаси́бо", translit: "spasíbo" }],
    },
  ],
};

function renderUnit() {
  return render(
    <MemoryRouter initialEntries={["/kurs/5"]}>
      <Routes>
        <Route path="/kurs/:unitId" element={<UnitView />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("UnitView", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("zeigt zuerst die Regel und startet danach die Aufgaben", async () => {
    vi.spyOn(api, "getUnit").mockResolvedValue(unit);
    renderUnit();
    expect(await screen.findByText("Locker oder förmlich?")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Los geht's" }));
    expect(await screen.findByText("Auf Wiedersehen!")).toBeInTheDocument();
  });

  it("zeigt nach einer falschen Antwort die Lösung", async () => {
    vi.spyOn(api, "getUnit").mockResolvedValue(unit);
    vi.spyOn(api, "submitAnswer").mockResolvedValue({
      correct: false,
      solution_text: "до свида́ния",
      solution_translit: "do svidánija",
      solution_audio: ["до свида́ния"],
      explanation_de: "Richtig ist: до свида́ния",
      unit_completed: false,
      correct_count: 0,
      total_count: 1,
    });
    renderUnit();
    fireEvent.click(await screen.findByRole("button", { name: "Los geht's" }));
    fireEvent.click(await screen.findByRole("button", { name: /свида́ния/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    expect(await screen.findByText(/до свида́ния/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Weiter" })).toBeInTheDocument();
  });

  it("zeigt am Ende den Abschluss-Bildschirm", async () => {
    vi.spyOn(api, "getUnit").mockResolvedValue({ ...unit, exercises: [unit.exercises[1]] });
    vi.spyOn(api, "submitAnswer").mockResolvedValue({
      correct: true,
      solution_text: "спаси́бо",
      solution_translit: "spasíbo",
      solution_audio: ["спаси́бо"],
      explanation_de: "",
      unit_completed: true,
      correct_count: 1,
      total_count: 1,
    });
    renderUnit();
    fireEvent.click(await screen.findByRole("button", { name: "Los geht's" }));
    fireEvent.click(await screen.findByRole("button", { name: /спаси́бо/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    fireEvent.click(await screen.findByRole("button", { name: "Weiter" }));
    expect(await screen.findByText("Einheit geschafft!")).toBeInTheDocument();
  });
});

describe("UnitView mit Ton", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(speech, "useSpeech").mockReturnValue({
      available: true,
      autoplay: false,
      setAutoplay: vi.fn(),
      say: vi.fn(),
    lastError: null,
    activeVoice: null,
      source: "browser",
    });
  });

  it("bietet die Lösung auch nach einer richtigen Antwort zum Anhören an", async () => {
    vi.spyOn(api, "getUnit").mockResolvedValue({ ...unit, exercises: [unit.exercises[1]] });
    vi.spyOn(api, "submitAnswer").mockResolvedValue({
      correct: true,
      solution_text: "спаси́бо",
      solution_translit: "spasíbo",
      solution_audio: ["спаси́бо"],
      explanation_de: "",
      unit_completed: false,
      correct_count: 1,
      total_count: 1,
    });
    renderUnit();
    fireEvent.click(await screen.findByRole("button", { name: "Los geht's" }));
    fireEvent.click(await screen.findByRole("button", { name: /спаси́бо/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    expect(await screen.findByRole("button", { name: "Anhören" })).toBeInTheDocument();
  });

  it("gibt bei einer Zuordnungsaufgabe jedes Wort einzeln zum Anhören", async () => {
    vi.spyOn(api, "getUnit").mockResolvedValue({ ...unit, exercises: [unit.exercises[1]] });
    vi.spyOn(api, "submitAnswer").mockResolvedValue({
      correct: true,
      solution_text: "я де́лаю",
      solution_translit: "ja délaju",
      solution_audio: ["я", "де́лаю"],
      explanation_de: "",
      unit_completed: false,
      correct_count: 1,
      total_count: 1,
    });
    renderUnit();
    fireEvent.click(await screen.findByRole("button", { name: "Los geht's" }));
    fireEvent.click(await screen.findByRole("button", { name: /спаси́бо/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    expect(await screen.findAllByRole("button", { name: "Anhören" })).toHaveLength(2);
  });
});

describe("UnitView stellt neue Wörter vor", () => {
  const mitWoertern = {
    ...unit,
    new_words: [
      { id: "govorit", text: "говори́ть", translit: "govorít'", gloss_de: "sprechen" },
    ],
  };

  beforeEach(() => vi.restoreAllMocks());

  it("zeigt die neuen Wörter zwischen Regel und Aufgaben", async () => {
    vi.spyOn(api, "getUnit").mockResolvedValue(mitWoertern);
    renderUnit();

    fireEvent.click(await screen.findByRole("button", { name: "Los geht's" }));
    expect(await screen.findByText("sprechen")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Aufgaben/ }));
    expect(await screen.findByText("Auf Wiedersehen!")).toBeInTheDocument();
  });

  it("überspringt sie, wenn die Einheit schon geschafft ist", async () => {
    vi.spyOn(api, "getUnit").mockResolvedValue({
      ...mitWoertern,
      solved_exercise_ids: mitWoertern.exercises.map((exercise) => exercise.id),
    });
    renderUnit();

    fireEvent.click(await screen.findByRole("button", { name: "Los geht's" }));
    expect(await screen.findByText("Auf Wiedersehen!")).toBeInTheDocument();
    expect(screen.queryByText("sprechen")).toBeNull();
  });

  it("überspringt sie, wenn die Einheit keine neuen Wörter hat", async () => {
    vi.spyOn(api, "getUnit").mockResolvedValue(unit);
    renderUnit();

    fireEvent.click(await screen.findByRole("button", { name: "Los geht's" }));
    expect(await screen.findByText("Auf Wiedersehen!")).toBeInTheDocument();
  });
});

describe("UnitView — Fehler-Nachlauf", () => {
  const falsch = {
    correct: false,
    solution_text: "до свида́ния",
    solution_translit: "do svidánija",
    solution_audio: ["до свида́ния"],
    explanation_de: "",
    unit_completed: false,
    correct_count: 0,
    total_count: 2,
  };
  const richtig = { ...falsch, correct: true, unit_completed: false };

  beforeEach(() => vi.restoreAllMocks());

  const loese = async (kachel: RegExp) => {
    fireEvent.click(await screen.findByRole("button", { name: kachel }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    fireEvent.click(await screen.findByRole("button", { name: "Weiter" }));
  };

  it("bringt eine falsch beantwortete Aufgabe wieder, statt die Einheit zu beenden", async () => {
    vi.spyOn(api, "getUnit").mockResolvedValue(unit);
    vi.spyOn(api, "submitAnswer").mockResolvedValue(falsch);
    renderUnit();

    fireEvent.click(await screen.findByRole("button", { name: "Los geht's" }));
    await loese(/свида́ния/);
    await loese(/спаси́бо/);

    expect(await screen.findByText(/Noch einmal/)).toBeInTheDocument();
    expect(screen.queryByText("Einheit geschafft!")).toBeNull();
  });

  it("zählt eine Wiederholung nicht als Fortschritt", async () => {
    vi.spyOn(api, "getUnit").mockResolvedValue(unit);
    vi.spyOn(api, "submitAnswer").mockResolvedValue(falsch);
    renderUnit();

    fireEvent.click(await screen.findByRole("button", { name: "Los geht's" }));
    expect(screen.getByText(/Aufgabe 1 von 2/)).toBeInTheDocument();
    await loese(/свида́ния/);

    // Falsch beantwortet heisst: nicht weitergekommen.
    expect(screen.getByText(/Aufgabe 1 von 2/)).toBeInTheDocument();
  });

  it("beendet die Einheit, wenn jede Aufgabe einmal richtig war", async () => {
    vi.spyOn(api, "getUnit").mockResolvedValue(unit);
    vi.spyOn(api, "submitAnswer").mockResolvedValue(richtig);
    renderUnit();

    fireEvent.click(await screen.findByRole("button", { name: "Los geht's" }));
    await loese(/свида́ния/);
    await loese(/спаси́бо/);

    expect(await screen.findByText("Einheit geschafft!")).toBeInTheDocument();
  });
});
