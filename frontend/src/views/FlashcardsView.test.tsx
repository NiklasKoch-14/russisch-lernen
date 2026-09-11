import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as speech from "../audio/SpeechContext";
import * as chimeHook from "../audio/useChime";
import type { FlashcardRound } from "../courseTypes";
import * as api from "../flashcardsApi";
import FlashcardsView from "./FlashcardsView";

const runde: FlashcardRound = {
  seed: "s",
  known_words: 42,
  cards: [
    {
      lexeme_id: "butylka",
      direction: "ru_de",
      prompt_ru: { text: "буты́лка", translit: "butýlka" },
      prompt_de: null,
      options_de: ["die Tasse", "die Flasche", "die Tüte"],
      options_ru: [],
    },
    {
      lexeme_id: "sdacha",
      direction: "de_ru",
      prompt_ru: null,
      prompt_de: "das Wechselgeld",
      options_de: [],
      options_ru: [
        { text: "сда́ча", translit: "sdáča" },
        { text: "чек", translit: "ček" },
        { text: "ка́сса", translit: "kássa" },
      ],
    },
  ],
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

/** Eine Option anklicken und die Antwort abwarten. */
const waehle = async (name: string | RegExp) => {
  const option = await screen.findByRole("button", { name });
  await act(async () => {
    fireEvent.click(option);
  });
};

describe("FlashcardsView", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    stumm();
    vi.spyOn(api, "getFlashcardRound").mockResolvedValue(runde);
    vi.spyOn(api, "answerFlashcard").mockResolvedValue({
      correct: true,
      correct_index: 1,
      text: "буты́лка",
      translit: "butýlka",
      gloss_de: "die Flasche",
    });
  });

  it("zeigt das russische Wort mit drei deutschen Bedeutungen", async () => {
    render(<FlashcardsView />);

    expect(await screen.findByText("буты́лка")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "die Flasche" })).toBeInTheDocument();
    expect(screen.getByText("Karte 1 von 2")).toBeInTheDocument();
    expect(screen.getByText("42 Wörter gelernt")).toBeInTheDocument();
  });

  it("meldet die richtige Antwort und geht weiter zur nächsten Karte", async () => {
    render(<FlashcardsView />);
    await waehle("die Flasche");

    expect(await screen.findByText("Richtig.")).toBeInTheDocument();
    expect(api.answerFlashcard).toHaveBeenCalledWith("butylka", "s", 1);

    await waehle("Weiter");
    expect(await screen.findByText("das Wechselgeld")).toBeInTheDocument();
  });

  it("nennt bei einer falschen Antwort Wort und Bedeutung", async () => {
    vi.spyOn(api, "answerFlashcard").mockResolvedValue({
      correct: false,
      correct_index: 1,
      text: "буты́лка",
      translit: "butýlka",
      gloss_de: "die Flasche",
    });
    render(<FlashcardsView />);
    await waehle("die Tüte");

    expect(await screen.findByText(/Richtig wäre: буты́лка — die Flasche/)).toBeInTheDocument();
  });

  it("zeigt bei umgekehrter Richtung russische Optionen", async () => {
    render(<FlashcardsView />);
    await waehle("die Flasche");
    await waehle("Weiter");

    expect(await screen.findByText("das Wechselgeld")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /сда́ча/ })).toBeInTheDocument();
  });

  it("zählt am Rundenende die Treffer und holt eine neue Runde", async () => {
    render(<FlashcardsView />);
    await waehle("die Flasche");
    await waehle("Weiter");
    await waehle(/сда́ча/);
    await waehle("Weiter");

    expect(await screen.findByText("2 von 2 richtig")).toBeInTheDocument();
    await waehle("Neue Runde");
    await waitFor(() => expect(api.getFlashcardRound).toHaveBeenCalledTimes(2));
  });

  it("holt beim Umschalten der Richtung eine neue Runde", async () => {
    render(<FlashcardsView />);
    await screen.findByText("буты́лка");

    await waehle("RU → DE");
    await waitFor(() => expect(api.getFlashcardRound).toHaveBeenLastCalledWith("ru_de"));
  });

  it("sagt es, wenn noch keine Wörter gelernt sind", async () => {
    vi.spyOn(api, "getFlashcardRound").mockResolvedValue({
      seed: "s",
      known_words: 0,
      cards: [],
    });
    render(<FlashcardsView />);

    expect(await screen.findByRole("heading", { name: "Noch keine Wörter" })).toBeInTheDocument();
  });

  it("klingt bei einer richtigen Karte", async () => {
    const chime = vi.fn();
    vi.spyOn(chimeHook, "useChime").mockReturnValue(chime);
    render(<FlashcardsView />);
    await waehle("die Flasche");
    await screen.findByText("Richtig.");
    expect(chime).toHaveBeenCalledTimes(1);
  });

  it("bleibt bei einer falschen Karte still", async () => {
    const chime = vi.fn();
    vi.spyOn(chimeHook, "useChime").mockReturnValue(chime);
    vi.spyOn(api, "answerFlashcard").mockResolvedValue({
      correct: false,
      correct_index: 1,
      text: "буты́лка",
      translit: "butýlka",
      gloss_de: "die Flasche",
    });
    render(<FlashcardsView />);
    await waehle("die Tüte");
    await screen.findByText(/Richtig wäre/);
    expect(chime).not.toHaveBeenCalled();
  });
});
