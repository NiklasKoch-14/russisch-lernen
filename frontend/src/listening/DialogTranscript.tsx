import SpeakerButton from "../audio/SpeakerButton";
import RussianText from "../course/RussianText";
import type { ListeningLine, ListeningSpeaker } from "../courseTypes";

/**
 * Das Gespräch zum Nachlesen — erst nach der Antwort, sonst wäre die Frage
 * verraten. Die Übersetzungen kommen mit der Antwort vom Server; fehlen sie,
 * bleibt der russische Satz für sich.
 */
export default function DialogTranscript({
  speakers,
  lines,
  translations = [],
}: {
  speakers: ListeningSpeaker[];
  lines: ListeningLine[];
  translations?: string[];
}) {
  return (
    <ol className="space-y-3">
      {lines.map((line, index) => (
        <li key={`${index}-${line.text}`} className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-slate-500" lang="ru">
              {speakers[line.speaker]?.name_ru}
            </span>
            <RussianText
              word={{ text: line.text, translit: line.translit }}
              className="text-xl"
              revealed
            />
            <SpeakerButton text={line.text} voice={speakers[line.speaker]?.voice} />
          </div>
          {translations[index] ? (
            <p className="text-slate-600">{translations[index]}</p>
          ) : null}
        </li>
      ))}
    </ol>
  );
}
