import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/** Eine Attrappe, die mitschreibt, welche Töne gestartet werden. */
class FakeAudioContext {
  static created = 0;
  static started: number[] = [];
  state = "running";
  currentTime = 0;
  destination = {};
  constructor() {
    FakeAudioContext.created += 1;
  }
  resume = vi.fn();
  createGain() {
    return {
      gain: { value: 1, setValueAtTime: vi.fn(), exponentialRampToValueAtTime: vi.fn() },
      connect: vi.fn(),
    };
  }
  createOscillator() {
    const oscillator = {
      type: "",
      frequency: { value: 0 },
      connect: vi.fn(),
      start: vi.fn(() => FakeAudioContext.started.push(oscillator.frequency.value)),
      stop: vi.fn(),
    };
    return oscillator;
  }
}

async function freshChime() {
  // Der Kontext ist modulweit — jeder Test braucht ein frisches Modul.
  vi.resetModules();
  return import("./chime");
}

describe("playChime", () => {
  beforeEach(() => {
    FakeAudioContext.created = 0;
    FakeAudioContext.started = [];
    vi.stubGlobal("AudioContext", FakeAudioContext);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("spielt zwei Töne aufwärts", async () => {
    const { playChime, CHIME_NOTES } = await freshChime();
    playChime();
    expect(FakeAudioContext.started).toEqual(CHIME_NOTES.map(([frequency]) => frequency));
    expect(CHIME_NOTES[1][0]).toBeGreaterThan(CHIME_NOTES[0][0]);
  });

  it("legt für viele Klänge nur einen Kontext an", async () => {
    const { playChime } = await freshChime();
    playChime();
    playChime();
    playChime();
    expect(FakeAudioContext.created).toBe(1);
  });

  it("bleibt still, wenn der Browser kein Web Audio kann", async () => {
    vi.stubGlobal("AudioContext", undefined);
    const { playChime } = await freshChime();
    expect(() => playChime()).not.toThrow();
  });

  it("schluckt Fehler des Browsers", async () => {
    vi.stubGlobal(
      "AudioContext",
      class {
        constructor() {
          throw new Error("kaputt");
        }
      },
    );
    const { playChime } = await freshChime();
    expect(() => playChime()).not.toThrow();
  });
});

describe("useChime", () => {
  afterEach(() => vi.restoreAllMocks());

  /** Alle drei Module aus derselben frischen Registry — sonst trifft die
   *  Attrappe eine andere Instanz von SpeechContext als der Hook. */
  async function hookWithSwitch(autoplay: boolean) {
    vi.resetModules();
    const speech = await import("./SpeechContext");
    const chime = await import("./chime");
    const play = vi.spyOn(chime, "playChime").mockImplementation(() => {});
    vi.spyOn(speech, "useSpeech").mockReturnValue({
      available: true,
      source: "browser",
      autoplay,
      setAutoplay: vi.fn(),
      say: vi.fn(),
      lastError: null,
      activeVoice: null,
    });
    const { useChime } = await import("./useChime");
    return { useChime, play };
  }

  it("klingt, wenn der Ton an ist", async () => {
    const { useChime, play } = await hookWithSwitch(true);
    renderHook(() => useChime()).result.current();
    expect(play).toHaveBeenCalledTimes(1);
  });

  it("bleibt still, wenn der Ton aus ist", async () => {
    const { useChime, play } = await hookWithSwitch(false);
    renderHook(() => useChime()).result.current();
    expect(play).not.toHaveBeenCalled();
  });
});
