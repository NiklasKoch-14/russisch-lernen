import { afterEach, describe, expect, it, vi } from "vitest";

import {
  SLOW_PLAYBACK_RATE,
  audioUrl,
  playAudio,
  prefetchAudio,
  serverAudioAvailable,
} from "./serverSpeech";

class FakeAudio {
  src = "";
  playbackRate = 1;
  preservesPitch = true;
  static lastInstance: FakeAudio | null = null;
  static shouldFail = false;

  constructor(src: string) {
    this.src = src;
    FakeAudio.lastInstance = this;
  }

  play(): Promise<void> {
    return FakeAudio.shouldFail ? Promise.reject(new Error("blockiert")) : Promise.resolve();
  }
}

afterEach(() => {
  vi.unstubAllGlobals();
  FakeAudio.shouldFail = false;
  FakeAudio.lastInstance = null;
});

describe("audioUrl", () => {
  it("kodiert den Text", () => {
    expect(audioUrl("дом")).toContain("text=%D0%B4%D0%BE%D0%BC");
  });

  it("zeigt auf den Audio-Endpunkt", () => {
    expect(audioUrl("дом")).toContain("/api/audio?");
  });

  it("liefert für denselben Text dieselbe URL — sonst greift der Browser-Cache nicht", () => {
    expect(audioUrl("дом")).toBe(audioUrl("дом"));
  });
});

describe("prefetchAudio", () => {
  it("holt die Datei vor", async () => {
    const fetchMock = vi.fn(() => Promise.resolve(new Response(new Blob())));
    vi.stubGlobal("fetch", fetchMock);
    await prefetchAudio("дом");
    expect(fetchMock).toHaveBeenCalledWith(audioUrl("дом"));
  });

  it("schluckt Fehler, statt den Aufrufer zu stören", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("weg"))));
    await expect(prefetchAudio("дом")).resolves.toBeUndefined();
  });
});

describe("playAudio", () => {
  it("spielt die Datei in normalem Tempo ab", async () => {
    vi.stubGlobal("Audio", FakeAudio);
    await playAudio("дом");
    expect(FakeAudio.lastInstance?.src).toContain("text=%D0%B4%D0%BE%D0%BC");
    expect(FakeAudio.lastInstance?.playbackRate).toBe(1);
  });

  it("spielt langsam, ohne die Stimme zu vertiefen", async () => {
    vi.stubGlobal("Audio", FakeAudio);
    await playAudio("дом", { slow: true });
    expect(FakeAudio.lastInstance?.playbackRate).toBe(SLOW_PLAYBACK_RATE);
    expect(FakeAudio.lastInstance?.preservesPitch).toBe(true);
  });

  it("wirft, wenn das Abspielen scheitert — der Aufrufer muss zurückfallen können", async () => {
    vi.stubGlobal("Audio", FakeAudio);
    FakeAudio.shouldFail = true;
    await expect(playAudio("дом")).rejects.toThrow();
  });
});

describe("serverAudioAvailable", () => {
  it("meldet true, wenn der Dienst verfügbar ist", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(Response.json({ available: true }))));
    await expect(serverAudioAvailable()).resolves.toBe(true);
  });

  it("meldet false, wenn der Dienst sich als nicht verfügbar meldet", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(Response.json({ available: false }))));
    await expect(serverAudioAvailable()).resolves.toBe(false);
  });

  it("meldet false bei einem Netzfehler", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("weg"))));
    await expect(serverAudioAvailable()).resolves.toBe(false);
  });

  it("meldet false bei einem Fehlerstatus", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response("", { status: 503 }))));
    await expect(serverAudioAvailable()).resolves.toBe(false);
  });
});
