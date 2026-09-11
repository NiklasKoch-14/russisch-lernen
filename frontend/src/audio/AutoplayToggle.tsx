import { useSpeech } from "./SpeechContext";

/**
 * Sitzt in der Kopfzeile, weil man ihn situativ braucht: im Zug still lernen,
 * zu Hause mit Ton. Er steuert das automatische Vorlesen und den Richtig-Klang
 * zusammen — „App ist still" soll ein einziger Griff sein. Hör-Aufgaben
 * bleiben Hör-Aufgaben und lassen sich weiter über den Lautsprecher anhören.
 *
 * Gesperrt wird er nie: den Klang erzeugt der Browser selbst, auch wenn keine
 * russische Stimme da ist — dann muss er sich trotzdem abschalten lassen.
 */
export default function AutoplayToggle() {
  const { available, autoplay, setAutoplay } = useSpeech();
  const label = autoplay ? "Ton ausschalten" : "Ton einschalten";
  const title = available
    ? `${label} — Vorlesen und Klänge`
    : `${label} — Keine russische Stimme gefunden, es geht nur um die Klänge`;

  return (
    <button
      type="button"
      // role=switch statt aria-pressed: es ist ein An/Aus-Schalter, und
      // aria-pressed gehoert im Kurs den Wortkacheln.
      role="switch"
      aria-label={label}
      aria-checked={autoplay}
      title={title}
      onClick={() => setAutoplay(!autoplay)}
      className="rounded-full border border-slate-300 px-2 py-1 transition hover:border-sky-400"
    >
      {autoplay ? "🔊" : "🔇"}
    </button>
  );
}
