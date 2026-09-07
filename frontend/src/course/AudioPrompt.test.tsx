import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as context from "../audio/SpeechContext";
import AudioPrompt from "./AudioPrompt";

const mockSpeech = (available: boolean | null, autoplay = true) => {
  const say = vi.fn();
  vi.spyOn(context, "useSpeech").mockReturnValue({
    available,
    autoplay,
    setAutoplay: vi.fn(),
    say,
    lastError: null,
  });
  return say;
};

afterEach(() => vi.restoreAllMocks());

describe("AudioPrompt", () => {
  it("verbirgt den deutschen Prompt, wenn eine Stimme da ist", () => {
    mockSpeech(true, false);
    render(<AudioPrompt text="ско́лько тебе́ лет" promptDe="Wie alt bist du?" />);
    expect(screen.queryByText("Wie alt bist du?")).toBeNull();
    expect(screen.getByRole("button", { name: "Anhören" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Langsam anhören" })).toBeInTheDocument();
  });

  it("zeigt ohne Stimme den deutschen Prompt statt der Knöpfe", () => {
    mockSpeech(false);
    render(<AudioPrompt text="ско́лько тебе́ лет" promptDe="Wie alt bist du?" />);
    expect(screen.getByText("Wie alt bist du?")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("spielt bei eingeschalteter Automatik einmal von allein ab", () => {
    const say = mockSpeech(true, true);
    render(<AudioPrompt text="дом" promptDe="Haus" />);
    expect(say).toHaveBeenCalledWith("дом", { slow: false });
  });

  it("spielt bei ausgeschalteter Automatik nichts von allein ab", () => {
    const say = mockSpeech(true, false);
    render(<AudioPrompt text="дом" promptDe="Haus" />);
    expect(say).not.toHaveBeenCalled();
  });

  it("spielt auch bei eingeschalteter Automatik nur ein einziges Mal ab", () => {
    const say = mockSpeech(true, true);
    const { rerender } = render(<AudioPrompt text="дом" promptDe="Haus" />);
    rerender(<AudioPrompt text="дом" promptDe="Haus" />);
    expect(say).toHaveBeenCalledTimes(1);
  });
});
