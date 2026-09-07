/**
 * Sprachausgabe über die Stimmen des Browsers. Bewusst ohne React, damit die
 * kniffligen Teile — Betonungszeichen und das späte Eintreffen der Stimmen —
 * für sich testbar bleiben.
 */

/** Kombinierendes Akut. Steht im Content zur Betonung, verwirrt aber manche Stimmen. */
const COMBINING_ACUTE = /\u0301/g;

export const NORMAL_RATE = 1;
/** Fuer den Lupen-Knopf. Bei Vokalreduktion hilft langsam, im Alltag stoert es. */
export const SLOW_RATE = 0.6;

export function stripStress(text: string): string {
  return text.replace(COMBINING_ACUTE, "");
}

const isRussian = (voice: SpeechSynthesisVoice) => voice.lang.toLowerCase().startsWith("ru");

/**
 * Lokale Stimmen zuerst. Online-Stimmen wie „Microsoft Dmitry Online (Natural)"
 * schicken den Text an einen Server: sie setzen verzoegert ein und stocken
 * mitten im Satz. Erst danach zaehlt die genauere Sprachkennung.
 */
export function pickRussianVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  const russian = voices.filter(isRussian);
  const local = russian.filter((voice) => voice.localService);
  // Lokal schlaegt die genauere Sprachkennung: eine lokale ru-Stimme ist besser
  // als eine ru-RU-Stimme, die jeden Satz erst aus dem Netz holt.
  const best = (candidates: SpeechSynthesisVoice[]) =>
    candidates.find((voice) => voice.lang === "ru-RU") ?? candidates[0];
  return best(local) ?? best(russian) ?? null;
}

/** getVoices() ist beim ersten Aufruf oft leer; die Liste kommt erst mit voiceschanged. */
export function loadVoices(): Promise<SpeechSynthesisVoice[]> {
  if (typeof speechSynthesis === "undefined") return Promise.resolve([]);

  const immediate = speechSynthesis.getVoices();
  if (immediate.length > 0) return Promise.resolve(immediate);

  return new Promise((resolve) => {
    const onChange = () => {
      speechSynthesis.removeEventListener("voiceschanged", onChange);
      resolve(speechSynthesis.getVoices());
    };
    speechSynthesis.addEventListener("voiceschanged", onChange);
  });
}

export function speak(
  text: string,
  voice: SpeechSynthesisVoice,
  rate: number = NORMAL_RATE,
  onError?: (code: string) => void,
): void {
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(stripStress(text));
  utterance.voice = voice;
  utterance.lang = voice.lang;
  utterance.rate = rate;
  utterance.onerror = (event) => onError?.(event.error ?? "unbekannt");
  speechSynthesis.speak(utterance);
}
