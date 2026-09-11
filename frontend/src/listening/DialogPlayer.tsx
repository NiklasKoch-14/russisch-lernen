import { useCallback, useEffect, useRef, useState } from "react";

import { useSpeech } from "../audio/SpeechContext";
import { SLOW_PLAYBACK_RATE, stopAudio } from "../audio/serverSpeech";
import type { ListeningLine, ListeningSpeaker } from "../courseTypes";
import { loadDialogTrack } from "../listeningApi";

/**
 * Das Gespräch als Ton — beim ersten Durchlauf ohne jeden Text.
 *
 * Mit Piper kommt es als **eine** Tonspur, vorab ganz geladen: nichts reißt
 * ab, die Länge steht fest, und ein Balken zeigt, wie lange es noch dauert.
 * Wer gerade spricht, verraten die Startzeiten der Zeilen — mehr nicht, sonst
 * wäre die Frage keine Hörfrage mehr.
 *
 * Ohne Tonspur (Piper aus, nur Browserstimme) läuft es Zeile für Zeile, und
 * jede Zeile wartet, bis die vorige gesprochen ist. Früher brach jede die
 * vorige ab, und nur die letzte war zu hören.
 */

interface Track {
  url: string;
  starts: number[];
}

/** 75 → "1:15" */
function clock(seconds: number): string {
  const whole = Math.max(0, Math.ceil(seconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

const BUTTON =
  "rounded-xl border-2 border-slate-300 bg-white px-4 py-2 transition hover:border-sky-400 disabled:opacity-60";

export default function DialogPlayer({
  dialogId,
  speakers,
  lines,
  onFinished,
}: {
  dialogId: number;
  speakers: ListeningSpeaker[];
  lines: ListeningLine[];
  /** Wird nach jedem vollständigen Durchlauf gerufen. */
  onFinished?: () => void;
}) {
  const { available, say, source } = useSpeech();
  const [slow, setSlow] = useState(false);
  const finished = useRef(onFinished);
  finished.current = onFinished;

  // --- Tonspur ------------------------------------------------------------
  const [track, setTrack] = useState<Track | null>(null);
  const [trackFailed, setTrackFailed] = useState(false);
  const audio = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [ended, setEnded] = useState(false);
  const [time, setTime] = useState(0);
  const [duration, setDuration] = useState(0);

  const withTrack = source === "server" && !trackFailed;

  useEffect(() => {
    if (source !== "server") return;
    let cancelled = false;
    let element: HTMLAudioElement | null = null;
    let url: string | null = null;
    setTrack(null);
    setTrackFailed(false);
    setPlaying(false);
    setEnded(false);
    setTime(0);
    setDuration(0);

    loadDialogTrack(dialogId)
      .then((loaded) => {
        url = loaded.url;
        if (cancelled) {
          URL.revokeObjectURL(loaded.url);
          return;
        }
        element = new Audio(loaded.url);
        // Ohne preservesPitch klingt langsames Abspielen tiefer statt langsamer.
        element.preservesPitch = true;
        const current = element;
        current.addEventListener("loadedmetadata", () => setDuration(current.duration));
        current.addEventListener("timeupdate", () => setTime(current.currentTime));
        current.addEventListener("play", () => {
          setPlaying(true);
          setEnded(false);
        });
        current.addEventListener("pause", () => setPlaying(false));
        current.addEventListener("ended", () => {
          setPlaying(false);
          setEnded(true);
          finished.current?.();
        });
        audio.current = current;
        setTrack(loaded);
      })
      .catch(() => {
        if (!cancelled) setTrackFailed(true);
      });

    return () => {
      cancelled = true;
      element?.pause();
      audio.current = null;
      if (url) URL.revokeObjectURL(url);
    };
  }, [dialogId, source]);

  useEffect(() => {
    if (audio.current) audio.current.playbackRate = slow ? SLOW_PLAYBACK_RATE : 1;
  }, [slow, track]);

  const toggleTrack = () => {
    const element = audio.current;
    if (!element) return;
    if (playing) {
      element.pause();
      return;
    }
    // Andere Ausgaben (Vorlesen, Lautsprecherknopf) nicht darüberlegen.
    stopAudio();
    if (ended) element.currentTime = 0;
    element.play().catch(() => setTrackFailed(true));
  };

  // --- Zeile für Zeile (Rückfall) -------------------------------------------
  const [position, setPosition] = useState<number | null>(null);
  // Läuft parallel zum State: die Schleife muss sofort sehen, dass abgebrochen
  // wurde, und nicht erst beim nächsten Rendern.
  const running = useRef(false);

  useEffect(() => {
    // Beim Wechsel auf ein anderes Gespräch nicht weiterreden.
    return () => {
      running.current = false;
    };
  }, [lines]);

  const playLines = useCallback(async () => {
    if (running.current) {
      // Hält nach der laufenden Zeile an — die Browserstimme lässt sich nicht
      // mitten im Satz pausieren.
      running.current = false;
      return;
    }
    running.current = true;
    for (let index = 0; index < lines.length; index += 1) {
      if (!running.current) {
        setPosition(null);
        return;
      }
      setPosition(index);
      await say(lines[index].text, { slow, voice: speakers[lines[index].speaker]?.voice });
    }
    running.current = false;
    setPosition(null);
    finished.current?.();
  }, [lines, say, slow, speakers]);

  if (!available) {
    return (
      <p className="text-slate-600">
        Ohne russische Stimme lässt sich das Gespräch nicht anhören — lies es unten mit.
      </p>
    );
  }

  // Wer gerade spricht: mit Spur aus den Startzeiten, sonst die laufende Zeile.
  let speaking: number | null = null;
  if (withTrack && track && playing) {
    const line = track.starts.reduce((found, start, index) => (start <= time ? index : found), 0);
    speaking = lines[line]?.speaker ?? null;
  } else if (!withTrack && position !== null) {
    speaking = lines[position]?.speaker ?? null;
  }

  let progress = 0;
  let label = "";
  if (withTrack) {
    const rate = slow ? SLOW_PLAYBACK_RATE : 1;
    progress = duration > 0 ? Math.min(1, time / duration) : 0;
    label = duration > 0 ? `noch ${clock((duration - time) / rate)}` : "";
  } else if (position !== null) {
    progress = position / lines.length;
    label = `Zeile ${position + 1} von ${lines.length}`;
  }

  let button: string;
  if (withTrack) {
    if (!track) button = "Gespräch wird geladen …";
    else if (playing) button = "⏸ Pause";
    else if (ended) button = "▶ Nochmal";
    else if (time > 0) button = "▶ Weiter";
    else button = "▶ Abspielen";
  } else {
    button = position === null ? "▶ Abspielen" : "⏸ Pause";
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {speakers.map((speaker, index) => (
          <span
            key={speaker.name_ru}
            aria-current={speaking === index ? "true" : undefined}
            className={`rounded-full border px-3 py-1 text-sm transition ${
              speaking === index
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

      <div className="flex items-center gap-3">
        <div
          role="progressbar"
          aria-label="Fortschritt des Gesprächs"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(progress * 100)}
          className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200"
        >
          <div
            className="h-full rounded-full bg-sky-500 transition-[width] duration-200"
            style={{ width: `${progress * 100}%` }}
          />
        </div>
        <span className="w-28 shrink-0 text-right text-sm tabular-nums text-slate-500">
          {label}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={withTrack ? toggleTrack : () => void playLines()}
          disabled={withTrack && !track}
          className={BUTTON}
        >
          {button}
        </button>
        <label className="flex items-center gap-2 text-slate-600">
          <input type="checkbox" checked={slow} onChange={(event) => setSlow(event.target.checked)} />
          langsam
        </label>
      </div>
    </div>
  );
}
