import { afterEach, describe, expect, it, vi } from "vitest";

import { NORMAL_RATE, SLOW_RATE, loadVoices, pickRussianVoice, speak, stripStress } from "./speech";

const voice = (lang: string, localService = true, name = lang) =>
  ({ lang, name, localService }) as SpeechSynthesisVoice;

class FakeUtterance {
  text: string;
  lang = "";
  rate = 1;
  voice: SpeechSynthesisVoice | null = null;
  constructor(text: string) {
    this.text = text;
  }
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("stripStress", () => {
  it("entfernt das kombinierende Betonungszeichen", () => {
    expect(stripStress("де́лаю")).toBe("делаю");
  });

  it("lässt ё unangetastet", () => {
    expect(stripStress("ещё")).toBe("ещё");
  });

  it("lässt Text ohne Betonung unverändert", () => {
    expect(stripStress("дом")).toBe("дом");
  });
});

describe("pickRussianVoice", () => {
  it("bevorzugt ru-RU", () => {
    expect(pickRussianVoice([voice("de-DE"), voice("ru"), voice("ru-RU")])?.lang).toBe("ru-RU");
  });

  it("nimmt sonst irgendeine russische Stimme", () => {
    expect(pickRussianVoice([voice("de-DE"), voice("ru")])?.lang).toBe("ru");
  });

  it("gibt null zurück, wenn keine russische Stimme da ist", () => {
    expect(pickRussianVoice([voice("de-DE"), voice("en-US")])).toBeNull();
  });

  it("zieht die lokale Stimme der Online-Stimme vor", () => {
    // Online-Stimmen gehen ueber das Netz: sie starten verzoegert und stocken.
    const online = voice("ru-RU", false, "Dmitry Online");
    const local = voice("ru-RU", true, "Irina Desktop");
    expect(pickRussianVoice([online, local])?.name).toBe("Irina Desktop");
  });

  it("nimmt eine lokale ru-Stimme vor einer Online-ru-RU-Stimme", () => {
    const online = voice("ru-RU", false, "Dmitry Online");
    const local = voice("ru", true, "Lokal");
    expect(pickRussianVoice([online, local])?.name).toBe("Lokal");
  });

  it("nimmt die Online-Stimme, wenn es keine lokale gibt", () => {
    const online = voice("ru-RU", false, "Dmitry Online");
    expect(pickRussianVoice([voice("de-DE"), online])?.name).toBe("Dmitry Online");
  });
});

describe("loadVoices", () => {
  it("liefert sofort, wenn die Liste schon gefüllt ist", async () => {
    vi.stubGlobal("speechSynthesis", {
      getVoices: () => [voice("ru-RU")],
      addEventListener: () => {},
      removeEventListener: () => {},
    });
    expect((await loadVoices()).map((item) => item.lang)).toEqual(["ru-RU"]);
  });

  it("wartet auf voiceschanged, wenn die Liste zuerst leer ist", async () => {
    const handlers: (() => void)[] = [];
    let voices: SpeechSynthesisVoice[] = [];
    vi.stubGlobal("speechSynthesis", {
      getVoices: () => voices,
      addEventListener: (_: string, callback: () => void) => {
        handlers.push(callback);
      },
      removeEventListener: () => {},
    });

    const pending = loadVoices();
    voices = [voice("ru-RU")];
    handlers.forEach((fire) => fire());

    expect((await pending).map((item) => item.lang)).toEqual(["ru-RU"]);
  });
});

describe("speak", () => {
  it("bricht laufende Ausgabe ab und spricht ohne Betonungszeichen", () => {
    const cancel = vi.fn();
    const speakSpy = vi.fn();
    vi.stubGlobal("speechSynthesis", { cancel, speak: speakSpy, getVoices: () => [] });
    vi.stubGlobal("SpeechSynthesisUtterance", FakeUtterance);

    speak("де́лаю", voice("ru-RU"), SLOW_RATE);

    expect(cancel).toHaveBeenCalled();
    expect(speakSpy.mock.calls[0][0]).toMatchObject({
      text: "делаю",
      rate: SLOW_RATE,
      lang: "ru-RU",
    });
  });

  it("spricht standardmäßig in normalem Tempo", () => {
    expect(NORMAL_RATE).toBe(1);
  });

  it("benutzt das normale Tempo als Standard", () => {
    const speakSpy = vi.fn();
    vi.stubGlobal("speechSynthesis", { cancel: vi.fn(), speak: speakSpy, getVoices: () => [] });
    vi.stubGlobal("SpeechSynthesisUtterance", FakeUtterance);

    speak("дом", voice("ru-RU"));

    expect(speakSpy.mock.calls[0][0].rate).toBe(NORMAL_RATE);
  });
});

describe("speak meldet Fehler", () => {
  it("reicht einen Synthesefehler an den Aufrufer weiter", () => {
    let spoken: { onerror?: (e: { error: string }) => void } | null = null;
    vi.stubGlobal("speechSynthesis", {
      cancel: vi.fn(),
      speak: (u: typeof spoken) => {
        spoken = u;
      },
      getVoices: () => [],
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

    const onError = vi.fn();
    speak("дом", voice("ru-RU"), NORMAL_RATE, onError);
    spoken!.onerror!({ error: "synthesis-failed" });

    expect(onError).toHaveBeenCalledWith("synthesis-failed");
  });
});
