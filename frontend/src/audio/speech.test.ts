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

  it("zieht die natürlich klingende Stimme der lokalen vor", () => {
    // Die lokalen Windows-Desktop-Stimmen sind leise und verschlucken kurze
    // Woerter; die Natural-Stimmen klingen besser, kommen aber aus dem Netz.
    const natural = voice("ru-RU", false, "Dmitry Online");
    const desktop = voice("ru-RU", true, "Irina Desktop");
    expect(pickRussianVoice([desktop, natural])?.name).toBe("Dmitry Online");
  });

  it("findet die natürliche Stimme unabhängig von der Listenreihenfolge", () => {
    const natural = voice("ru-RU", false, "Dmitry Online");
    const desktop = voice("ru-RU", true, "Irina Desktop");
    expect(pickRussianVoice([natural, desktop])?.name).toBe("Dmitry Online");
  });

  it("nimmt die lokale Stimme, wenn es keine natürliche gibt", () => {
    const desktop = voice("ru-RU", true, "Irina Desktop");
    expect(pickRussianVoice([voice("de-DE"), desktop])?.name).toBe("Irina Desktop");
  });

  it("bevorzugt innerhalb einer Gruppe die genauere Sprachkennung", () => {
    const broad = voice("ru", false, "Breit Online");
    const exact = voice("ru-RU", false, "Genau Online");
    expect(pickRussianVoice([broad, exact])?.name).toBe("Genau Online");
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

describe("speak wartet auf das Ende", () => {
  const stubSynthesis = () => {
    let spoken: { onend?: () => void; onerror?: (e: { error: string }) => void } | null = null;
    vi.stubGlobal("speechSynthesis", {
      cancel: vi.fn(),
      speak: (u: typeof spoken) => {
        spoken = u;
      },
      getVoices: () => [],
    });
    vi.stubGlobal("SpeechSynthesisUtterance", FakeUtterance);
    return () => spoken!;
  };

  it("kehrt erst zurück, wenn der Satz gesprochen ist", async () => {
    const spoken = stubSynthesis();
    let fertig = false;
    const ausgabe = speak("дом", voice("ru-RU")).then(() => {
      fertig = true;
    });
    await Promise.resolve();
    expect(fertig).toBe(false);

    spoken().onend!();
    await ausgabe;
    expect(fertig).toBe(true);
  });

  it("kehrt auch nach einem Abbruch zurück — sonst hinge das Gespräch", async () => {
    const spoken = stubSynthesis();
    const ausgabe = speak("дом", voice("ru-RU"));
    spoken().onerror!({ error: "interrupted" });
    await expect(ausgabe).resolves.toBeUndefined();
  });
});

