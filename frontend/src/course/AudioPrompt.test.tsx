import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as context from "../audio/SpeechContext";
import * as server from "../audio/serverSpeech";
import AudioPrompt from "./AudioPrompt";

const mockSpeech = (available: boolean | null, autoplay = true) => {
  const say = vi.fn();
  vi.spyOn(context, "useSpeech").mockReturnValue({
    available,
    source: available ? "browser" : "none",
    autoplay,
    setAutoplay: vi.fn(),
    say,
    lastError: null,
    activeVoice: null,
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

describe("Vorladen", () => {
  const mockSource = (source: "server" | "browser") =>
    vi.spyOn(context, "useSpeech").mockReturnValue({
      available: true,
      source,
      autoplay: false,
      setAutoplay: vi.fn(),
      say: vi.fn(),
      lastError: null,
      activeVoice: null,
    });

  it("holt den Ton beim Betreten vor, wenn er vom Server kommt", () => {
    const prefetch = vi.spyOn(server, "prefetchAudio").mockResolvedValue();
    mockSource("server");
    render(<AudioPrompt text="дом" promptDe="Haus" />);
    expect(prefetch).toHaveBeenCalledWith("дом");
  });

  it("lädt nichts vor, wenn der Ton aus dem Browser kommt", () => {
    const prefetch = vi.spyOn(server, "prefetchAudio").mockResolvedValue();
    mockSource("browser");
    render(<AudioPrompt text="дом" promptDe="Haus" />);
    expect(prefetch).not.toHaveBeenCalled();
  });

  it("lädt je Satz nur einmal vor", () => {
    const prefetch = vi.spyOn(server, "prefetchAudio").mockResolvedValue();
    mockSource("server");
    const { rerender } = render(<AudioPrompt text="дом" promptDe="Haus" />);
    rerender(<AudioPrompt text="дом" promptDe="Haus" />);
    expect(prefetch).toHaveBeenCalledTimes(1);
  });
});
