import { useSpeech } from "../audio/SpeechContext";
import type { ListenMeaningExercise as Model, Submission } from "../courseTypes";
import AudioPrompt from "./AudioPrompt";
import RussianText from "./RussianText";

/**
 * Satz anhören, deutsche Bedeutung wählen. Ohne russische Stimme wird der Satz
 * angezeigt statt gesprochen — dann ist es eine Leseaufgabe, aber lösbar.
 */
export default function ListenMeaningExercise({
  exercise,
  disabled = false,
  onSubmit,
}: {
  exercise: Model;
  disabled?: boolean;
  onSubmit: (submission: Submission) => void;
}) {
  const { available } = useSpeech();

  return (
    <div className="space-y-4">
      <AudioPrompt text={exercise.audio_text} promptDe={exercise.prompt_de} />
      {available ? null : (
        <div className="flex flex-wrap items-end gap-3 text-xl">
          {exercise.sentence.map((word, position) => (
            <RussianText key={`word-${position}`} word={word} />
          ))}
        </div>
      )}
      <div className="flex flex-col gap-2">
        {exercise.options_de.map((option, index) => (
          <button
            key={option}
            type="button"
            disabled={disabled}
            onClick={() => onSubmit({ option_index: index })}
            className="rounded-xl border-2 border-slate-300 bg-white px-4 py-2 text-left text-lg transition hover:border-sky-400 disabled:opacity-60"
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  );
}
