import SpeakerButton from "../audio/SpeakerButton";
import type { NewWord } from "../courseTypes";
import RussianText from "./RussianText";

/**
 * Die neuen Woerter der Einheit, bevor die Aufgaben beginnen.
 *
 * Ohne diesen Schritt begegnet man einem Wort zuerst in einer Zuordnungsaufgabe
 * — und die fragt ab, statt zu erklaeren. Die Bedeutung steht hier deshalb
 * offen da; nur die Aussprache bleibt hinter dem Verweilen, wie ueberall sonst.
 */
export default function NewWords({
  words,
  onContinue,
}: {
  words: NewWord[];
  onContinue: () => void;
}) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium">
        {words.length === 1 ? "1 neues Wort" : `${words.length} neue Wörter`} in dieser Einheit
      </h3>
      <ul className="space-y-2">
        {words.map((word) => (
          <li
            key={word.id}
            className="flex items-center gap-3 rounded-xl border-2 border-slate-200 bg-white px-4 py-2"
          >
            <span className="text-lg">
              <RussianText word={word} />
            </span>
            <SpeakerButton text={word.text} />
            <span className="ml-auto text-right text-slate-600">{word.gloss_de}</span>
          </li>
        ))}
      </ul>
      <button
        type="button"
        onClick={onContinue}
        className="rounded-xl bg-sky-600 px-5 py-2 font-medium text-white"
      >
        Weiter zu den Aufgaben
      </button>
    </div>
  );
}
