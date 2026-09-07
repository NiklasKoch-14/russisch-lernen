import { useSpeech } from "./SpeechContext";

/**
 * Sitzt in der Kopfzeile, weil man ihn situativ braucht: im Zug still lernen,
 * zu Hause mit Ton. Er steuert nur das automatische Abspielen — Hör-Aufgaben
 * bleiben Hör-Aufgaben und lassen sich weiter über den Lautsprecher anhören.
 */
export default function AutoplayToggle() {
  const { available, autoplay, setAutoplay } = useSpeech();
  const label = autoplay
    ? "Automatisches Vorlesen ausschalten"
    : "Automatisches Vorlesen einschalten";

  return (
    <button
      type="button"
      // role=switch statt aria-pressed: es ist ein An/Aus-Schalter, und
      // aria-pressed gehoert im Kurs den Wortkacheln.
      role="switch"
      aria-label={label}
      aria-checked={autoplay}
      title={available ? label : "Keine russische Stimme gefunden"}
      disabled={!available}
      onClick={() => setAutoplay(!autoplay)}
      className="rounded-full border border-slate-300 px-2 py-1 transition hover:border-sky-400 disabled:opacity-40"
    >
      {autoplay ? "🔊" : "🔇"}
    </button>
  );
}
