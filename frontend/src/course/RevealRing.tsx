import { REVEAL_DELAY_MS } from "./useRevealOnHover";

const SIZE = 16;
const STROKE = 2.5;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/**
 * Der Donut oben rechts auf der Karte: laeuft in einer Sekunde voll und zeigt
 * damit an, wie lange die Maus noch stillhalten muss, bis die Aussprache
 * erscheint. Ohne ihn wirkt die Verzoegerung wie Traegheit statt wie Absicht.
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
          animation: `speaker-reveal-ring ${REVEAL_DELAY_MS}ms linear forwards`,
        }}
      />
    </svg>
  );
}
