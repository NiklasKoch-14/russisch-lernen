import type { Word } from "../courseTypes";
import RussianText from "./RussianText";

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
  return (
    <button
      type="button"
      aria-pressed={state === "selected"}
      disabled={disabled}
      onClick={onClick}
      className={`rounded-xl border-2 px-4 py-2 text-lg transition disabled:opacity-60 ${STYLES[state]} ${className}`}
    >
      <RussianText word={word} />
    </button>
  );
}
