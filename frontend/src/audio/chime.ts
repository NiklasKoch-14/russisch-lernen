/**
 * Der kleine Zweiklang nach einer richtigen Antwort.
 *
 * Der Browser erzeugt ihn selbst über Web Audio: keine Tondatei, keine
 * Lizenzfrage, offline verfügbar, und das Backend bleibt außen vor. Zwei kurze
 * Sinustöne aufwärts (eine Quinte), leise und mit weichem Ausklang — hörbar
 * genug als Bestätigung, zu kurz, um das Vorlesen zu stören.
 *
 * Bei falschen Antworten gibt es bewusst keinen Ton: Fehler gehören zum Lernen,
 * ein Summer würde sie bestrafen.
 */

/** Frequenz in Hz und Einsatz in Sekunden nach dem Start. */
export const CHIME_NOTES: ReadonlyArray<readonly [number, number]> = [
  [880, 0], // a''
  [1318.5, 0.09], // e'''
];

const VOLUME = 0.15;
const NOTE_SECONDS = 0.28;
const SILENT = 0.0001; // exponentialRamp darf nicht bei 0 anfangen oder enden

type AudioContextClass = typeof AudioContext;

let context: AudioContext | null = null;

function audioContextClass(): AudioContextClass | undefined {
  const scope = window as unknown as {
    AudioContext?: AudioContextClass;
    webkitAudioContext?: AudioContextClass;
  };
  return scope.AudioContext ?? scope.webkitAudioContext;
}

/** Spielt den Zweiklang. Ohne Web Audio bleibt es still — nichts anderes hängt davon ab. */
export function playChime(): void {
  const Context = audioContextClass();
  if (!Context) return;
  try {
    // Ein Kontext für die ganze Sitzung: Browser begrenzen, wie viele offen sein
    // dürfen. Angelegt wird er erst beim ersten Klang, also nach einem Klick —
    // vorher würde ihn die Autoplay-Sperre der Browser stumm halten.
    context ??= new Context();
    if (context.state === "suspended") void context.resume();

    const start = context.currentTime;
    const master = context.createGain();
    master.gain.value = VOLUME;
    master.connect(context.destination);

    for (const [frequency, offset] of CHIME_NOTES) {
      const at = start + offset;
      const oscillator = context.createOscillator();
      const envelope = context.createGain();
      oscillator.type = "sine";
      oscillator.frequency.value = frequency;
      envelope.gain.setValueAtTime(SILENT, at);
      envelope.gain.exponentialRampToValueAtTime(1, at + 0.01);
      envelope.gain.exponentialRampToValueAtTime(SILENT, at + NOTE_SECONDS);
      oscillator.connect(envelope);
      envelope.connect(master);
      oscillator.start(at);
      oscillator.stop(at + NOTE_SECONDS + 0.02);
    }
  } catch {
    // Ein Klang, der nicht klappt, ist kein Fehler, den jemand sehen muss.
  }
}
