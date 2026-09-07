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

/**
 * Standard für die ganze Suite: keine russische Stimme. Damit sind alle Tests,
 * die nichts mit Ton zu tun haben, vom Klang der Maschine unabhaengig und sehen
 * durchgaengig die Textfassung der Aufgaben.
 */
export const test = base.extend({
  page: async ({ page }, use) => {
    await stubSpeech(page, ["de-DE"]);
    await use(page);
  },
});

export { expect } from "@playwright/test";
