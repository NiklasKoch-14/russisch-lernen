import { useCallback, useEffect, useRef, useState } from "react";

/** So lange muss die Maus stillhalten, bis die Aussprache erscheint. */
export const REVEAL_DELAY_MS = 1000;

/**
 * Erst nach diesem Anteil der Wartezeit taucht der Ladekreis auf. Beim blossen
 * Vorbeifahren soll nichts aufblitzen.
 */
export const RING_START_FRACTION = 1 / 3;
export const RING_DELAY_MS = Math.round(REVEAL_DELAY_MS * RING_START_FRACTION);

/**
 * Deckt etwas nach kurzem Verweilen auf und verbirgt es beim Verlassen wieder.
 *
 * Das Verzoegern ist Absicht: erst selbst lesen, dann nachsehen. Ohne die Pause
 * huepft die Aussprache schon beim Vorbeifahren ins Bild und der Selbsttest ist
 * dahin.
 */
export function useRevealOnHover(delayMs: number = REVEAL_DELAY_MS) {
  const [hovering, setHovering] = useState(false);
  const [revealed, setRevealed] = useState(false);
  /** Wartet schon lange genug, dass der Ladekreis sich lohnt. */
  const [pendingReveal, setPendingReveal] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const ringTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clear = useCallback(() => {
    for (const handle of [timer, ringTimer]) {
      if (handle.current !== null) {
        clearTimeout(handle.current);
        handle.current = null;
      }
    }
  }, []);

  useEffect(() => clear, [clear]);

  const onMouseEnter = useCallback(() => {
    setHovering(true);
    clear();
    ringTimer.current = setTimeout(
      () => setPendingReveal(true),
      Math.round(delayMs * RING_START_FRACTION),
    );
    timer.current = setTimeout(() => {
      setRevealed(true);
      setPendingReveal(false);
    }, delayMs);
  }, [clear, delayMs]);

  const onMouseLeave = useCallback(() => {
    clear();
    setHovering(false);
    setRevealed(false);
    setPendingReveal(false);
  }, [clear]);

  return { hovering, revealed, pendingReveal, bind: { onMouseEnter, onMouseLeave } };
}
