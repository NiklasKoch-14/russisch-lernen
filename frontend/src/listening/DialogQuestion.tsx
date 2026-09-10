import type { ListeningResult } from "../courseTypes";

/**
 * Die Verständnisfrage. Nach der Antwort bleiben die Optionen stehen und zeigen,
 * welche richtig war — auch dann, wenn richtig geantwortet wurde.
 */
export default function DialogQuestion({
  question,
  options,
  chosen,
  result,
  onChoose,
}: {
  question: string;
  options: string[];
  chosen: number | null;
  result: ListeningResult | null;
  onChoose: (index: number) => void;
}) {
  return (
    <div className="space-y-3">
      <h3 className="text-lg font-medium">{question}</h3>
      <div className="flex flex-col gap-2">
        {options.map((option, index) => {
          const richtig = result !== null && index === result.correct_index;
          const falschGewaehlt = result !== null && index === chosen && !result.correct;
          const farbe = richtig
            ? "border-emerald-500 bg-emerald-50"
            : falschGewaehlt
              ? "border-rose-500 bg-rose-50"
              : "border-slate-300 bg-white";
          return (
            <button
              key={option}
              type="button"
              disabled={result !== null}
              onClick={() => onChoose(index)}
              className={`rounded-xl border-2 px-4 py-2 text-left text-lg transition hover:border-sky-400 disabled:opacity-90 ${farbe}`}
            >
              {option}
            </button>
          );
        })}
      </div>
    </div>
  );
}
