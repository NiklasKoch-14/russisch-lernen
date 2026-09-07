/**
 * Ton vom eigenen Server (Piper).
 *
 * Die URL ist inhaltsbestimmt und die Antwort traegt `immutable` — deshalb legt
 * der Browser die Datei ohnehin ab. Trotzdem laden wir sie hier selbst und
 * spielen aus einem fertigen Blob: ein `<audio src=url>` beginnt sonst zu
 * spielen, bevor die Datei vollstaendig ist, und schneidet beim allerersten Mal
 * das erste Wort ab.
 */

import { API_BASE_URL } from "../api";

export const SLOW_PLAYBACK_RATE = 0.6;

/** Hoechstens so viele Saetze im Speicher halten. Ein Satz sind ~50 KB. */
const MAX_CACHED = 40;

/** Laufende und fertige Abrufe. Verhindert, dass Vorladen und Abspielen
 *  denselben Satz zweimal holen — genau das verursachte das Abschneiden. */
const pending = new Map<string, Promise<Blob>>();

/**
 * Wirft die geladenen Toene weg. Gebraucht in Tests, und wenn sich die Stimme
 * serverseitig aendert: die URL bleibt dann gleich, der Inhalt nicht.
 */
export function clearAudioCache(): void {
  pending.clear();
}

export function audioUrl(text: string): string {
  return `${API_BASE_URL}/api/audio?text=${encodeURIComponent(text)}`;
}

function loadAudio(text: string): Promise<Blob> {
  const url = audioUrl(text);
  const known = pending.get(url);
  if (known) return known;

  const request = fetch(url).then(async (response) => {
    if (!response.ok) throw new Error(`Ton nicht verfügbar: ${response.status}`);
    return response.blob();
  });

  request.catch(() => pending.delete(url));
  pending.set(url, request);

  if (pending.size > MAX_CACHED) {
    const oldest = pending.keys().next().value;
    if (oldest !== undefined) pending.delete(oldest);
  }
  return request;
}

/** Waermt den Speicher. Fehler sind hier bedeutungslos. */
export async function prefetchAudio(text: string): Promise<void> {
  try {
    await loadAudio(text);
  } catch {
    // Vorladen ist Kuer — der Klick holt die Datei sonst eben selbst.
  }
}

export async function playAudio(text: string, options?: { slow?: boolean }): Promise<void> {
  const blob = await loadAudio(text);
  const objectUrl = URL.createObjectURL(blob);

  const audio = new Audio(objectUrl);
  // Ohne preservesPitch klingt langsames Abspielen tiefer statt langsamer.
  audio.preservesPitch = true;
  audio.playbackRate = options?.slow ? SLOW_PLAYBACK_RATE : 1;

  const release = () => URL.revokeObjectURL(objectUrl);
  audio.addEventListener("ended", release);
  audio.addEventListener("error", release);

  try {
    await audio.play();
  } catch (error) {
    release();
    throw error;
  }
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
