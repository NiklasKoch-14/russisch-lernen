import type { Exercise, Submission } from "../courseTypes";
import BuildSentenceExercise from "./BuildSentenceExercise";
import ChooseFormExercise from "./ChooseFormExercise";
import DialogReplyExercise from "./DialogReplyExercise";
import ListenMeaningExercise from "./ListenMeaningExercise";
import MatchPairsExercise from "./MatchPairsExercise";

export default function ExerciseRunner({
  exercise,
  disabled = false,
  onSubmit,
}: {
  exercise: Exercise;
  disabled?: boolean;
  onSubmit: (submission: Submission) => void;
}) {
  const props = { disabled, onSubmit };
  switch (exercise.type) {
    case "build_sentence":
      return <BuildSentenceExercise exercise={exercise} {...props} />;
    case "choose_form":
      return <ChooseFormExercise exercise={exercise} {...props} />;
    case "match_pairs":
      return <MatchPairsExercise exercise={exercise} {...props} />;
    case "dialog_reply":
      return <DialogReplyExercise exercise={exercise} {...props} />;
    case "listen_meaning":
      return <ListenMeaningExercise exercise={exercise} {...props} />;
  }
}
