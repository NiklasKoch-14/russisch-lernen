import { REVEAL_DELAY_MS, RING_DELAY_MS } from "./useRevealOnHover";

const SIZE = 16;
const STROKE = 2.5;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/**
 * Der Donut oben rechts auf der Karte: zeigt an, wie lange die Maus noch
 * stillhalten muss, bis die Aussprache erscheint. Ohne ihn wirkt die
 * Verzoegerung wie Traegheit statt wie Absicht.
 *
 * Er erscheint erst nach einem Drittel der Wartezeit — und dann schon zu einem
 * Drittel gefuellt. Der negative Startversatz sorgt dafuer: die Animation
 * beginnt so, als liefe sie bereits seit dem Hovern, und wird punktgenau mit
 * dem Aufdecken voll.
 */
export default function RevealRing() {
  return (
    <svg
      data-testid="reveal-ring"
      aria-hidden="true"
      width={SIZE}
      height={SIZE}
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      className="absolute right-1.5 top-1.5"
    >
      <circle
        cx={SIZE / 2}
        cy={SIZE / 2}
        r={RADIUS}
        fill="none"
        strokeWidth={STROKE}
        className="stroke-slate-200"
      />
      <circle
        cx={SIZE / 2}
        cy={SIZE / 2}
        r={RADIUS}
        fill="none"
        strokeWidth={STROKE}
        strokeLinecap="round"
        strokeDasharray={CIRCUMFERENCE}
        className="origin-center -rotate-90 stroke-sky-500"
        style={{
          animation: `speaker-reveal-ring ${REVEAL_DELAY_MS}ms linear -${RING_DELAY_MS}ms forwards`,
        }}
      />
    </svg>
  );
}
