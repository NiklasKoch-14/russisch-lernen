import type { ChooseFormExercise as Model, Submission } from "../courseTypes";
import AudioPrompt from "./AudioPrompt";
import RussianText from "./RussianText";
import Tile from "./Tile";

export default function ChooseFormExercise({
  exercise,
  disabled = false,
  onSubmit,
}: {
  exercise: Model;
  disabled?: boolean;
  onSubmit: (submission: Submission) => void;
}) {
  return (
    <div className="space-y-4">
      {exercise.audio_prompt && exercise.audio_text ? (
        <AudioPrompt text={exercise.audio_text} promptDe={exercise.prompt_de} />
      ) : (
        <p className="text-lg">{exercise.prompt_de}</p>
      )}
      <div className="flex flex-wrap items-end gap-3 text-xl">
        {exercise.sentence.map((word, position) =>
          word === null ? (
            <span
              key={`blank-${position}`}
              data-testid="blank"
              className="inline-block w-24 border-b-2 border-slate-400"
            />
          ) : (
            <RussianText key={`word-${position}`} word={word} />
          ),
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        {exercise.options.map((option) => (
          <Tile
            key={option.index}
            word={option}
            state="idle"
            disabled={disabled}
            onClick={() => onSubmit({ option_index: option.index })}
          />
        ))}
      </div>
    </div>
  );
}
