import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { getProfile, patchProfile } from "../courseApi";
import type { Voice } from "./serverSpeech";
import { playAudio, serverAudioAvailable } from "./serverSpeech";
import { NORMAL_RATE, SLOW_RATE, loadVoices, pickRussianVoice, speak } from "./speech";

/** Woher der Ton kommt. `none` heisst: Hoer-Aufgaben zeigen ihre Textfassung. */
export type SpeechSource = "server" | "browser" | "none";

interface SpeechValue {
  /** null, solange Server und Stimmen noch geprueft werden. */
  available: boolean | null;
  source: SpeechSource;
  autoplay: boolean;
  setAutoplay: (value: boolean) => void;
  /** `voice` waehlt die Figur; ohne Server spricht dieselbe Browserstimme alle Rollen.
   *  Kehrt zurueck, wenn der Satz zu Ende ist oder abgebrochen wurde. */
  say: (text: string, options?: { slow?: boolean; voice?: Voice }) => Promise<void>;
  /** Fehlercode der letzten Sprachausgabe, sonst null. */
  lastError: string | null;
  /** Welche Stimme tatsaechlich spricht — `local: false` heisst: aus dem Netz. */
  activeVoice: { name: string; lang: string; local: boolean } | null;
}

const SpeechContext = createContext<SpeechValue>({
  available: false,
  source: "none",
  autoplay: true,
  setAutoplay: () => {},
  say: async () => {},
  lastError: null,
  activeVoice: null,
});

export function useSpeech(): SpeechValue {
  return useContext(SpeechContext);
}

export function SpeechProvider({ children }: { children: ReactNode }) {
  const [voice, setVoice] = useState<SpeechSynthesisVoice | null>(null);
  const [voicesChecked, setVoicesChecked] = useState(false);
  const [serverOk, setServerOk] = useState<boolean | null>(null);
  const [autoplay, setAutoplayState] = useState(true);
  const [lastError, setLastError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    serverAudioAvailable().then((ok) => {
      if (!cancelled) setServerOk(ok);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    loadVoices().then((voices) => {
      if (cancelled) return;
      setVoice(pickRussianVoice(voices));
      setVoicesChecked(true);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    getProfile()
      .then((profile) => setAutoplayState(profile.audio_autoplay))
      .catch(() => setAutoplayState(true));
  }, []);

  const source: SpeechSource = serverOk ? "server" : voice ? "browser" : "none";

  // Erst urteilen, wenn beide Quellen geprueft sind — sonst blitzt kurz die
  // Textfassung auf, bevor der Ton da ist.
  const settled = serverOk !== null && voicesChecked;
  const available = settled ? source !== "none" : null;

  const setAutoplay = useCallback((value: boolean) => {
    setAutoplayState(value);
    patchProfile({ audio_autoplay: value }).catch(() => {});
  }, []);

  const say = useCallback(
    async (text: string, options?: { slow?: boolean; voice?: Voice }) => {
      // Nur zuruecksetzen, wenn wirklich ein Fehler steht — sonst rendert jeder
      // Lautsprecherklick die ganze App neu.
      setLastError((previous) => (previous === null ? previous : null));

      if (serverOk) {
        try {
          await playAudio(text, { slow: options?.slow ?? false, voice: options?.voice });
          return;
        } catch {
          // Einmal als tot erkannt, nicht bei jedem Klick erneut probieren.
          setServerOk(false);
        }
      }

      if (!voice) return;
      await speak(text, voice, options?.slow ? SLOW_RATE : NORMAL_RATE, setLastError);
    },
    [serverOk, voice],
  );

  const activeVoice = useMemo(() => {
    if (source === "server") return { name: "Piper", lang: "ru-RU", local: true };
    return voice ? { name: voice.name, lang: voice.lang, local: voice.localService } : null;
  }, [source, voice]);

  const value = useMemo(
    () => ({ available, source, autoplay, setAutoplay, say, lastError, activeVoice }),
    [available, source, autoplay, setAutoplay, say, lastError, activeVoice],
  );

  return <SpeechContext.Provider value={value}>{children}</SpeechContext.Provider>;
}
