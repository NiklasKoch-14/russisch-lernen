import { useCallback, useEffect, useState } from "react";

import { useChime } from "../audio/useChime";
import type { FlashcardResult, FlashcardRound } from "../courseTypes";
import Flashcard from "../flashcards/Flashcard";
import { answerFlashcard, getFlashcardRound } from "../flashcardsApi";

const RICHTUNGEN = [
  { key: "mixed", label: "gemischt" },
  { key: "ru_de", label: "RU → DE" },
  { key: "de_ru", label: "DE → RU" },
] as const;

/**
 * Karteikarten über alle bisher gelernten Vokabeln.
 *
 * Zwölf Karten je Runde, drei Optionen je Karte. Getrennt von „Wiederholen":
 * dort geht es um Wortformen im Satz, hier um die nackte Vokabel — deshalb
 * verschiebt eine falsche Karte hier keinen Wiederholungstermin dort.
 */
export default function FlashcardsView() {
  const [direction, setDirection] = useState<string>("mixed");
  const [round, setRound] = useState<FlashcardRound | null>(null);
  const [position, setPosition] = useState(0);
  const [chosen, setChosen] = useState<number | null>(null);
  const [result, setResult] = useState<FlashcardResult | null>(null);
  const [treffer, setTreffer] = useState(0);
  const [error, setError] = useState(false);
  const chime = useChime();

  const laden = useCallback((gewaehlt: string) => {
    setRound(null);
    setPosition(0);
    setChosen(null);
    setResult(null);
    setTreffer(0);
    getFlashcardRound(gewaehlt)
      .then(setRound)
      .catch(() => setError(true));
  }, []);

  useEffect(() => {
    laden(direction);
  }, [direction, laden]);

  if (error) return <p>Die Karteikarten konnten nicht geladen werden.</p>;
  if (!round) return <p>Karten werden geladen …</p>;

  const schalter = (
    <div className="flex flex-wrap items-center gap-2">
      {RICHTUNGEN.map((richtung) => (
        <button
          key={richtung.key}
          type="button"
          aria-pressed={direction === richtung.key}
          onClick={() => setDirection(richtung.key)}
          className={`rounded-full border-2 px-3 py-1 text-sm transition ${
            direction === richtung.key
              ? "border-sky-500 bg-sky-50 font-medium text-sky-800"
              : "border-slate-300 bg-white text-slate-600 hover:border-sky-400"
          }`}
        >
          {richtung.label}
        </button>
      ))}
      <span className="ml-auto text-sm text-slate-500">{round.known_words} Wörter gelernt</span>
    </div>
  );

  if (round.cards.length === 0) {
    return (
      <div className="space-y-3">
        {schalter}
        <h2 className="text-2xl font-semibold">Noch keine Wörter</h2>
        <p className="text-slate-600">
          Schließ eine Einheit im Kurs ab — danach liegen ihre Vokabeln hier als Karten.
        </p>
      </div>
    );
  }

  const card = round.cards[position];

  if (!card) {
    return (
      <div className="space-y-4">
        {schalter}
        <h2 className="text-2xl font-semibold">
          {treffer} von {round.cards.length} richtig
        </h2>
        <button
          type="button"
          onClick={() => laden(direction)}
          className="rounded-xl border-2 border-slate-300 bg-white px-4 py-2 transition hover:border-sky-400"
        >
          Neue Runde
        </button>
      </div>
    );
  }

  const antworten = (index: number) => {
    if (result) return;
    setChosen(index);
    answerFlashcard(card.lexeme_id, round.seed, index)
      .then((antwort) => {
        setResult(antwort);
        if (antwort.correct) {
          setTreffer((bisher) => bisher + 1);
          chime();
        }
      })
      .catch(() => setError(true));
  };

  const weiter = () => {
    setChosen(null);
    setResult(null);
    setPosition((aktuell) => aktuell + 1);
  };

  return (
    <div className="space-y-5">
      {schalter}
      <p className="text-sm text-slate-500">
        Karte {position + 1} von {round.cards.length}
      </p>

      <Flashcard card={card} result={result} chosen={chosen} onChoose={antworten} />

      {result ? (
        <div className="space-y-3">
          <p className={result.correct ? "text-emerald-700" : "text-rose-700"}>
            {result.correct ? "Richtig." : `Richtig wäre: ${result.text} — ${result.gloss_de}`}
          </p>
          <button
            type="button"
            onClick={weiter}
            className="rounded-xl border-2 border-slate-300 bg-white px-4 py-2 transition hover:border-sky-400"
          >
            Weiter
          </button>
        </div>
      ) : null}
    </div>
  );
}
