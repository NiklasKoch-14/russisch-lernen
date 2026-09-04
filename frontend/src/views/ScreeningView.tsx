import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { answerScreening, startScreening } from "../courseApi";
import type { ScreeningProbe } from "../courseTypes";

export default function ScreeningView() {
  const [probe, setProbe] = useState<ScreeningProbe | null>(null);
  const [answers, setAnswers] = useState<number[]>([]);
  const [placement, setPlacement] = useState<number | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    startScreening()
      .then((step) => (step.finished ? setPlacement(step.placement_unit) : setProbe(step.probe)))
      .catch(() => setError(true));
  }, []);

  const choose = (option: number) => {
    const next = [...answers, option];
    setAnswers(next);
    answerScreening(next)
      .then((step) => {
        if (step.finished) {
          setPlacement(step.placement_unit);
          setProbe(null);
        } else {
          setProbe(step.probe);
        }
      })
      .catch(() => setError(true));
  };

  if (error) return <p>Die Einstufung konnte nicht geladen werden.</p>;

  if (placement !== null) {
    return (
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold">Fertig!</h2>
        <p>Wir schlagen vor, dass du hier einsteigst:</p>
        <Link
          to={`/kurs/${placement}`}
          className="inline-block rounded-xl bg-sky-600 px-5 py-2 font-medium text-white"
        >
          Mit Einheit {placement} starten
        </Link>
      </div>
    );
  }

  if (!probe) return <p>Einstufung wird geladen …</p>;

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">
        Frage {probe.index + 1} von {probe.total}
      </p>
      <h2 className="text-xl">{probe.prompt_de}</h2>
      <div className="flex flex-col gap-2">
        {probe.options.map((option, index) => (
          <button
            key={option}
            type="button"
            onClick={() => choose(index)}
            className="rounded-xl border-2 border-slate-300 bg-white px-4 py-3 text-left text-lg hover:border-sky-400"
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  );
}
