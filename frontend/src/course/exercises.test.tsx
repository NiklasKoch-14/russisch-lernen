import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as speech from "../audio/SpeechContext";

import BuildSentenceExercise from "./BuildSentenceExercise";
import ChooseFormExercise from "./ChooseFormExercise";
import DialogReplyExercise from "./DialogReplyExercise";
import MatchPairsExercise from "./MatchPairsExercise";

const build = {
  id: "6-2",
  type: "build_sentence" as const,
  audio_prompt: false,
  prompt_de: "Wie heißen Sie?",
  tiles: [
    { index: 0, text: "зову́т", translit: "zovút" },
    { index: 1, text: "как", translit: "kak" },
    { index: 2, text: "вас", translit: "vas" },
  ],
};

describe("BuildSentenceExercise", () => {
  it("baut den Satz in Klickreihenfolge", () => {
    const onSubmit = vi.fn();
    render(<BuildSentenceExercise exercise={build} onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: /как/ }));
    fireEvent.click(screen.getByRole("button", { name: /вас/ }));
    fireEvent.click(screen.getByRole("button", { name: /зову́т/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    expect(onSubmit).toHaveBeenCalledWith({ tile_indices: [1, 2, 0] });
  });

  it("nimmt eine Kachel per erneutem Klick wieder heraus", () => {
    const onSubmit = vi.fn();
    render(<BuildSentenceExercise exercise={build} onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: /как/ }));
    fireEvent.click(screen.getByRole("button", { name: /как/ }));
    fireEvent.click(screen.getByRole("button", { name: /вас/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    expect(onSubmit).toHaveBeenCalledWith({ tile_indices: [2] });
  });

  it("lässt Prüfen erst zu, wenn etwas gewählt wurde", () => {
    render(<BuildSentenceExercise exercise={build} onSubmit={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Prüfen" })).toBeDisabled();
  });
});

const choose = {
  id: "6-4",
  type: "choose_form" as const,
  audio_prompt: false,
  prompt_de: "Welche Form von ты passt?",
  sentence: [{ text: "как", translit: "kak" }, null, { text: "зову́т", translit: "zovút" }],
  options: [
    { index: 0, text: "ты", translit: "ty" },
    { index: 1, text: "тебя́", translit: "tebjá" },
  ],
};

describe("ChooseFormExercise", () => {
  it("zeigt die Lücke im Satz", () => {
    render(<ChooseFormExercise exercise={choose} onSubmit={vi.fn()} />);
    expect(screen.getByTestId("blank")).toBeInTheDocument();
  });

  it("meldet den gewählten Index", () => {
    const onSubmit = vi.fn();
    render(<ChooseFormExercise exercise={choose} onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: /тебя́/ }));
    expect(onSubmit).toHaveBeenCalledWith({ option_index: 1 });
  });
});

const match = {
  id: "5-1",
  type: "match_pairs" as const,
  prompt_de: "Ordne zu.",
  left: [
    { index: 0, text: "приве́т", translit: "privét" },
    { index: 1, text: "пока́", translit: "poká" },
  ],
  right: [
    { index: 0, gloss_de: "tschüss (locker)" },
    { index: 1, gloss_de: "hallo (locker)" },
  ],
};

describe("MatchPairsExercise", () => {
  it("sendet die Paare, sobald alle zugeordnet sind", () => {
    const onSubmit = vi.fn();
    render(<MatchPairsExercise exercise={match} onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: /приве́т/ }));
    fireEvent.click(screen.getByRole("button", { name: "hallo (locker)" }));
    fireEvent.click(screen.getByRole("button", { name: /пока́/ }));
    fireEvent.click(screen.getByRole("button", { name: "tschüss (locker)" }));
    expect(onSubmit).toHaveBeenCalledWith({ pairs: [[0, 1], [1, 0]] });
  });

  it("sendet nichts, solange noch Paare fehlen", () => {
    const onSubmit = vi.fn();
    render(<MatchPairsExercise exercise={match} onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: /приве́т/ }));
    fireEvent.click(screen.getByRole("button", { name: "hallo (locker)" }));
    expect(onSubmit).not.toHaveBeenCalled();
  });
});

const dialog = {
  id: "5-6",
  type: "dialog_reply" as const,
  prompt_de: "Was antwortest du?",
  tutor_line: [{ text: "здра́вствуйте", translit: "zdrávstvujte" }],
  options: [
    { index: 0, text: "пока́", translit: "poká" },
    { index: 1, text: "здра́вствуйте", translit: "zdrávstvujte" },
  ],
};

describe("DialogReplyExercise", () => {
  it("zeigt die Tutor-Zeile und meldet die Wahl", () => {
    const onSubmit = vi.fn();
    render(<DialogReplyExercise exercise={dialog} onSubmit={onSubmit} />);
    expect(screen.getByTestId("tutor-line")).toHaveTextContent("здра́вствуйте");
    fireEvent.click(screen.getAllByRole("button", { name: /пока́/ })[0]);
    expect(onSubmit).toHaveBeenCalledWith({ option_index: 0 });
  });
});

const mockSpeech = (available: boolean) =>
  vi.spyOn(speech, "useSpeech").mockReturnValue({
    available,
    autoplay: false,
    setAutoplay: vi.fn(),
    say: vi.fn(),
  });

afterEach(() => vi.restoreAllMocks());

describe("Hör-Prompt", () => {
  it("ersetzt bei build_sentence den deutschen Prompt durch den Abspielknopf", () => {
    mockSpeech(true);
    render(
      <BuildSentenceExercise
        exercise={{ ...build, audio_prompt: true, audio_text: "как вас зову́т" }}
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.queryByText("Wie heißen Sie?")).toBeNull();
    expect(screen.getByRole("button", { name: "Anhören" })).toBeInTheDocument();
  });

  it("fällt bei build_sentence ohne Stimme auf den deutschen Prompt zurück", () => {
    mockSpeech(false);
    render(
      <BuildSentenceExercise
        exercise={{ ...build, audio_prompt: true, audio_text: "как вас зову́т" }}
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.getByText("Wie heißen Sie?")).toBeInTheDocument();
  });

  it("bleibt bei build_sentence ohne Stimme lösbar", () => {
    mockSpeech(false);
    const onSubmit = vi.fn();
    render(
      <BuildSentenceExercise
        exercise={{ ...build, audio_prompt: true, audio_text: "как вас зову́т" }}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /как/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    expect(onSubmit).toHaveBeenCalledWith({ tile_indices: [1] });
  });

  it("ersetzt bei choose_form den deutschen Prompt durch den Abspielknopf", () => {
    mockSpeech(true);
    render(
      <ChooseFormExercise
        exercise={{ ...choose, audio_prompt: true, audio_text: "я де́лаю" }}
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: "Anhören" })).toBeInTheDocument();
  });
});
