import { useState } from "react";

import type { BuildSentenceExercise as Model, Submission } from "../courseTypes";
import Tile from "./Tile";

export default function BuildSentenceExercise({
  exercise,
  disabled = false,
  onSubmit,
}: {
  exercise: Model;
  disabled?: boolean;
  onSubmit: (submission: Submission) => void;
}) {
  const [chosen, setChosen] = useState<number[]>([]);

  const toggle = (index: number) =>
    setChosen((current) =>
      current.includes(index) ? current.filter((item) => item !== index) : [...current, index],
    );

  return (
    <div className="space-y-4">
      <p className="text-lg">{exercise.prompt_de}</p>
      <div className="min-h-16 rounded-xl border-2 border-dashed border-slate-300 p-3">
        <div className="flex flex-wrap gap-2">
          {chosen.map((index) => (
            <Tile
              key={index}
              word={exercise.tiles[index]}
              state="selected"
              disabled={disabled}
              onClick={() => toggle(index)}
            />
          ))}
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {exercise.tiles
          .filter((tile) => !chosen.includes(tile.index))
          .map((tile) => (
            <Tile
              key={tile.index}
              word={tile}
              state="idle"
              disabled={disabled}
              onClick={() => toggle(tile.index)}
            />
          ))}
      </div>
      <button
        type="button"
        disabled={disabled || chosen.length === 0}
        onClick={() => onSubmit({ tile_indices: chosen })}
        className="rounded-xl bg-sky-600 px-5 py-2 font-medium text-white disabled:opacity-50"
      >
        Prüfen
      </button>
    </div>
  );
}
