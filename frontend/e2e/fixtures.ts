import { test as base } from "@playwright/test";
import type { Page } from "@playwright/test";

/**
 * Ersetzt die Sprachausgabe durch eine Attrappe, die mitschreibt statt zu sprechen.
 *
 * Ohne das haengen die Tests davon ab, welche Stimmen auf der Maschine zufaellig
 * installiert sind: mit russischer Stimme verschwinden die deutschen Prompts der
 * Hoer-Aufgaben, ohne bleiben sie stehen. Beides ist richtig — aber nur eines
 * davon ist testbar.
 */
export async function stubSpeech(page: Page, langs: string[]): Promise<void> {
  await page.addInitScript((available: string[]) => {
    const spoken: string[] = [];
    (window as unknown as { __spoken: string[] }).__spoken = spoken;

    class FakeUtterance {
      text: string;
      lang = "";
      rate = 1;
      voice: unknown = null;
      constructor(text: string) {
        this.text = text;
      }
    }

    Object.defineProperty(window, "SpeechSynthesisUtterance", {
      configurable: true,
      value: FakeUtterance,
    });
    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: {
        getVoices: () => available.map((lang) => ({ lang, name: lang })),
        addEventListener: () => {},
        removeEventListener: () => {},
        cancel: () => {},
        speak: (utterance: { text: string }) => spoken.push(utterance.text),
      },
    });
  }, langs);
}

/** Was die Seite bisher zu sprechen versucht hat. */
export function spokenTexts(page: Page): Promise<string[]> {
  return page.evaluate(() => (window as unknown as { __spoken: string[] }).__spoken ?? []);
}

/** Eine gueltige, sehr kurze WAV-Datei — 44 Byte Kopf, keine Samples. */
const TINY_WAV = Buffer.from(
  "UklGRiQAAABXQVZFZm10IBAAAAABAAEAIlYAAESsAAACABAAZGF0YQAAAAA=",
  "base64",
);

/**
 * Faengt den Audio-Endpunkt ab. Der tts-Container laeuft in e2e-Laeufen nicht;
 * ohne das ginge jeder Tonabruf ins Leere.
 */
export async function stubServerAudio(page: Page, available: boolean): Promise<void> {
  await page.route("**/api/audio/health", (route) => route.fulfill({ json: { available } }));
  await page.route("**/api/audio?*", (route) =>
    available
      ? route.fulfill({ body: TINY_WAV, contentType: "audio/wav" })
      : route.fulfill({ status: 503, json: { detail: "Sprachdienst nicht erreichbar" } }),
  );
}

/**
 * Standard für die ganze Suite: keine russische Stimme. Damit sind alle Tests,
 * die nichts mit Ton zu tun haben, vom Klang der Maschine unabhaengig und sehen
 * durchgaengig die Textfassung der Aufgaben.
 */
export const test = base.extend({
  page: async ({ page }, use) => {
    // Standard: kein Serverton, keine russische Browserstimme. Damit bleiben
    // alle Laeufe, die nichts mit Ton zu tun haben, auf der Textfassung.
    await stubServerAudio(page, false);
    await stubSpeech(page, ["de-DE"]);
    await use(page);
  },
});

export { expect } from "@playwright/test";
