import { useCallback, useEffect, useRef, useState } from "react";

import { useSpeech } from "../audio/SpeechContext";
import { prefetchAudio } from "../audio/serverSpeech";
import type { ListeningLine, ListeningSpeaker } from "../courseTypes";

/**
 * Das Gespräch als Ton — beim ersten Durchlauf ohne jeden Text.
 *
 * Sichtbar ist nur, wer gerade spricht: das ist die Trennung, die beim Hören
 * hilft, ohne die Frage zu verraten. Abgespielt wird immer das ganze Gespräch;
 * einzelne Zeilen anzuspringen übt nichts.
 */
export default function DialogPlayer({
  speakers,
  lines,
  onFinished,
}: {
  speakers: ListeningSpeaker[];
  lines: ListeningLine[];
  /** Wird nach dem ersten vollständigen Durchlauf gerufen. */
  onFinished?: () => void;
}) {
  const { available, say, source } = useSpeech();
  const [position, setPosition] = useState<number | null>(null);
  const [slow, setSlow] = useState(false);
  // Läuft parallel zum State: die Schleife muss sofort sehen, dass abgebrochen
  // wurde, und nicht erst beim nächsten Rendern.
  const running = useRef(false);

  useEffect(() => {
    if (source !== "server") return;
    for (const line of lines) {
      void prefetchAudio(line.text, speakers[line.speaker]?.voice);
    }
  }, [lines, source, speakers]);

  useEffect(() => {
    // Beim Wechsel auf ein anderes Gespräch nicht weiterreden.
    return () => {
      running.current = false;
    };
  }, [lines]);

  const stop = useCallback(() => {
    running.current = false;
    setPosition(null);
  }, []);

  const play = useCallback(async () => {
    if (running.current) return;
    running.current = true;
    for (let index = 0; index < lines.length; index += 1) {
      if (!running.current) return;
      setPosition(index);
      await say(lines[index].text, { slow, voice: speakers[lines[index].speaker]?.voice });
    }
    running.current = false;
    setPosition(null);
    onFinished?.();
  }, [lines, onFinished, say, slow, speakers]);

  if (!available) {
    return (
      <p className="text-slate-600">
        Ohne russische Stimme lässt sich das Gespräch nicht anhören — lies es unten mit.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {speakers.map((speaker, index) => (
          <span
            key={speaker.name_ru}
            className={`rounded-full border px-3 py-1 text-sm transition ${
              position !== null && lines[position]?.speaker === index
                ? "border-sky-500 bg-sky-50 font-medium text-sky-800"
                : "border-slate-300 text-slate-600"
            }`}
          >
            <span lang="ru">{speaker.name_ru}</span>
          </span>
        ))}
        <span className="text-sm text-slate-500">
          {speakers.length} Sprecher · {lines.length} Zeilen
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => void play()}
          disabled={position !== null}
          className="rounded-xl border-2 border-slate-300 bg-white px-4 py-2 transition hover:border-sky-400 disabled:opacity-60"
        >
          {position === null ? "▶ Abspielen" : "läuft …"}
        </button>
        <button
          type="button"
          onClick={stop}
          disabled={position === null}
          className="rounded-xl border-2 border-slate-300 bg-white px-4 py-2 transition hover:border-sky-400 disabled:opacity-60"
        >
          ⏸ Pause
        </button>
        <label className="flex items-center gap-2 text-slate-600">
          <input type="checkbox" checked={slow} onChange={(event) => setSlow(event.target.checked)} />
          langsam
        </label>
      </div>
    </div>
  );
}
