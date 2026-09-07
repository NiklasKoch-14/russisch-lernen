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
  const { revealed, pendingReveal, bind } = useRevealOnHover();
  const showsRing = pendingReveal && Boolean(word.translit);

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
    </button>
  );
}
