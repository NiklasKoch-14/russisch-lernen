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

/** Was gerade spielt. Ohne das ueberlagern sich Autoplay und Lautsprecherklick. */
let playing: HTMLAudioElement | null = null;

/**
 * Wirft die geladenen Toene weg. Gebraucht in Tests, und wenn sich die Stimme
 * serverseitig aendert: die URL bleibt dann gleich, der Inhalt nicht.
 */
export function clearAudioCache(): void {
  pending.clear();
}

/** Bricht eine laufende Ausgabe ab — Gegenstueck zu speechSynthesis.cancel(). */
export function stopAudio(): void {
  if (!playing) return;
  playing.pause();
  playing.currentTime = 0;
  playing = null;
}

/** Welche Figur spricht. Das Modell dahinter kennt nur der Server. */
export type Voice = "m" | "f";

export function audioUrl(text: string, voice?: Voice): string {
  const base = `${API_BASE_URL}/api/audio?text=${encodeURIComponent(text)}`;
  // Ohne Angabe bleibt die Adresse, wie sie war: der Browser hat den Ton der
  // Einzelsaetze schon abgelegt, und `immutable` gilt je Adresse.
  return voice ? `${base}&voice=${voice}` : base;
}

function loadAudio(text: string, voice?: Voice): Promise<Blob> {
  const url = audioUrl(text, voice);
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
export async function prefetchAudio(text: string, voice?: Voice): Promise<void> {
  try {
    await loadAudio(text, voice);
  } catch {
    // Vorladen ist Kuer — der Klick holt die Datei sonst eben selbst.
  }
}

/**
 * Spielt einen Satz und kehrt zurück, wenn er zu Ende ist — oder abgebrochen
 * wurde. Früher meldete sie sich schon beim Start (so hält es `audio.play()`);
 * wer Zeilen nacheinander abspielte, brach damit jede durch die nächste ab.
 */
export async function playAudio(
  text: string,
  options?: { slow?: boolean; voice?: Voice },
): Promise<void> {
  // Vor dem Laden abbrechen: sonst laeuft die alte Ausgabe waehrend des
  // Abrufs weiter und die neue setzt sich darueber.
  stopAudio();
  const blob = await loadAudio(text, options?.voice);
  const objectUrl = URL.createObjectURL(blob);

  const audio = new Audio(objectUrl);
  // Ohne preservesPitch klingt langsames Abspielen tiefer statt langsamer.
  audio.preservesPitch = true;
  audio.playbackRate = options?.slow ? SLOW_PLAYBACK_RATE : 1;

  const release = () => {
    URL.revokeObjectURL(objectUrl);
    if (playing === audio) playing = null;
  };
  audio.addEventListener("ended", release);
  audio.addEventListener("error", release);

  // Auch ein Abbruch beendet den Satz — sonst wartete, wer auf ihn wartet, ewig.
  const finished = new Promise<void>((resolve) => {
    for (const type of ["ended", "pause", "error"]) {
      audio.addEventListener(type, () => resolve());
    }
  });

  stopAudio();
  playing = audio;

  try {
    await audio.play();
  } catch (error) {
    release();
    throw error;
  }
  await finished;
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
