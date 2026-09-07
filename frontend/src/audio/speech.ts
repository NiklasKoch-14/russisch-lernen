/**
 * Sprachausgabe über die Stimmen des Browsers. Bewusst ohne React, damit die
 * kniffligen Teile — Betonungszeichen und das späte Eintreffen der Stimmen —
 * für sich testbar bleiben.
 */

/** Kombinierendes Akut. Steht im Content zur Betonung, verwirrt aber manche Stimmen. */
const COMBINING_ACUTE = "́";

/** Etwas langsamer als normal — bei russischer Vokalreduktion hört man sonst zu wenig. */
export const NORMAL_RATE = 0.85;
export const SLOW_RATE = 0.6;

export function stripStress(text: string): string {
  return text.replaceAll(COMBINING_ACUTE, "");
}

export function pickRussianVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  return (
    voices.find((voice) => voice.lang === "ru-RU") ??
    voices.find((voice) => voice.lang.toLowerCase().startsWith("ru")) ??
    null
  );
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
): void {
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(stripStress(text));
  utterance.voice = voice;
  utterance.lang = voice.lang;
  utterance.rate = rate;
  speechSynthesis.speak(utterance);
}
