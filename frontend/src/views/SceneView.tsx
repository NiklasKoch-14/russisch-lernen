import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import BuildSentenceExercise from "../course/BuildSentenceExercise";
import NpcLine from "../game/NpcLine";
import PlaceHeader from "../game/PlaceHeader";
import PlaceStage from "../game/PlaceStage";
import { answerTurn, getPlace, getTurn } from "../gameApi";
import type { PlaceDetail, Submission, TurnResult, TurnView } from "../gameTypes";

export default function SceneView() {
  const { placeId, sceneId } = useParams();
  const [params] = useSearchParams();
  const seed = params.get("seed") ?? "";
  const navigate = useNavigate();

  const [index, setIndex] = useState(0);
  const [turn, setTurn] = useState<TurnView | null>(null);
  const [place, setPlace] = useState<PlaceDetail | null>(null);
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

  // Der Raum kommt aus der Ortsnutzlast, nicht aus dem Router-Zustand: die
  // Szene muss ein Neuladen ihrer Adresse unbeschadet überstehen. Bleibt er
  // aus, läuft das Gespräch ohne Kulisse weiter.
  useEffect(() => {
    if (!placeId) return;
    getPlace(placeId)
      .then(setPlace)
      .catch(() => setPlace(null));
  }, [placeId]);

  const submit = useCallback(
    (submission: Submission) => {
      if (!sceneId) return;
      answerTurn(sceneId, index, seed, submission)
        .then(setResult)
        .catch(() => setError(true));
    },
    [sceneId, index, seed],
  );

  const leave = () => navigate(`/dorf/${placeId}`);

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
  if (!turn && !done) return <p>Szene wird geladen …</p>;

  /** Nach einem zweiten Versuch geht es immer weiter, egal wie er ausging. */
  const canRetry = result !== null && !result.correct && !retried;

  const speaker = done ? null : place?.npcs.find((npc) => npc.id === turn!.npc.id);
  // Steht die Person links im Bild, gehört die Karte nach rechts — und umgekehrt.
  const side =
    speaker?.spot && speaker.spot.x + speaker.spot.w / 2 >= 0.5 ? "left" : "right";

  const card = (
    <div
      data-testid="dialog-card"
      data-side={side}
      className={`pointer-events-auto space-y-4 rounded-2xl border-2 border-slate-200 bg-white/95 p-4 shadow-lg backdrop-blur-sm absolute top-14 max-h-[calc(100%-4.5rem)] w-[46%] overflow-y-auto max-sm:static max-sm:mt-4 max-sm:max-h-none max-sm:w-full ${
        side === "left" ? "left-4 sm:left-6" : "right-4 sm:right-6"
      }`}
    >
      {done ? (
        <>
          <h2 className="text-2xl font-semibold">Geschafft!</h2>
          <p>{done.outro_de}</p>
          <button
            type="button"
            onClick={leave}
            className="rounded-xl bg-sky-600 px-5 py-2 font-medium text-white"
          >
            Zurück in den Raum
          </button>
        </>
      ) : (
        <>
          <header className="flex items-baseline justify-between gap-3">
            <div>
              <p className="text-lg font-medium">{turn!.npc.name_ru}</p>
              <p className="text-sm text-slate-600">{turn!.npc.name_de}</p>
            </div>
            <p className="text-sm text-slate-500">
              Zug {turn!.index + 1} von {turn!.turn_count}
            </p>
          </header>

          <NpcLine line={turn!.npc_line} />

          <BuildSentenceExercise
            key={`${turn!.index}-${retried}`}
            exercise={turn!.exercise}
            disabled={result !== null}
            onSubmit={submit}
          />

          {result && (
            // Dieselbe Rueckmeldung wie im Kurs: gruen mit "Richtig!", rot mit
            // "Nicht ganz." — ohne sie bleibt nach dem Pruefen offen, ob die
            // Antwort gestimmt hat.
            <div
              data-testid="turn-feedback"
              className={`space-y-3 rounded-xl p-3 ${
                result.correct ? "bg-emerald-50" : "bg-rose-50"
              }`}
            >
              <p className="font-medium">{result.correct ? "Richtig!" : "Nicht ganz."}</p>
              {result.npc_reaction && <NpcLine line={result.npc_reaction} />}
              {!result.correct && <p>{result.explanation_de}</p>}
              {result.scene_completed && <p>{result.outro_de}</p>}
              <button
                type="button"
                onClick={canRetry ? retry : advance}
                className="rounded-xl bg-sky-600 px-5 py-2 font-medium text-white"
              >
                {canRetry ? "Nochmal" : "Weiter"}
              </button>
            </div>
          )}

          <button type="button" onClick={leave} className="text-sm text-sky-700 underline">
            Zurück
          </button>
        </>
      )}
    </div>
  );

  return (
    <section className="flex w-full flex-col gap-4 sm:min-h-0 sm:flex-1">
      {/* Der Rahmen steht immer, auch bevor der Raum geladen ist: sonst haengt
          React die Dialogkarte beim Nachladen um und die schon gewaehlten
          Kacheln sind weg. */}
      <div className="relative aspect-[3/2] w-full overflow-hidden sm:aspect-auto sm:min-h-0 sm:flex-1">
        {place && (
          <PlaceStage
            art={place.art}
            altText={place.name_de}
            npcs={place.npcs}
            focusNpcId={done ? undefined : turn!.npc.id}
            cover
          />
        )}
        {place && (
          // Auf die freie Seite: die Dialogkarte deckt sonst genau die Ecke
          // zu, in der der Ortsname steht.
          <div
            className={`pointer-events-none absolute top-4 pt-14 sm:top-6 sm:pt-16 ${
              side === "left" ? "right-4 text-right sm:right-6" : "left-4 sm:left-6"
            }`}
          >
            <div className="pointer-events-auto">
              <PlaceHeader nameRu={place.name_ru} nameDe={place.name_de} onImage />
            </div>
          </div>
        )}
        {card}
      </div>
    </section>
  );
}
