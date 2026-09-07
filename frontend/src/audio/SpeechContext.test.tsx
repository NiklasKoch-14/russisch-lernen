import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as server from "./serverSpeech";
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
  // Ohne das fetcht der Provider gegen das echte Backend — die Tests haengen
  // dann davon ab, ob gerade ein Stack laeuft. Die Serverstufe wird dort
  // geprueft, wo sie hingehoert (siehe "Drei Stufen").
  vi.spyOn(server, "serverAudioAvailable").mockResolvedValue(false);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
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

describe("Welche Stimme ist aktiv", () => {
  function Probe2() {
    const { activeVoice } = useSpeech();
    return (
      <span data-testid="stimme">
        {activeVoice ? `${activeVoice.name}|${activeVoice.local ? "lokal" : "online"}` : "keine"}
      </span>
    );
  }

  const withVoices = (list: { lang: string; name: string; localService: boolean }[]) => {
    vi.stubGlobal("speechSynthesis", {
      getVoices: () => list,
      addEventListener: () => {},
      removeEventListener: () => {},
      cancel: () => {},
      speak: () => {},
    });
  };

  it("nennt die gewählte Stimme und ob sie aus dem Netz kommt", async () => {
    withVoices([
      { lang: "ru-RU", name: "Irina Desktop", localService: true },
      { lang: "ru-RU", name: "Dmitry Online", localService: false },
    ]);
    render(
      <SpeechProvider>
        <Probe2 />
      </SpeechProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("stimme")).toHaveTextContent("Dmitry Online|online"),
    );
  });

  it("meldet die lokale Stimme, wenn es keine andere gibt", async () => {
    withVoices([{ lang: "ru-RU", name: "Irina Desktop", localService: true }]);
    render(
      <SpeechProvider>
        <Probe2 />
      </SpeechProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("stimme")).toHaveTextContent("Irina Desktop|lokal"),
    );
  });

  it("meldet keine Stimme, wenn keine russische da ist", async () => {
    withVoices([{ lang: "de-DE", name: "Katja", localService: true }]);
    render(
      <SpeechProvider>
        <Probe2 />
      </SpeechProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("stimme")).toHaveTextContent("keine"));
  });
});

describe("Drei Stufen", () => {
  function Stufe() {
    const { source, available, say } = useSpeech();
    return (
      <>
        <span data-testid="quelle">{source}</span>
        <span data-testid="ton">{String(available)}</span>
        <button type="button" onClick={() => void say("дом")}>
          sprechen
        </button>
      </>
    );
  }

  const renderStufe = () =>
    render(
      <SpeechProvider>
        <Stufe />
      </SpeechProvider>,
    );

  it("nimmt den Server, wenn er antwortet", async () => {
    vi.spyOn(server, "serverAudioAvailable").mockResolvedValue(true);
    const play = vi.spyOn(server, "playAudio").mockResolvedValue();
    stubVoices([]);
    renderStufe();

    await waitFor(() => expect(screen.getByTestId("quelle")).toHaveTextContent("server"));
    screen.getByRole("button", { name: "sprechen" }).click();
    await waitFor(() => expect(play).toHaveBeenCalledWith("дом", { slow: false }));
  });

  it("nimmt die Browserstimme, wenn der Server schweigt", async () => {
    vi.spyOn(server, "serverAudioAvailable").mockResolvedValue(false);
    stubVoices(["ru-RU"]);
    renderStufe();

    await waitFor(() => expect(screen.getByTestId("quelle")).toHaveTextContent("browser"));
    screen.getByRole("button", { name: "sprechen" }).click();
    await waitFor(() => expect(spoken).toEqual(["дом"]));
  });

  it("meldet keinen Ton, wenn beides fehlt", async () => {
    vi.spyOn(server, "serverAudioAvailable").mockResolvedValue(false);
    stubVoices(["de-DE"]);
    renderStufe();

    await waitFor(() => expect(screen.getByTestId("quelle")).toHaveTextContent("none"));
    expect(screen.getByTestId("ton")).toHaveTextContent("false");
  });

  it("meldet Ton, sobald eine der beiden Quellen da ist", async () => {
    vi.spyOn(server, "serverAudioAvailable").mockResolvedValue(true);
    vi.spyOn(server, "playAudio").mockResolvedValue();
    stubVoices(["de-DE"]);
    renderStufe();

    await waitFor(() => expect(screen.getByTestId("ton")).toHaveTextContent("true"));
  });

  it("fällt auf den Browser zurück, wenn das Abspielen scheitert", async () => {
    vi.spyOn(server, "serverAudioAvailable").mockResolvedValue(true);
    vi.spyOn(server, "playAudio").mockRejectedValue(new Error("blockiert"));
    stubVoices(["ru-RU"]);
    renderStufe();

    await waitFor(() => expect(screen.getByTestId("quelle")).toHaveTextContent("server"));
    screen.getByRole("button", { name: "sprechen" }).click();

    await waitFor(() => expect(spoken).toEqual(["дом"]));
    await waitFor(() => expect(screen.getByTestId("quelle")).toHaveTextContent("browser"));
  });

  it("probiert den toten Dienst nicht bei jedem Klick erneut", async () => {
    vi.spyOn(server, "serverAudioAvailable").mockResolvedValue(true);
    const play = vi.spyOn(server, "playAudio").mockRejectedValue(new Error("blockiert"));
    stubVoices(["ru-RU"]);
    renderStufe();

    await waitFor(() => expect(screen.getByTestId("quelle")).toHaveTextContent("server"));
    const knopf = screen.getByRole("button", { name: "sprechen" });
    knopf.click();
    await waitFor(() => expect(screen.getByTestId("quelle")).toHaveTextContent("browser"));
    knopf.click();
    await waitFor(() => expect(spoken).toEqual(["дом", "дом"]));

    expect(play).toHaveBeenCalledTimes(1);
  });
});
