import type { Word } from "../courseTypes";
import RevealRing from "./RevealRing";
import RussianText from "./RussianText";
import { useRevealOnHover } from "./useRevealOnHover";

export type TileState = "idle" | "selected" | "correct" | "wrong";

const STYLES: Record<TileState, string> = {
  idle: "border-slate-300 bg-white hover:border-sky-400",
  selected: "border-sky-500 bg-sky-50",
  correct: "border-emerald-500 bg-emerald-50",
  wrong: "border-rose-500 bg-rose-50",
};

export default function Tile({
  word,
  state,
  onClick,
  disabled = false,
  className = "",
}: {
  word: Word;
  state: TileState;
  onClick: () => void;
  disabled?: boolean;
  className?: string;
}) {
  // Das Aufdecken haengt an der ganzen Karte, nicht am winzigen Text darin.
  const { revealed, pendingReveal, revealedGloss, bind } = useRevealOnHover();
  const showsRing = pendingReveal && Boolean(word.translit);
  // Zweite Runde nur, wo es auch etwas aufzudecken gibt.
  const showsGlossRing = revealed && !revealedGloss && Boolean(word.gloss_de);
  const showsGloss = revealedGloss && Boolean(word.gloss_de);

  return (
    <button
      type="button"
      aria-pressed={state === "selected"}
      disabled={disabled}
      onClick={onClick}
      {...bind}
      className={`relative rounded-xl border-2 px-4 py-2 text-lg transition disabled:opacity-60 ${STYLES[state]} ${className}`}
    >
      <RussianText word={word} revealed={revealed} />
      {showsRing ? <RevealRing /> : null}
      {showsGlossRing ? <RevealRing phase="gloss" /> : null}
      {/* Als Fahne unter der Kachel statt im Fluss: sonst waere jede Kachel
          dauerhaft eine Zeile hoeher, nur damit beim Aufdecken nichts springt. */}
      {showsGloss ? (
        <span className="pointer-events-none absolute left-1/2 top-full z-10 mt-1 -translate-x-1/2 whitespace-nowrap rounded-lg bg-slate-800 px-2 py-1 text-xs font-medium text-white shadow">
          {word.gloss_de}
        </span>
      ) : null}
    </button>
  );
}
