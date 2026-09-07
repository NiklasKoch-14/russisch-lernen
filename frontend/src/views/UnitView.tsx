import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import ExerciseRunner from "../course/ExerciseRunner";
import NewWords from "../course/NewWords";
import { getUnit, submitAnswer } from "../courseApi";
import SpeakerButton from "../audio/SpeakerButton";
import type { AnswerResult, Submission, UnitDetail } from "../courseTypes";

type Phase = "rule" | "words" | "exercises" | "done";

export default function UnitView() {
  const { unitId } = useParams();
  const id = Number(unitId);
  const [unit, setUnit] = useState<UnitDetail | null>(null);
  const [phase, setPhase] = useState<Phase>("rule");
  /** Was noch drankommt. Falsch Beantwortetes wandert ans Ende statt zu verschwinden. */
  const [queue, setQueue] = useState<string[] | null>(null);
  const [solved, setSolved] = useState<Set<string>>(new Set());
  const [missed, setMissed] = useState<Set<string>>(new Set());
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getUnit(id)
      .then((loaded) => {
        setUnit(loaded);
        setQueue(loaded.exercises.map((item) => item.id));
      })
      .catch(() => setError(true));
  }, [id]);

  if (error) return <p>Die Einheit konnte nicht geladen werden.</p>;
  if (!unit) return <p>Einheit wird geladen …</p>;

  // Wer die Einheit schon geschafft hat, braucht die Woerter nicht noch einmal
  // vorgestellt zu bekommen — der Fortschritt sagt das bereits.
  const completed = unit.solved_exercise_ids.length >= unit.exercises.length;
  const introducesWords = unit.new_words.length > 0 && !completed;
  const afterRule = () => setPhase(introducesWords ? "words" : "exercises");

  if (phase === "words") {
    return <NewWords words={unit.new_words} onContinue={() => setPhase("exercises")} />;
  }

  if (phase === "rule") {
    return (
      <article className="space-y-4">
        <h2 className="text-2xl font-semibold">{unit.title_de}</h2>
        <p className="text-slate-600">{unit.scenario_de}</p>
        <section className="rounded-2xl border-2 border-sky-200 bg-sky-50 p-4">
          <h3 className="font-medium">{unit.grammar_focus.title_de}</h3>
          <p className="mt-2 whitespace-pre-line">{unit.grammar_focus.explanation_de}</p>
        </section>
        <button
          type="button"
          onClick={afterRule}
          className="rounded-xl bg-sky-600 px-5 py-2 font-medium text-white"
        >
          Los geht's
        </button>
      </article>
    );
  }

  if (phase === "done") {
    return (
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold">Einheit geschafft!</h2>
        <Link
          to="/kurs"
          className="inline-block rounded-xl bg-sky-600 px-5 py-2 font-medium text-white"
        >
          Zurück zum Kurs
        </Link>
      </div>
    );
  }

  const currentId = queue?.[0];
  const exercise = unit.exercises.find((item) => item.id === currentId) ?? unit.exercises[0];
  const isRepeat = missed.has(exercise.id);

  const handleSubmit = (submission: Submission) => {
    submitAnswer(id, exercise.id, submission)
      .then((answer) => {
        setResult(answer);
        if (!answer.correct) setMissed((current) => new Set(current).add(exercise.id));
      })
      .catch(() => setError(true));
  };

  // Die Backend-Erklaerung nennt bei den meisten Aufgabentypen bereits die Loesung.
  // Dann waere sie neben der "Richtig ist"-Zeile nur eine Dopplung.
  const extraExplanation =
    result && !result.correct && !result.explanation_de.includes(result.solution_text)
      ? result.explanation_de
      : "";

  const advance = () => {
    const wasCorrect = result?.correct === true;
    setResult(null);
    if (wasCorrect) setSolved((current) => new Set(current).add(exercise.id));

    const [head, ...rest] = queue ?? [];
    // Richtig: raus aus der Schlange. Falsch: ans Ende, damit sie wiederkommt.
    const next = wasCorrect ? rest : [...rest, head];
    setQueue(next);
    if (next.length === 0) setPhase("done");
  };

  return (
    <div className="space-y-6">
      {/* Geloeste statt Position: sonst zaehlte der Zaehler bei Wiederholungen
          ueber die Gesamtzahl hinaus. Er bleibt stehen, wenn es nicht stimmte —
          was ehrlich ist, man ist ja nicht weitergekommen. */}
      <p className="text-sm text-slate-500">
        Aufgabe {solved.size + 1} von {unit.exercises.length}
      </p>
      {isRepeat ? (
        <p className="text-sm text-amber-700">
          Noch einmal — beim letzten Mal hat es nicht gestimmt.
        </p>
      ) : null}
      <ExerciseRunner
        key={exercise.id}
        exercise={exercise}
        disabled={result !== null}
        onSubmit={handleSubmit}
      />
      {result ? (
        <div
          data-testid="feedback"
          className={`space-y-2 rounded-2xl p-4 ${result.correct ? "bg-emerald-50" : "bg-rose-50"}`}
        >
          <p className="font-medium">{result.correct ? "Richtig!" : "Nicht ganz."}</p>
          {extraExplanation ? <p>{extraExplanation}</p> : null}
          {/* Ein Block fuer beide Faelle: nach einem Fehler nennt er die Loesung,
              nach einer richtigen Antwort bietet er sie nur zum Nachhoeren an. */}
          {result.solution_audio.length > 0 ? (
            <div className="flex flex-wrap items-center gap-3">
              {result.correct ? null : <span>Richtig ist:</span>}
              {result.solution_audio.map((part) => (
                <span key={part} className="flex items-center gap-1">
                  <span lang="ru">{part}</span>
                  <SpeakerButton text={part} />
                </span>
              ))}
            </div>
          ) : null}
          <button
            type="button"
            onClick={advance}
            className="rounded-xl bg-sky-600 px-5 py-2 font-medium text-white"
          >
            Weiter
          </button>
        </div>
      ) : null}
    </div>
  );
}
