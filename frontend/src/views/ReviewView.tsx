import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import SpeakerButton from "../audio/SpeakerButton";
import ExerciseRunner from "../course/ExerciseRunner";
import MatchPairsExercise from "../course/MatchPairsExercise";
import {
  getReviewRound,
  submitReviewExercise,
  submitReviewRound,
} from "../courseApi";
import type { ReviewItem, ReviewResult, ReviewRound, Submission } from "../courseTypes";

/** Was am Ende der Runde gezeigt wird — aus beiden Eintragsarten zusammengetragen. */
interface Zeile {
  ref: string;
  correct: boolean;
  text: string;
  gloss_de: string;
}

export default function ReviewView() {
  const [round, setRound] = useState<ReviewRound | null>(null);
  const [position, setPosition] = useState(0);
  const [lines, setLines] = useState<Zeile[]>([]);
  const [error, setError] = useState(false);

  const laden = useCallback(() => {
    setRound(null);
    setPosition(0);
    setLines([]);
    getReviewRound()
      .then(setRound)
      .catch(() => setError(true));
  }, []);

  useEffect(laden, [laden]);

  if (error) return <p>Die Wiederholung konnte nicht geladen werden.</p>;
  if (!round) return <p>Wiederholung wird geladen …</p>;

  if (round.items.length === 0) {
    return (
      <div className="space-y-4">
        <p>Gerade gibt es nichts zu wiederholen. Mach im Kurs weiter!</p>
        <Link to="/" className="inline-block rounded-xl bg-sky-600 px-5 py-2 font-medium text-white">
          Zurück zu Heute
        </Link>
      </div>
    );
  }

  const item: ReviewItem | undefined = round.items[position];

  if (!item) {
    return (
      <div className="space-y-3">
        <h2 className="text-2xl font-semibold">
          {lines.filter((line) => line.correct).length} von {lines.length} richtig
        </h2>
        <ul className="space-y-1">
          {lines.map((line) => (
            <li
              key={line.ref}
              className={`flex items-center gap-2 ${
                line.correct ? "text-emerald-700" : "text-rose-700"
              }`}
            >
              <span lang="ru">{line.text}</span>
              {line.gloss_de ? <span>— {line.gloss_de}</span> : null}
              <SpeakerButton text={line.text} />
            </li>
          ))}
        </ul>
        {/* Die Startseite zaehlt mit, wie viel heute aufgefrischt wurde, und
            setzt den Haken; wer mag, macht gleich die naechste Runde. */}
        <div className="flex flex-wrap items-center gap-4 pt-2">
          <Link to="/" className="inline-block rounded-xl bg-sky-600 px-5 py-2 font-medium text-white">
            Zurück zu Heute
          </Link>
          <button type="button" onClick={laden} className="rounded-xl border-2 border-slate-300 bg-white px-4 py-2 transition hover:border-sky-400">
            Weiter auffrischen
          </button>
        </div>
      </div>
    );
  }

  const weiter = () => setPosition((current) => current + 1);

  if (item.kind === "pairs") {
    return (
      <MatchPairsExercise
        exercise={{
          id: "review",
          type: "match_pairs",
          prompt_de: "Ordne die fälligen Wortformen ihrer Bedeutung zu.",
          left: item.left,
          right: item.right,
        }}
        onSubmit={(submission: Submission) => {
          if (!("pairs" in submission)) return;
          submitReviewRound(submission.pairs)
            .then((result: ReviewResult) => {
              setLines((current) => [...current, ...result.results]);
              weiter();
            })
            .catch(() => setError(true));
        }}
      />
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">
        Wiederholung {position + 1} von {round.items.length}
      </p>
      <ExerciseRunner
        key={item.exercise_id}
        exercise={item}
        onSubmit={(submission: Submission) => {
          submitReviewExercise(item.unit_id, item.exercise_id, submission)
            .then((answer) => {
              setLines((current) => [
                ...current,
                {
                  ref: item.ref,
                  correct: answer.correct,
                  text: answer.solution_text,
                  gloss_de: "",
                },
              ]);
              weiter();
            })
            .catch(() => setError(true));
        }}
      />
    </div>
  );
}
