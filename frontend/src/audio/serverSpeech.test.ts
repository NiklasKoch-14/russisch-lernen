import { afterEach, describe, expect, it, vi } from "vitest";

import {
  SLOW_PLAYBACK_RATE,
  audioUrl,
  clearAudioCache,
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
  /** Spielt von selbst zu Ende — wie ein kurzer Satz. Aus, wenn ein Test den
   *  Satz mitten im Abspielen braucht. */
  static autoEnd = true;

  constructor(src: string) {
    this.src = src;
    FakeAudio.lastInstance = this;
  }

  private handlers: Record<string, (() => void)[]> = {};

  addEventListener(type: string, handler: () => void) {
    (this.handlers[type] ??= []).push(handler);
  }

  private fire(type: string) {
    (this.handlers[type] ?? []).forEach((handler) => handler());
  }

  fireEnded() {
    this.fire("ended");
  }

  paused = false;
  currentTime = 1.2;

  pause() {
    this.paused = true;
    this.fire("pause");
  }

  play(): Promise<void> {
    if (FakeAudio.shouldFail) return Promise.reject(new Error("blockiert"));
    if (FakeAudio.autoEnd) queueMicrotask(() => this.fireEnded());
    return Promise.resolve();
  }
}

afterEach(() => {
  vi.unstubAllGlobals();
  FakeAudio.shouldFail = false;
  FakeAudio.autoEnd = true;
  FakeAudio.lastInstance = null;
  // Die Ablage liegt auf Modulebene und wuerde sonst in den naechsten Test lecken.
  clearAudioCache();
});

/** fetch + URL so stubben, dass playAudio aus einem fertigen Blob spielt. */
const stubBlobPlayback = (objectUrl = "blob:x") => {
  const fetchMock = vi.fn(() => Promise.resolve(new Response(new Blob(["x"]))));
  vi.stubGlobal("fetch", fetchMock);
  vi.stubGlobal("Audio", FakeAudio);
  vi.stubGlobal("URL", { createObjectURL: () => objectUrl, revokeObjectURL: vi.fn() });
  return fetchMock;
};

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
    stubBlobPlayback();
    await playAudio("дом");
    expect(FakeAudio.lastInstance?.playbackRate).toBe(1);
  });

  it("spielt langsam, ohne die Stimme zu vertiefen", async () => {
    stubBlobPlayback();
    await playAudio("дом", { slow: true });
    expect(FakeAudio.lastInstance?.playbackRate).toBe(SLOW_PLAYBACK_RATE);
    expect(FakeAudio.lastInstance?.preservesPitch).toBe(true);
  });

  it("wirft, wenn das Abspielen scheitert — der Aufrufer muss zurückfallen können", async () => {
    stubBlobPlayback();
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

describe("ein Abruf statt zwei", () => {
  it("teilt sich den Abruf zwischen Vorladen und Abspielen", async () => {
    const fetchMock = vi.fn(() => Promise.resolve(new Response(new Blob(["x"]))));
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("Audio", FakeAudio);
    vi.stubGlobal("URL", { createObjectURL: () => "blob:x", revokeObjectURL: vi.fn() });

    await prefetchAudio("дом");
    await playAudio("дом");

    // Zwei parallele Anfragen liessen das Audio-Element streamen — und genau
    // dabei wird das erste Wort abgeschnitten.
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("spielt aus dem fertig geladenen Blob, nicht von der URL", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(new Blob(["x"])))));
    vi.stubGlobal("Audio", FakeAudio);
    vi.stubGlobal("URL", { createObjectURL: () => "blob:fertig", revokeObjectURL: vi.fn() });

    await playAudio("дом");

    expect(FakeAudio.lastInstance?.src).toBe("blob:fertig");
  });

  it("gibt die Blob-URL nach dem Abspielen wieder frei", async () => {
    const revoke = vi.fn();
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(new Blob(["x"])))));
    vi.stubGlobal("Audio", FakeAudio);
    vi.stubGlobal("URL", { createObjectURL: () => "blob:x", revokeObjectURL: revoke });

    await playAudio("дом");

    expect(revoke).toHaveBeenCalledWith("blob:x");
  });

  it("wirft weiter, wenn der Abruf scheitert — der Rückfall muss greifen", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("weg"))));
    vi.stubGlobal("Audio", FakeAudio);
    await expect(playAudio("дом")).rejects.toThrow();
  });
});

describe("nur eine Wiedergabe zur Zeit", () => {
  it("stoppt die laufende Ausgabe, bevor die nächste startet", async () => {
    stubBlobPlayback();
    FakeAudio.autoEnd = false;
    const ersteAusgabe = playAudio("дом");
    await vi.waitFor(() => expect(FakeAudio.lastInstance).not.toBeNull());
    const erste = FakeAudio.lastInstance!;

    void playAudio("дом");
    // Die abgebrochene Ausgabe meldet sich als beendet — sonst hinge, wer auf sie wartet.
    await ersteAusgabe;

    // Ohne das ueberlagern sich Autoplay und Lautsprecherklick — das klingt
    // wie Stocken mitten im Satz.
    expect(erste.paused).toBe(true);
    expect(erste.currentTime).toBe(0);
    await vi.waitFor(() => expect(FakeAudio.lastInstance).not.toBe(erste));
  });

  it("kehrt erst zurück, wenn der Satz zu Ende ist", async () => {
    // Genau das fehlte beim Hörgespräch: meldete sich playAudio schon beim
    // Start, brach jede Zeile die vorige ab, und nur die letzte war zu hören.
    stubBlobPlayback();
    FakeAudio.autoEnd = false;
    let fertig = false;
    const ausgabe = playAudio("дом").then(() => {
      fertig = true;
    });
    await vi.waitFor(() => expect(FakeAudio.lastInstance).not.toBeNull());
    await Promise.resolve();
    expect(fertig).toBe(false);

    FakeAudio.lastInstance!.fireEnded();
    await ausgabe;
    expect(fertig).toBe(true);
  });
});

describe("Stimmen", () => {
  it("hängt die Rolle an die Adresse", () => {
    expect(audioUrl("дом")).not.toContain("voice=");
    expect(audioUrl("дом", "f")).toContain("voice=f");
  });

  it("hält die Stimmen im Speicher auseinander", async () => {
    // Sonst spraeche die zweite Figur mit dem Ton der ersten.
    const fetchMock = stubBlobPlayback();
    await prefetchAudio("дом", "m");
    await prefetchAudio("дом", "f");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("spielt mit der verlangten Stimme", async () => {
    const fetchMock = stubBlobPlayback();
    await playAudio("дом", { voice: "f" });
    expect(fetchMock).toHaveBeenCalledWith(audioUrl("дом", "f"));
  });
});
