import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SpeechProvider, useSpeech } from "./SpeechContext";

const { getProfile, patchProfile } = vi.hoisted(() => ({
  getProfile: vi.fn(),
  patchProfile: vi.fn(),
}));

vi.mock("../courseApi", () => ({ getProfile, patchProfile }));

const profile = (audio_autoplay: boolean) => ({
  language: "russian",
  cefr_level: "A1",
  show_transliteration: true,
  placement_unit: null,
  audio_autoplay,
});

function Probe() {
  const { available, autoplay, say } = useSpeech();
  return (
    <>
      <p>{`${available}-${autoplay}`}</p>
      <button onClick={() => say("де́лаю")}>sprechen</button>
    </>
  );
}

const spoken: string[] = [];

const stubVoices = (langs: string[]) => {
  vi.stubGlobal("speechSynthesis", {
    getVoices: () => langs.map((lang) => ({ lang, name: lang })),
    addEventListener: () => {},
    removeEventListener: () => {},
    cancel: () => {},
    speak: (utterance: { text: string }) => spoken.push(utterance.text),
  });
  vi.stubGlobal(
    "SpeechSynthesisUtterance",
    class {
      text: string;
      lang = "";
      rate = 1;
      voice: SpeechSynthesisVoice | null = null;
      constructor(text: string) {
        this.text = text;
      }
    },
  );
};

beforeEach(() => {
  spoken.length = 0;
  getProfile.mockResolvedValue(profile(true));
  patchProfile.mockResolvedValue(undefined);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("SpeechProvider", () => {
  it("meldet available=true, wenn eine russische Stimme da ist", async () => {
    stubVoices(["de-DE", "ru-RU"]);
    render(
      <SpeechProvider>
        <Probe />
      </SpeechProvider>,
    );
    await waitFor(() => expect(screen.getByText("true-true")).toBeInTheDocument());
  });

  it("meldet available=false ohne russische Stimme", async () => {
    stubVoices(["de-DE"]);
    render(
      <SpeechProvider>
        <Probe />
      </SpeechProvider>,
    );
    await waitFor(() => expect(screen.getByText("false-true")).toBeInTheDocument());
  });

  it("übernimmt den Autoplay-Zustand aus dem Profil", async () => {
    getProfile.mockResolvedValue(profile(false));
    stubVoices(["ru-RU"]);
    render(
      <SpeechProvider>
        <Probe />
      </SpeechProvider>,
    );
    await waitFor(() => expect(screen.getByText("true-false")).toBeInTheDocument());
  });

  it("spricht nicht, solange keine Stimme gefunden wurde", async () => {
    stubVoices(["de-DE"]);
    render(
      <SpeechProvider>
        <Probe />
      </SpeechProvider>,
    );
    await waitFor(() => expect(screen.getByText("false-true")).toBeInTheDocument());
    screen.getByRole("button", { name: "sprechen" }).click();
    expect(spoken).toEqual([]);
  });

  it("spricht ohne Betonungszeichen, wenn eine Stimme da ist", async () => {
    stubVoices(["ru-RU"]);
    render(
      <SpeechProvider>
        <Probe />
      </SpeechProvider>,
    );
    await waitFor(() => expect(screen.getByText("true-true")).toBeInTheDocument());
    screen.getByRole("button", { name: "sprechen" }).click();
    expect(spoken).toEqual(["делаю"]);
  });
});
