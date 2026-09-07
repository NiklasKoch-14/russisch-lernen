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

describe("SpeechProvider rendert nicht die halbe App neu", () => {
  let renders = 0;

  function Counter() {
    renders += 1;
    const { say } = useSpeech();
    return (
      <button onClick={() => say("дом")} type="button">
        sprechen
      </button>
    );
  }

  it("löst beim Sprechen kein erneutes Rendern aus", async () => {
    stubVoices(["ru-RU"]);
    renders = 0;
    render(
      <SpeechProvider>
        <Counter />
      </SpeechProvider>,
    );
    // Erst die Stimmen- und Profilabfrage abwarten, dann zählen.
    await waitFor(() => expect(spoken).toEqual([]));
    await waitFor(() => expect(renders).toBeGreaterThan(0));
    await new Promise((resolve) => setTimeout(resolve, 20));

    const before = renders;
    screen.getByRole("button", { name: "sprechen" }).click();
    await new Promise((resolve) => setTimeout(resolve, 20));

    expect(spoken).toEqual(["дом"]);
    expect(renders).toBe(before);
  });
});

describe("Abbrechen ist kein Fehler", () => {
  let renders = 0;
  const utterances: { onerror?: (e: { error: string }) => void }[] = [];

  function Counter() {
    renders += 1;
    const { say, lastError } = useSpeech();
    return (
      <>
        <button onClick={() => say("дом")} type="button">
          sprechen
        </button>
        <span data-testid="fehler">{lastError ?? "keiner"}</span>
      </>
    );
  }

  const stubRecording = () => {
    utterances.length = 0;
    vi.stubGlobal("speechSynthesis", {
      getVoices: () => [{ lang: "ru-RU", name: "ru-RU", localService: true }],
      addEventListener: () => {},
      removeEventListener: () => {},
      cancel: () => {},
      speak: (u: (typeof utterances)[number]) => utterances.push(u),
    });
    vi.stubGlobal(
      "SpeechSynthesisUtterance",
      class {
        text: string;
        lang = "";
        rate = 1;
        voice: SpeechSynthesisVoice | null = null;
        onerror: ((e: { error: string }) => void) | null = null;
        constructor(text: string) {
          this.text = text;
        }
      },
    );
  };

  it("meldet ein abgebrochenes Vorlesen nicht als Fehler", async () => {
    stubRecording();
    renders = 0;
    render(
      <SpeechProvider>
        <Counter />
      </SpeechProvider>,
    );
    await waitFor(() => expect(renders).toBeGreaterThan(0));
    await new Promise((resolve) => setTimeout(resolve, 20));

    screen.getByRole("button", { name: "sprechen" }).click();
    await new Promise((resolve) => setTimeout(resolve, 20));
    const before = renders;

    // Der Nutzer klickt erneut: cancel() bricht die laufende Ausgabe ab.
    utterances[0].onerror!({ error: "interrupted" });
    await new Promise((resolve) => setTimeout(resolve, 20));

    expect(screen.getByTestId("fehler")).toHaveTextContent("keiner");
    expect(renders).toBe(before);
  });

  it("meldet einen echten Synthesefehler weiterhin", async () => {
    stubRecording();
    render(
      <SpeechProvider>
        <Counter />
      </SpeechProvider>,
    );
    await new Promise((resolve) => setTimeout(resolve, 20));
    screen.getByRole("button", { name: "sprechen" }).click();
    await new Promise((resolve) => setTimeout(resolve, 20));

    utterances[0].onerror!({ error: "synthesis-failed" });
    await waitFor(() =>
      expect(screen.getByTestId("fehler")).toHaveTextContent("synthesis-failed"),
    );
  });
});
