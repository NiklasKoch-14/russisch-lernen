import type { DialogReplyExercise as Model, Submission } from "../courseTypes";
import RussianText from "./RussianText";
import Tile from "./Tile";

export default function DialogReplyExercise({
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
      <p className="text-lg">{exercise.prompt_de}</p>
      <div
        data-testid="tutor-line"
        className="flex flex-wrap gap-2 rounded-2xl bg-white p-4 text-xl shadow-sm"
      >
        {exercise.tutor_line.map((word, position) => (
          <RussianText key={position} word={word} />
        ))}
      </div>
      <div className="flex flex-col gap-2">
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
