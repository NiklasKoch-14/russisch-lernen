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
 * Klang vor Tempo — eine bewusste Abwaegung, keine technische Notwendigkeit.
 *
 * Die lokalen Windows-Stimmen (`Microsoft Irina Desktop`) sind sofort da, aber
 * leise und blechern, und sie verschlucken den Anlaut kurzer Woerter. Die
 * Natural-Stimmen (`Microsoft Dmitry Online`) klingen deutlich besser, holen
 * jeden Satz aber aus dem Netz und setzen dadurch spuerbar spaeter ein.
 *
 * Nach `localService` zu sortieren statt nach dem Namen haelt das unabhaengig
 * von der Reihenfolge, in der der Browser seine Stimmen meldet.
 */
export function pickRussianVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  const russian = voices.filter(isRussian);
  const natural = russian.filter((voice) => !voice.localService);
  const best = (candidates: SpeechSynthesisVoice[]) =>
    candidates.find((voice) => voice.lang === "ru-RU") ?? candidates[0];
  return best(natural) ?? best(russian) ?? null;
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

/**
 * Folgen eines cancel(), nicht Fehler: Wir brechen jede laufende Ausgabe
 * absichtlich ab, bevor wir die naechste starten.
 */
const HARMLESS_ERRORS = new Set(["interrupted", "canceled", "cancelled"]);

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
  utterance.onerror = (event) => {
    const code = event.error ?? "unbekannt";
    if (HARMLESS_ERRORS.has(code)) return;
    onError?.(code);
  };
  speechSynthesis.speak(utterance);
}
