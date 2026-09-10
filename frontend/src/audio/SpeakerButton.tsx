import type { Voice } from "./serverSpeech";
import { useSpeech } from "./SpeechContext";

/**
 * Der einzige Weg, im Kurs Ton auszulösen. Ohne russische Stimme rendert er
 * nichts — Aufrufer brauchen deshalb keine eigene Bedingung.
 */
export default function SpeakerButton({
  text,
  label = "Anhören",
  slow = false,
  voice,
}: {
  text: string;
  label?: string;
  slow?: boolean;
  /** Welche Figur spricht — ohne Angabe die Vorgabestimme. */
  voice?: Voice;
}) {
  const { available, say } = useSpeech();
  if (!available) return null;

  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={() => say(text, { slow, voice })}
      className="rounded-full border border-slate-300 px-2 py-1 text-slate-600 transition hover:border-sky-400 hover:text-sky-700"
    >
      {slow ? "🐢" : "🔊"}
    </button>
  );
}
