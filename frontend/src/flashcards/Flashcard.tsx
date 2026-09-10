import SpeakerButton from "../audio/SpeakerButton";
import RussianText from "../course/RussianText";
import type { Flashcard as Model, FlashcardResult } from "../courseTypes";

/**
 * Eine Karte: oben die Frage, darunter drei Optionen.
 *
 * Welche Seite die Frage ist, entscheidet die Richtung — die russische Seite
 * trägt immer Umschrift und einen Lautsprecher, egal auf welcher Seite sie
 * gerade steht.
 */
export default function Flashcard({
  card,
  result,
  chosen,
  onChoose,
}: {
  card: Model;
  /** null, solange noch nicht geantwortet wurde. */
  result: FlashcardResult | null;
  chosen: number | null;
  onChoose: (index: number) => void;
}) {
  const optionen =
    card.direction === "ru_de"
      ? card.options_de.map((text) => ({ text, translit: null }))
      : card.options_ru.map((word) => ({ text: word.text, translit: word.translit }));

  return (
    <div className="space-y-5">
      <div className="flex min-h-24 items-center justify-center gap-3 rounded-2xl border-2 border-slate-200 bg-white px-6 py-8">
        {card.direction === "ru_de" && card.prompt_ru ? (
          <>
            <RussianText word={card.prompt_ru} className="text-3xl" revealed />
            <SpeakerButton text={card.prompt_ru.text} />
          </>
        ) : (
          <span className="text-2xl">{card.prompt_de}</span>
        )}
      </div>

      <div className="flex flex-col gap-2">
        {optionen.map((option, index) => {
          const richtig = result !== null && index === result.correct_index;
          const falschGewaehlt = result !== null && index === chosen && !result.correct;
          const farbe = richtig
            ? "border-emerald-500 bg-emerald-50"
            : falschGewaehlt
              ? "border-rose-500 bg-rose-50"
              : "border-slate-300 bg-white";
          return (
            <button
              key={`${option.text}-${index}`}
              type="button"
              disabled={result !== null}
              onClick={() => onChoose(index)}
              className={`flex items-center gap-3 rounded-xl border-2 px-4 py-3 text-left text-lg transition hover:border-sky-400 disabled:opacity-90 ${farbe}`}
            >
              {option.translit === null ? (
                option.text
              ) : (
                <RussianText
                  word={{ text: option.text, translit: option.translit }}
                  revealed={result !== null}
                />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
