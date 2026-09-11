import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useSpeech } from "../audio/SpeechContext";
import { useChime } from "../audio/useChime";
import type { ListeningDialog, ListeningResult } from "../courseTypes";
import { answerDialog, getNextDialog } from "../listeningApi";
import DialogPlayer from "../listening/DialogPlayer";
import DialogQuestion from "../listening/DialogQuestion";
import DialogTranscript from "../listening/DialogTranscript";

/**
 * Zwei Figuren reden, du hörst zu und sagst danach, worum es ging.
 *
 * Drei Phasen: hören (kein Text), antworten, nachlesen. Der russische Text
 * liegt zum Abspielen schon vor, wird aber erst nach der Antwort gezeigt —
 * sonst wäre die Frage keine Hörfrage mehr.
 */
export default function ListeningView() {
  const { available } = useSpeech();
  const chime = useChime();
  const [dialog, setDialog] = useState<ListeningDialog | null>(null);
  const [chosen, setChosen] = useState<number | null>(null);
  const [result, setResult] = useState<ListeningResult | null>(null);
  const [gehoert, setGehoert] = useState(false);
  const [error, setError] = useState(false);

  // Die Startseite schlaegt ein bestimmtes Gespraech vor. Das gilt nur fuer das
  // erste; „Nächstes Gespräch" nimmt danach wieder das uebliche.
  const [params] = useSearchParams();
  const wished = Number(params.get("gespraech")) || undefined;

  const laden = useCallback((dialogId?: number) => {
    setDialog(null);
    setChosen(null);
    setResult(null);
    setGehoert(false);
    getNextDialog(dialogId)
      .then(setDialog)
      .catch(() => setError(true));
  }, []);

  // Nur beim ersten Aufbau: ein anderer Wunsch kommt ohnehin nur ueber einen
  // neuen Seitenaufruf, und `wished` in den Abhaengigkeiten wuerde nach
  // „Nächstes Gespräch" nichts aendern — der Parameter bleibt ja stehen.
  useEffect(() => laden(wished), [laden]);

  if (error) return <p>Die Gespräche konnten nicht geladen werden.</p>;
  if (!dialog) return <p>Gespräch wird geladen …</p>;

  if (dialog.dialog_id === null) {
    return (
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold">Noch kein Gespräch</h2>
        <p className="text-slate-600">
          {dialog.next_unit
            ? `Schließ Einheit ${dialog.next_unit} ab — dann kannst du dem ersten Gespräch folgen.`
            : "Es gibt noch keine Gespräche."}
        </p>
      </div>
    );
  }

  const antworten = (index: number) => {
    setChosen(index);
    answerDialog(dialog.dialog_id as number, dialog.seed, index)
      .then((answer) => {
        setResult(answer);
        if (answer.correct) chime();
      })
      .catch(() => setError(true));
  };

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold">
          {result ? result.title_de : "Hör zu — worum geht es?"}
        </h2>
        {result ? null : (
          <p className="text-slate-600">
            Der Text bleibt verdeckt. Du kannst so oft hören, wie du willst.
          </p>
        )}
      </div>

      <DialogPlayer
        speakers={dialog.speakers}
        lines={dialog.lines}
        onFinished={() => setGehoert(true)}
      />

      {/* Ohne Stimme waere die Frage nicht zu beantworten — dann steht der Text
          sofort da und es wird eine Leseaufgabe, aber eine loesbare. */}
      {available && !gehoert && !result ? (
        <p className="text-slate-500">Die Frage kommt, sobald das Gespräch einmal durch ist.</p>
      ) : (
        <DialogQuestion
          question={dialog.question_de}
          options={dialog.options_de}
          chosen={chosen}
          result={result}
          onChoose={antworten}
        />
      )}

      {result || !available ? (
        <div className="space-y-3 border-t border-slate-200 pt-4">
          <h3 className="text-lg font-medium">Zum Nachlesen</h3>
          <DialogTranscript
            speakers={dialog.speakers}
            lines={dialog.lines}
            translations={result?.translations_de}
          />
        </div>
      ) : null}

      {result ? (
        <div className="flex flex-wrap items-center gap-4">
          <Link
            to="/"
            className="inline-block rounded-xl bg-sky-600 px-5 py-2 font-medium text-white"
          >
            Zurück zu Heute
          </Link>
          <button
            type="button"
            onClick={() => laden()}
            className="rounded-xl border-2 border-slate-300 bg-white px-4 py-2 transition hover:border-sky-400"
          >
            Nächstes Gespräch
          </button>
        </div>
      ) : null}
    </div>
  );
}
