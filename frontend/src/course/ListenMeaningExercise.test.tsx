import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as context from "../audio/SpeechContext";
import ListenMeaningExercise from "./ListenMeaningExercise";

const exercise = {
  id: "25-7",
  type: "listen_meaning" as const,
  prompt_de: "Hör zu. Was wird gesagt?",
  audio_text: "я живу́ в Берли́не",
  sentence: [
    { text: "я", translit: "ja" },
    { text: "живу́", translit: "živú" },
  ],
  options_de: ["Ich fahre nach Berlin.", "Ich wohne in Berlin.", "Er wohnt in Berlin."],
};

const mockSpeech = (available: boolean) =>
  vi.spyOn(context, "useSpeech").mockReturnValue({
    available,
    autoplay: false,
    setAutoplay: vi.fn(),
    say: vi.fn(),
    lastError: null,
  });

afterEach(() => vi.restoreAllMocks());

describe("ListenMeaningExercise", () => {
  it("schickt den angeklickten Anzeige-Index", () => {
    mockSpeech(true);
    const onSubmit = vi.fn();
    render(<ListenMeaningExercise exercise={exercise} onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: "Ich wohne in Berlin." }));
    expect(onSubmit).toHaveBeenCalledWith({ option_index: 1 });
  });

  it("verrät den Satz nicht, solange eine Stimme da ist", () => {
    mockSpeech(true);
    render(<ListenMeaningExercise exercise={exercise} onSubmit={vi.fn()} />);
    expect(screen.queryByText("живу́")).toBeNull();
  });

  it("zeigt ohne Stimme den Satz als Text und bleibt lösbar", () => {
    mockSpeech(false);
    const onSubmit = vi.fn();
    render(<ListenMeaningExercise exercise={exercise} onSubmit={onSubmit} />);
    expect(screen.getByText("живу́")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Er wohnt in Berlin." }));
    expect(onSubmit).toHaveBeenCalledWith({ option_index: 2 });
  });

  it("sperrt die Optionen, wenn die Aufgabe beantwortet ist", () => {
    mockSpeech(true);
    render(<ListenMeaningExercise exercise={exercise} disabled onSubmit={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Er wohnt in Berlin." })).toBeDisabled();
  });
});
