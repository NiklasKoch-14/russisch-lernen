import { useEffect, useRef } from "react";

import SpeakerButton from "../audio/SpeakerButton";
import { useSpeech } from "../audio/SpeechContext";
import { prefetchAudio } from "../audio/serverSpeech";

/**
 * Die Aufgabenstellung als Ton. Ohne russische Stimme fällt sie auf den
 * deutschen Prompt zurück — die Aufgabe bleibt dann die gewöhnliche Aufgabe.
 */
export default function AudioPrompt({ text, promptDe }: { text: string; promptDe: string }) {
  const { available, autoplay, say, source } = useSpeech();
  const played = useRef(false);

  useEffect(() => {
    // Beim Betreten schon holen, damit der spaetere Klick sofort spielt. Der
    // Browser legt die Datei wegen `immutable` selbst ab.
    if (source === "server") void prefetchAudio(text);
  }, [source, text]);

  useEffect(() => {
    // Einmal beim Betreten vorspielen. Browser blockieren das vor der ersten
    // Nutzergeste auf der Seite — dafuer gibt es den Lautsprecher.
    if (available && autoplay && !played.current) {
      played.current = true;
      say(text, { slow: false });
    }
  }, [available, autoplay, say, text]);

  if (!available) return <p className="text-lg">{promptDe}</p>;

  return (
    <div className="flex items-center gap-2">
      <SpeakerButton text={text} />
      <SpeakerButton text={text} slow label="Langsam anhören" />
      <span className="text-slate-500">Hör zu.</span>
    </div>
  );
}
