/**
 * Ton vom eigenen Server (Piper).
 *
 * Die URL ist inhaltsbestimmt und die Antwort traegt `immutable` — deshalb legt
 * der Browser die Datei selbst ab, und das Vorladen ist fast geschenkt: ein
 * `fetch` beim Betreten der Aufgabe, und der spaetere Klick spielt sofort.
 */

import { API_BASE_URL } from "../api";

export const SLOW_PLAYBACK_RATE = 0.6;

export function audioUrl(text: string): string {
  return `${API_BASE_URL}/api/audio?text=${encodeURIComponent(text)}`;
}

/** Waermt den Zwischenspeicher des Browsers. Fehler sind hier bedeutungslos. */
export async function prefetchAudio(text: string): Promise<void> {
  try {
    await fetch(audioUrl(text));
  } catch {
    // Vorladen ist Kuer, nicht Pflicht — der Klick holt die Datei sonst eben selbst.
  }
}

export async function playAudio(text: string, options?: { slow?: boolean }): Promise<void> {
  const audio = new Audio(audioUrl(text));
  // Ohne preservesPitch klingt langsames Abspielen tiefer statt langsamer.
  audio.preservesPitch = true;
  audio.playbackRate = options?.slow ? SLOW_PLAYBACK_RATE : 1;
  await audio.play();
}

export async function serverAudioAvailable(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/audio/health`);
    if (!response.ok) return false;
    const body = (await response.json()) as { available?: boolean };
    return body.available === true;
  } catch {
    return false;
  }
}
