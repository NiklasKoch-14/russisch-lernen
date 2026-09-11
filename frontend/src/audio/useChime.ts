import { useCallback } from "react";

import { playChime } from "./chime";
import { useSpeech } from "./SpeechContext";

/**
 * Der Richtig-Klang, sofern der Ton-Schalter in der Kopfzeile an ist.
 *
 * Ein Schalter für beides — Vorlesen und Klänge —, damit „App ist still" ein
 * einziger Griff bleibt, etwa im Zug.
 */
export function useChime(): () => void {
  const { autoplay } = useSpeech();
  return useCallback(() => {
    if (autoplay) playChime();
  }, [autoplay]);
}
