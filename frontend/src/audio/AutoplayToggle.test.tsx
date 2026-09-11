import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AutoplayToggle from "./AutoplayToggle";
import * as context from "./SpeechContext";

const mockSpeech = (available: boolean | null, autoplay: boolean) => {
  const setAutoplay = vi.fn();
  vi.spyOn(context, "useSpeech").mockReturnValue({
    available,
    source: available ? "browser" : "none",
    autoplay,
    setAutoplay,
    say: vi.fn(),
    lastError: null,
    activeVoice: null,
  });
  return setAutoplay;
};

afterEach(() => vi.restoreAllMocks());

describe("AutoplayToggle", () => {
  it("schaltet den Ton aus", () => {
    const setAutoplay = mockSpeech(true, true);
    render(<AutoplayToggle />);
    fireEvent.click(screen.getByRole("switch", { name: "Ton ausschalten" }));
    expect(setAutoplay).toHaveBeenCalledWith(false);
  });

  it("schaltet den Ton wieder ein", () => {
    const setAutoplay = mockSpeech(true, false);
    render(<AutoplayToggle />);
    fireEvent.click(screen.getByRole("switch", { name: "Ton einschalten" }));
    expect(setAutoplay).toHaveBeenCalledWith(true);
  });

  it("bleibt ohne Stimme bedienbar, weil er auch den Richtig-Klang steuert", () => {
    // Den Klang erzeugt der Browser selbst — er geht auch ohne russische Stimme.
    // Ein gesperrter Schalter liesse sich dann nicht mehr leise stellen.
    mockSpeech(false, true);
    render(<AutoplayToggle />);
    const toggle = screen.getByRole("switch", { name: "Ton ausschalten" });
    expect(toggle).toBeEnabled();
    expect(toggle).toHaveAttribute("title", expect.stringMatching(/Keine russische Stimme/));
  });

  it("sagt, was er steuert", () => {
    mockSpeech(true, true);
    render(<AutoplayToggle />);
    expect(screen.getByRole("switch")).toHaveAttribute(
      "title",
      "Ton ausschalten — Vorlesen und Klänge",
    );
  });
});

describe("AutoplayToggle und die Wortkacheln", () => {
  it("belegt aria-pressed nicht — das gehört den Kacheln", () => {
    mockSpeech(true, true);
    const { container } = render(<AutoplayToggle />);
    expect(container.querySelector("[aria-pressed]")).toBeNull();
  });
});
