import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as speech from "../audio/SpeechContext";
import * as api from "../courseApi";
import ReviewView from "./ReviewView";

const zuordnung = {
  kind: "pairs" as const,
  left: [
    { index: 0, ref: "privet:base", text: "приве́т", translit: "privét" },
    { index: 1, ref: "poka:base", text: "пока́", translit: "poká" },
  ],
  right: [
    { index: 0, gloss_de: "tschüss (locker)" },
    { index: 1, gloss_de: "hallo (locker)" },
  ],
};

const kursaufgabe = {
  kind: "exercise" as const,
  unit_id: 8,
  exercise_id: "8-4",
  ref: "govorit:prs.1sg",
  id: "8-4",
  type: "choose_form" as const,
  prompt_de: "Welche Endung passt zu я?",
  audio_prompt: false,
  sentence: [{ text: "я", translit: "ja" }, null],
  options: [{ index: 0, text: "говорю́", translit: "govorjú" }],
};

const stumm = () =>
  vi.spyOn(speech, "useSpeech").mockReturnValue({
    available: false,
    source: "none",
    autoplay: false,
    setAutoplay: vi.fn(),
    say: vi.fn(),
    lastError: null,
    activeVoice: null,
  });

describe("ReviewView", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    stumm();
  });

  it("meldet, wenn nichts fällig ist", async () => {
    vi.spyOn(api, "getReviewRound").mockResolvedValue({ items: [] });
    render(<ReviewView />);
    expect(await screen.findByText(/nichts zu wiederholen/i)).toBeInTheDocument();
  });

  it("löst eine echte Kursaufgabe und schickt sie an den Wiederholungs-Endpunkt", async () => {
    vi.spyOn(api, "getReviewRound").mockResolvedValue({ items: [kursaufgabe] });
    const submit = vi.spyOn(api, "submitReviewExercise").mockResolvedValue({
      correct: true,
      solution_text: "говорю́",
      solution_translit: "govorjú",
      solution_audio: ["говорю́"],
      explanation_de: "",
      unit_completed: false,
      correct_count: 0,
      total_count: 0,
    });

    render(<ReviewView />);
    fireEvent.click(await screen.findByRole("button", { name: /говорю́/ }));

    await waitFor(() => expect(submit).toHaveBeenCalledWith(8, "8-4", { option_index: 0 }));
    expect(await screen.findByText("1 von 1 richtig")).toBeInTheDocument();
  });

  it("schickt die Zuordnung weiterhin an ihren eigenen Endpunkt", async () => {
    vi.spyOn(api, "getReviewRound").mockResolvedValue({ items: [zuordnung] });
    const submit = vi.spyOn(api, "submitReviewRound").mockResolvedValue({
      correct_count: 2,
      total_count: 2,
      results: [
        { ref: "privet:base", correct: true, gloss_de: "hallo (locker)", text: "приве́т" },
        { ref: "poka:base", correct: true, gloss_de: "tschüss (locker)", text: "пока́" },
      ],
    });

    render(<ReviewView />);
    fireEvent.click(await screen.findByRole("button", { name: /приве́т/ }));
    fireEvent.click(screen.getByRole("button", { name: "hallo (locker)" }));
    fireEvent.click(screen.getByRole("button", { name: /пока́/ }));
    fireEvent.click(screen.getByRole("button", { name: "tschüss (locker)" }));

    await waitFor(() => expect(submit).toHaveBeenCalled());
    expect(await screen.findByText("2 von 2 richtig")).toBeInTheDocument();
  });

  it("läuft beide Eintragsarten nacheinander durch", async () => {
    vi.spyOn(api, "getReviewRound").mockResolvedValue({ items: [kursaufgabe, zuordnung] });
    vi.spyOn(api, "submitReviewExercise").mockResolvedValue({
      correct: false,
      solution_text: "говорю́",
      solution_translit: "govorjú",
      solution_audio: [],
      explanation_de: "",
      unit_completed: false,
      correct_count: 0,
      total_count: 0,
    });

    render(<ReviewView />);
    expect(await screen.findByText("Wiederholung 1 von 2")).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: /говорю́/ }));

    // Danach die Zuordnung, nicht schon das Ergebnis.
    expect(await screen.findByRole("button", { name: /приве́т/ })).toBeInTheDocument();
  });
});
