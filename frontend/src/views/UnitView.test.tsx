import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

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
