import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getToday } from "../courseApi";
import type { TodayPlan, TodayStep } from "../courseTypes";

/**
 * Die Startseite: was heute dran ist, als Checkliste mit genau einem Hauptknopf.
 *
 * Sie ist ein Lehrer, kein Menü. Statt sechs gleichwertiger Wege schlägt sie
 * einen vor — auffrischen, eine neue Einheit, anwenden — und sagt am Ende
 * „fertig für heute". Gezeigt wird die Dauer, nie die Menge: „150 fällig"
 * bedeutet für einen Anfänger nur „du hast versagt". Serien, Punkte und
 * Prozente fehlen mit Absicht. Hintergrund und Quellen stehen in
 * docs/superpowers/specs/2026-09-11-speaker-today-start-page-design.md.
 */

const SKIPPED_DE: Record<NonNullable<TodayPlan["unit_skipped"]>, string> = {
  pause: "Heute keine neue Einheit — wir frischen erst auf.",
  backlog: "Heute keine neue Einheit — erst das Wiederholen, sonst wird der Stapel morgen zu hoch.",
  all_done: "Alle vorhandenen Einheiten sind geschafft — neue kommen bald.",
};

const STATUS_DE: Record<TodayStep["status"], string> = {
  done: "erledigt",
  next: "als Nächstes",
  later: "danach",
};

const STATUS_ICON: Record<TodayStep["status"], string> = {
  done: "✓",
  next: "▶",
  later: "○",
};

const STATUS_STYLE: Record<TodayStep["status"], string> = {
  done: "border-emerald-200 bg-emerald-50",
  next: "border-sky-300 bg-white shadow-sm",
  later: "border-slate-200 bg-white",
};

const ICON_STYLE: Record<TodayStep["status"], string> = {
  done: "bg-emerald-600 text-white",
  next: "bg-sky-600 text-white",
  later: "border-2 border-slate-300 text-slate-400",
};

function title(step: TodayStep): string {
  switch (step.kind) {
    case "review":
      return "Auffrischen";
    case "unit":
      return `Einheit ${step.unit_id} · ${step.title_de}`;
    case "listening":
      return `Gespräch hören · ${step.title_de}`;
    case "scene":
      return `Im Dorf · ${step.title_de}`;
  }
}

function detail(step: TodayStep): string {
  switch (step.kind) {
    case "review":
      return "Was du schon kennst, kurz wiederholt.";
    case "unit":
      return step.detail_de;
    case "listening":
      return step.known
        ? "Kennst du schon — hör, wie viel du jetzt verstehst."
        : "Erst hören, dann lesen.";
    case "scene": {
      // Die App hört nicht zu — laut sprechen schließt die Lücke wenigstens halb.
      const hint = "sag die Antwort laut, bevor du klickst.";
      return step.detail_de ? `${step.detail_de} — ${hint}` : `S${hint.slice(1)}`;
    }
  }
}

/** Kurz, weil es auf dem Knopf steht. */
function action(step: TodayStep): string {
  switch (step.kind) {
    case "review":
      return "Auffrischen";
    case "unit":
      return `Einheit ${step.unit_id}`;
    case "listening":
      return "Gespräch hören";
    case "scene":
      return "Ins Dorf";
  }
}

const TEXT_LINK = "text-sky-700 underline underline-offset-2 hover:text-sky-900";

export default function TodayView() {
  const [plan, setPlan] = useState<TodayPlan | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getToday()
      .then(setPlan)
      .catch(() => setError(true));
  }, []);

  if (error) return <p>Der Plan für heute konnte nicht geladen werden.</p>;
  if (!plan) return <p>Plan für heute wird geladen …</p>;

  const open = plan.steps.filter((step) => step.status !== "done");
  const next = plan.steps.find((step) => step.status === "next");
  const minutes = open.reduce((sum, step) => sum + step.minutes, 0);
  const started = plan.steps.some((step) => step.status === "done");
  const review = plan.steps.find((step) => step.kind === "review");
  const unitDone = plan.steps.some((step) => step.kind === "unit" && step.status === "done");

  // Die kurze Variante ist nur eine Wahl, wenn danach noch etwas käme.
  const offerShort = review !== undefined && review.status !== "done" && open.length > 1;
  const offerAnotherUnit =
    plan.next_unit_id !== null &&
    (plan.unit_skipped === "pause" || plan.unit_skipped === "backlog" || unitDone);

  let summary: string;
  if (plan.finished) summary = "Fertig für heute.";
  else if (open.length > 0) summary = `Etwa ${minutes} ${minutes === 1 ? "Minute" : "Minuten"}.`;
  else summary = "Für heute steht nichts an.";

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h2 className="text-2xl font-semibold">
          {plan.greeting === "welcome_back" ? "Schön, dass du wieder da bist." : "Heute"}
        </h2>
        <p className={plan.finished ? "text-lg font-medium text-emerald-700" : "text-slate-600"}>
          {summary}
        </p>
      </header>

      {plan.steps.length > 0 ? (
        <ol aria-label="Heute dran" className="space-y-3">
          {plan.steps.map((step) => (
            <li
              key={step.kind}
              aria-current={step.status === "next" ? "step" : undefined}
              className={`flex items-start gap-3 rounded-2xl border-2 px-4 py-3 ${STATUS_STYLE[step.status]}`}
            >
              <span
                aria-hidden="true"
                className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm ${ICON_STYLE[step.status]}`}
              >
                {STATUS_ICON[step.status]}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block font-medium">{title(step)}</span>
                <span className="block text-slate-600">{detail(step)}</span>
              </span>
              <span className="shrink-0 text-sm text-slate-500">{STATUS_DE[step.status]}</span>
            </li>
          ))}
        </ol>
      ) : null}

      {plan.unit_skipped ? <p className="text-slate-600">{SKIPPED_DE[plan.unit_skipped]}</p> : null}

      {next ? (
        <Link
          to={next.link}
          className="inline-flex min-h-12 items-center rounded-xl bg-sky-600 px-6 py-3 text-lg font-medium text-white shadow-sm transition hover:bg-sky-700"
        >
          {`${started ? "Weiter" : "Los"}: ${action(next)} · ca. ${next.minutes} Min.`}
        </Link>
      ) : null}

      <nav aria-label="Andere Wege" className="flex flex-wrap gap-x-5 gap-y-2">
        {offerShort ? (
          <Link to="/wiederholen" className={TEXT_LINK}>
            Nur 5 Minuten heute
          </Link>
        ) : null}
        {offerAnotherUnit ? (
          <Link to={`/kurs/${plan.next_unit_id}`} className={TEXT_LINK}>
            Noch eine Einheit
          </Link>
        ) : null}
        {plan.offer_screening ? (
          <Link to="/einstufung" className={TEXT_LINK}>
            Du kannst schon etwas Russisch? Einstufung · 2 Min.
          </Link>
        ) : null}
        <Link to="/kurs" className={TEXT_LINK}>
          Alle Einheiten
        </Link>
      </nav>

      {plan.week_days > 0 ? (
        <p className="text-sm text-slate-500">
          {`Diese Woche an ${plan.week_days} ${plan.week_days === 1 ? "Tag" : "Tagen"} geübt.`}
        </p>
      ) : null}
    </div>
  );
}
