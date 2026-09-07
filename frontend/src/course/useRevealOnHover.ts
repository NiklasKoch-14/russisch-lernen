import { useCallback, useEffect, useRef, useState } from "react";

/** So lange muss die Maus stillhalten, bis die Aussprache erscheint. */
export const REVEAL_DELAY_MS = 1000;

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
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clear = useCallback(() => {
    if (timer.current !== null) {
      clearTimeout(timer.current);
      timer.current = null;
    }
  }, []);

  useEffect(() => clear, [clear]);

  const onMouseEnter = useCallback(() => {
    setHovering(true);
    clear();
    timer.current = setTimeout(() => setRevealed(true), delayMs);
  }, [clear, delayMs]);

  const onMouseLeave = useCallback(() => {
    clear();
    setHovering(false);
    setRevealed(false);
  }, [clear]);

  return { hovering, revealed, bind: { onMouseEnter, onMouseLeave } };
}
