import { useState } from "react";

import type { MatchPairsExercise as Model, Submission } from "../courseTypes";
import Tile from "./Tile";

export default function MatchPairsExercise({
  exercise,
  disabled = false,
  onSubmit,
}: {
  exercise: Model;
  disabled?: boolean;
  onSubmit: (submission: Submission) => void;
}) {
  const [active, setActive] = useState<number | null>(null);
  const [pairs, setPairs] = useState<number[][]>([]);

  const matchedLeft = pairs.map((pair) => pair[0]);
  const matchedRight = pairs.map((pair) => pair[1]);

  const pickRight = (rightIndex: number) => {
    if (active === null) return;
    const next = [...pairs, [active, rightIndex]];
    setPairs(next);
    setActive(null);
    if (next.length === exercise.left.length) {
      onSubmit({ pairs: next });
    }
  };

  return (
    <div className="space-y-4">
      <p className="text-lg">{exercise.prompt_de}</p>
      {/* Ein Raster statt zweier Stapel: nur so teilen sich die Zeilen ihre
          Hoehe, und links wie rechts sind die Karten gleich gross. Mit
          grid-flow-col bleibt die Lesereihenfolge trotzdem spaltenweise. */}
      <div
        className="grid grid-flow-col grid-cols-2 gap-3"
        style={{ gridTemplateRows: `repeat(${exercise.left.length}, 1fr)` }}
      >
        {exercise.left.map((item) => (
          <Tile
            key={item.index}
            word={item}
            className="flex h-full items-center justify-center text-center"
            state={
              matchedLeft.includes(item.index)
                ? "correct"
                : active === item.index
                  ? "selected"
                  : "idle"
            }
            disabled={disabled || matchedLeft.includes(item.index)}
            onClick={() => setActive(item.index)}
          />
        ))}
        {exercise.right.map((item) => (
          <button
            key={item.index}
            type="button"
            disabled={disabled || matchedRight.includes(item.index)}
            onClick={() => pickRight(item.index)}
            className="flex h-full items-center justify-center rounded-xl border-2 border-slate-300 bg-white px-4 py-2 text-center transition hover:border-sky-400 disabled:opacity-50"
          >
            {item.gloss_de}
          </button>
        ))}
      </div>
    </div>
  );
}
