import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AutoplayToggle from "./AutoplayToggle";
import * as context from "./SpeechContext";

const mockSpeech = (available: boolean | null, autoplay: boolean) => {
  const setAutoplay = vi.fn();
  vi.spyOn(context, "useSpeech").mockReturnValue({
    available,
    autoplay,
    setAutoplay,
    say: vi.fn(),
    lastError: null,
  });
  return setAutoplay;
};

afterEach(() => vi.restoreAllMocks());

describe("AutoplayToggle", () => {
  it("schaltet die Automatik aus", () => {
    const setAutoplay = mockSpeech(true, true);
    render(<AutoplayToggle />);
    fireEvent.click(screen.getByRole("switch", { name: "Automatisches Vorlesen ausschalten" }));
    expect(setAutoplay).toHaveBeenCalledWith(false);
  });

  it("schaltet die Automatik wieder ein", () => {
    const setAutoplay = mockSpeech(true, false);
    render(<AutoplayToggle />);
    fireEvent.click(screen.getByRole("switch", { name: "Automatisches Vorlesen einschalten" }));
    expect(setAutoplay).toHaveBeenCalledWith(true);
  });

  it("ist ohne Stimme deaktiviert", () => {
    mockSpeech(false, true);
    render(<AutoplayToggle />);
    expect(screen.getByRole("switch")).toBeDisabled();
  });
});

describe("AutoplayToggle und die Wortkacheln", () => {
  it("belegt aria-pressed nicht — das gehört den Kacheln", () => {
    mockSpeech(true, true);
    const { container } = render(<AutoplayToggle />);
    expect(container.querySelector("[aria-pressed]")).toBeNull();
  });
});
