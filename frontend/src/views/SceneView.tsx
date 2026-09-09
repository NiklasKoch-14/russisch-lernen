import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import BuildSentenceExercise from "../course/BuildSentenceExercise";
import NpcLine from "../game/NpcLine";
import { answerTurn, artUrl, getTurn } from "../gameApi";
import type { Submission, TurnResult, TurnView } from "../gameTypes";

export default function SceneView() {
  const { placeId, sceneId } = useParams();
  const [params] = useSearchParams();
  const seed = params.get("seed") ?? "";
  const navigate = useNavigate();

  const [index, setIndex] = useState(0);
  const [turn, setTurn] = useState<TurnView | null>(null);
  const [result, setResult] = useState<TurnResult | null>(null);
  /** Ein Zug wird nach einem Fehler genau einmal wiederholt, dann geht es weiter. */
  const [retried, setRetried] = useState(false);
  const [done, setDone] = useState<TurnResult | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!sceneId || !seed) return;
    getTurn(sceneId, seed, index)
      .then(setTurn)
      .catch(() => setError(true));
  }, [sceneId, seed, index]);

  const submit = useCallback(
    (submission: Submission) => {
      if (!sceneId) return;
      answerTurn(sceneId, index, seed, submission)
        .then(setResult)
        .catch(() => setError(true));
    },
    [sceneId, index, seed],
  );

  const retry = () => {
    setResult(null);
    setRetried(true);
  };

  const advance = () => {
    if (result?.scene_completed) {
      setDone(result);
      return;
    }
    setResult(null);
    setRetried(false);
    setIndex((current) => current + 1);
  };

  if (error) return <p>Die Szene konnte nicht geladen werden.</p>;

  if (done) {
    return (
      <section className="mx-auto max-w-3xl space-y-4">
        <h2 className="text-2xl font-semibold">Geschafft!</h2>
        <p>{done.outro_de}</p>
        <button
          type="button"
          onClick={() => navigate(`/dorf/${placeId}`)}
          className="rounded-xl bg-sky-600 px-5 py-2 font-medium text-white"
        >
          Zurück
        </button>
      </section>
    );
  }

  if (!turn) return <p>Szene wird geladen …</p>;

  /** Nach einem zweiten Versuch geht es immer weiter, egal wie er ausging. */
  const canRetry = result !== null && !result.correct && !retried;

  return (
    <section className="mx-auto max-w-3xl space-y-4">
      <header className="flex items-center gap-3">
        <img
          src={artUrl(turn.npc.art)}
          alt={turn.npc.name_de}
          className="h-16 w-16 rounded-full object-cover"
        />
        <div>
          <p className="text-lg font-medium">{turn.npc.name_ru}</p>
          <p className="text-sm text-slate-600">{turn.npc.name_de}</p>
        </div>
      </header>

      <p className="text-sm text-slate-500">
        Zug {turn.index + 1} von {turn.turn_count}
      </p>
      <NpcLine line={turn.npc_line} />

      <BuildSentenceExercise
        key={`${turn.index}-${retried}`}
        exercise={turn.exercise}
        disabled={result !== null}
        onSubmit={submit}
      />

      {result && (
        <div className="space-y-3 rounded-2xl border-2 border-slate-200 p-4">
          {result.npc_reaction && <NpcLine line={result.npc_reaction} />}
          {!result.correct && <p>{result.explanation_de}</p>}
          {result.scene_completed && <p>{result.outro_de}</p>}
          {canRetry ? (
            <button
              type="button"
              onClick={retry}
              className="rounded-xl bg-sky-600 px-5 py-2 font-medium text-white"
            >
              Nochmal
            </button>
          ) : (
            <button
              type="button"
              onClick={advance}
              className="rounded-xl bg-sky-600 px-5 py-2 font-medium text-white"
            >
              Weiter
            </button>
          )}
        </div>
      )}
    </section>
  );
}
