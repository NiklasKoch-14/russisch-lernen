import { useEffect, useState } from "react";

import MatchPairsExercise from "../course/MatchPairsExercise";
import { getReviewRound, submitReviewRound } from "../courseApi";
import type { ReviewResult, ReviewRound } from "../courseTypes";

export default function ReviewView() {
  const [round, setRound] = useState<ReviewRound | null>(null);
  const [result, setResult] = useState<ReviewResult | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getReviewRound()
      .then(setRound)
      .catch(() => setError(true));
  }, []);

  if (error) return <p>Die Wiederholung konnte nicht geladen werden.</p>;
  if (!round) return <p>Wiederholung wird geladen …</p>;

  if (result) {
    return (
      <div className="space-y-3">
        <h2 className="text-2xl font-semibold">
          {result.correct_count} von {result.total_count} richtig
        </h2>
        <ul className="space-y-1">
          {result.results.map((item) => (
            <li key={item.ref} className={item.correct ? "text-emerald-700" : "text-rose-700"}>
              <span lang="ru">{item.text}</span> — {item.gloss_de}
            </li>
          ))}
        </ul>
      </div>
    );
  }

  if (round.left.length === 0) {
    return <p>Gerade gibt es nichts zu wiederholen. Mach im Kurs weiter!</p>;
  }

  return (
    <MatchPairsExercise
      exercise={{
        id: "review",
        type: "match_pairs",
        prompt_de: "Ordne die fälligen Wortformen ihrer Bedeutung zu.",
        left: round.left,
        right: round.right,
      }}
      onSubmit={(submission) => {
        if ("pairs" in submission) {
          submitReviewRound(submission.pairs)
            .then(setResult)
            .catch(() => setError(true));
        }
      }}
    />
  );
}
