import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

import { getProfile, patchProfile } from "../courseApi";
import { NORMAL_RATE, SLOW_RATE, loadVoices, pickRussianVoice, speak } from "./speech";

interface SpeechValue {
  /** null, solange die Stimmen des Browsers noch geladen werden. */
  available: boolean | null;
  autoplay: boolean;
  setAutoplay: (value: boolean) => void;
  say: (text: string, options?: { slow?: boolean }) => void;
}

const SpeechContext = createContext<SpeechValue>({
  available: false,
  autoplay: true,
  setAutoplay: () => {},
  say: () => {},
});

export function useSpeech(): SpeechValue {
  return useContext(SpeechContext);
}

export function SpeechProvider({ children }: { children: ReactNode }) {
  const [voice, setVoice] = useState<SpeechSynthesisVoice | null>(null);
  const [available, setAvailable] = useState<boolean | null>(null);
  const [autoplay, setAutoplayState] = useState(true);

  useEffect(() => {
    let cancelled = false;
    loadVoices().then((voices) => {
      if (cancelled) return;
      const found = pickRussianVoice(voices);
      setVoice(found);
      setAvailable(found !== null);
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

  const setAutoplay = (value: boolean) => {
    setAutoplayState(value);
    patchProfile({ audio_autoplay: value }).catch(() => {});
  };

  const say = (text: string, options?: { slow?: boolean }) => {
    if (!voice) return;
    speak(text, voice, options?.slow ? SLOW_RATE : NORMAL_RATE);
  };

  return (
    <SpeechContext.Provider value={{ available, autoplay, setAutoplay, say }}>
      {children}
    </SpeechContext.Provider>
  );
}
