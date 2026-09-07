import { afterEach, describe, expect, it, vi } from "vitest";

import { NORMAL_RATE, SLOW_RATE, loadVoices, pickRussianVoice, speak, stripStress } from "./speech";

const voice = (lang: string) => ({ lang, name: lang }) as SpeechSynthesisVoice;

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
    let handler: (() => void) | null = null;
    let voices: SpeechSynthesisVoice[] = [];
    vi.stubGlobal("speechSynthesis", {
      getVoices: () => voices,
      addEventListener: (_: string, callback: () => void) => {
        handler = callback;
      },
      removeEventListener: () => {},
    });

    const pending = loadVoices();
    voices = [voice("ru-RU")];
    handler?.();

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

  it("benutzt das normale Tempo als Standard", () => {
    const speakSpy = vi.fn();
    vi.stubGlobal("speechSynthesis", { cancel: vi.fn(), speak: speakSpy, getVoices: () => [] });
    vi.stubGlobal("SpeechSynthesisUtterance", FakeUtterance);

    speak("дом", voice("ru-RU"));

    expect(speakSpy.mock.calls[0][0].rate).toBe(NORMAL_RATE);
  });
});
