import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as speech from "../audio/SpeechContext";
import * as api from "../courseApi";
import ReviewView from "./ReviewView";

const round = {
  left: [
    { index: 0, ref: "privet:base", text: "приве́т", translit: "privét" },
    { index: 1, ref: "poka:base", text: "пока́", translit: "poká" },
  ],
  right: [
    { index: 0, gloss_de: "tschüss (locker)" },
    { index: 1, gloss_de: "hallo (locker)" },
  ],
};

describe("ReviewView", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("meldet, wenn nichts fällig ist", async () => {
    vi.spyOn(api, "getReviewRound").mockResolvedValue({ left: [], right: [] });
    render(<ReviewView />);
    expect(await screen.findByText(/nichts zu wiederholen/i)).toBeInTheDocument();
  });

  it("schickt die Zuordnung ab und zeigt das Ergebnis", async () => {
    vi.spyOn(api, "getReviewRound").mockResolvedValue(round);
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
    expect(submit).toHaveBeenCalledWith([
      [0, 1],
      [1, 0],
    ]);
    expect(await screen.findByText("2 von 2 richtig")).toBeInTheDocument();
  });
});

describe("ReviewView mit Ton", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(speech, "useSpeech").mockReturnValue({
      available: true,
      autoplay: false,
      setAutoplay: vi.fn(),
      say: vi.fn(),
    lastError: null,
    });
  });

  it("lässt jede Form der Auflösung anhören", async () => {
    vi.spyOn(api, "getReviewRound").mockResolvedValue(round);
    vi.spyOn(api, "submitReviewRound").mockResolvedValue({
      correct_count: 2,
      total_count: 2,
      results: [
        { ref: "privet:base", correct: true, gloss_de: "hallo (locker)", text: "приве́т" },
        { ref: "poka:base", correct: false, gloss_de: "tschüss (locker)", text: "пока́" },
      ],
    });
    render(<ReviewView />);
    fireEvent.click(await screen.findByRole("button", { name: /приве́т/ }));
    fireEvent.click(screen.getByRole("button", { name: "hallo (locker)" }));
    fireEvent.click(screen.getByRole("button", { name: /пока́/ }));
    fireEvent.click(screen.getByRole("button", { name: "tschüss (locker)" }));
    expect(await screen.findAllByRole("button", { name: "Anhören" })).toHaveLength(2);
  });
});
