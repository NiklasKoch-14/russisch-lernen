import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import SpeakerButton from "./SpeakerButton";
import * as context from "./SpeechContext";

const useSpeechAs = (available: boolean | null) => {
  const say = vi.fn();
  vi.spyOn(context, "useSpeech").mockReturnValue({
    available,
    autoplay: true,
    setAutoplay: vi.fn(),
    say,
    lastError: null,
    activeVoice: null,
  });
  return say;
};

afterEach(() => vi.restoreAllMocks());

describe("SpeakerButton", () => {
  it("spricht den Text beim Klick", () => {
    const say = useSpeechAs(true);
    render(<SpeakerButton text="де́лаю" />);
    fireEvent.click(screen.getByRole("button", { name: "Anhören" }));
    expect(say).toHaveBeenCalledWith("де́лаю", { slow: false });
  });

  it("spricht langsam, wenn slow gesetzt ist", () => {
    const say = useSpeechAs(true);
    render(<SpeakerButton text="де́лаю" slow label="Langsam anhören" />);
    fireEvent.click(screen.getByRole("button", { name: "Langsam anhören" }));
    expect(say).toHaveBeenCalledWith("де́лаю", { slow: true });
  });

  it("erscheint gar nicht, wenn keine Stimme da ist", () => {
    useSpeechAs(false);
    render(<SpeakerButton text="де́лаю" />);
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("erscheint noch nicht, solange die Stimmen geladen werden", () => {
    useSpeechAs(null);
    render(<SpeakerButton text="де́лаю" />);
    expect(screen.queryByRole("button")).toBeNull();
  });
});
