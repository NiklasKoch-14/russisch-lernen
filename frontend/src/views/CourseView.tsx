import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getCourse } from "../courseApi";
import type { CourseOverview, UnitSummary } from "../courseTypes";

export const STAGE_TITLES: Record<number, string> = {
  0: "Schrift & Klang",
  1: "Erste Sätze",
  2: "Alltag konkret",
  3: "Erzählen",
  4: "Flüssiger Alltag",
};

const STATUS_LABEL: Record<UnitSummary["status"], string> = {
  not_started: "noch offen",
  in_progress: "angefangen",
  completed: "abgeschlossen",
};

const STATUS_STYLE: Record<UnitSummary["status"], string> = {
  not_started: "border-slate-200 bg-white",
  in_progress: "border-sky-300 bg-sky-50",
  completed: "border-emerald-300 bg-emerald-50",
};

export default function CourseView() {
  const [overview, setOverview] = useState<CourseOverview | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getCourse()
      .then(setOverview)
      .catch(() => setError(true));
  }, []);

  if (error) return <p>Der Kurs konnte nicht geladen werden.</p>;
  if (!overview) return <p>Kurs wird geladen …</p>;

  return (
    <div className="space-y-8">
      {overview.stages.map((stage) => (
        <section key={stage.stage} className="space-y-3">
          <h2 className="text-xl font-semibold">
            {STAGE_TITLES[stage.stage] ?? `Stufe ${stage.stage}`}
          </h2>
          <ul className="space-y-2">
            {stage.units.map((unit) => (
              <li key={unit.id}>
                <Link
                  to={`/kurs/${unit.id}`}
                  aria-label={`Einheit ${unit.id}: ${unit.title_de} — ${STATUS_LABEL[unit.status]}`}
                  className={`flex items-center justify-between rounded-xl border-2 px-4 py-3 ${STATUS_STYLE[unit.status]}`}
                >
                  <span>
                    <span className="mr-2 text-slate-500">{unit.id}</span>
                    <span className="font-medium">{unit.title_de}</span>
                  </span>
                  <span className="text-sm text-slate-500">{STATUS_LABEL[unit.status]}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
